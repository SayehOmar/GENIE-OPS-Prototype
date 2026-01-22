"""
API routes for testing and form analysis
"""

import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.automation.browser import BrowserAutomation
from app.ai.form_reader import FormReader
from app.utils.logger import logger

router = APIRouter()


class FormAnalysisRequest(BaseModel):
    url: str
    use_ai: bool = True


class FormAnalysisResponse(BaseModel):
    success: bool
    method: str  # "ai" or "dom"
    form_structure: Dict[str, Any]
    fields: list
    error: Optional[str] = None


@router.post("/analyze-form", response_model=FormAnalysisResponse)
async def analyze_form(request: FormAnalysisRequest):
    """
    Analyze a form at the given URL
    Returns form structure with field names, selectors, and purposes
    """
    browser = BrowserAutomation()

    try:
        # Start browser and navigate
        await browser.start()
        await browser.navigate(request.url)

        # Get HTML content
        html_content = await browser.get_page_content()

        form_structure = None
        method = "dom"

        # Try AI analysis if requested and available
        if request.use_ai:
            try:
                form_reader = FormReader()
                if form_reader.client:
                    form_structure = await form_reader.analyze_form(html_content)
                    if (
                        form_structure
                        and not form_structure.get("error")
                        and form_structure.get("fields")
                    ):
                        method = "ai"
                        logger.info("Form analyzed using AI")
                    else:
                        # AI failed, fallback to DOM
                        logger.warning(
                            "AI analysis failed, falling back to DOM extraction"
                        )
                        form_structure = None
                else:
                    logger.warning("Ollama not available, using DOM extraction")
            except Exception as e:
                logger.warning(
                    f"AI analysis error: {e}, falling back to DOM extraction"
                )

        # Use DOM extraction if AI not used or failed
        if not form_structure or not form_structure.get("fields"):
            form_structure = await browser.extract_form_fields_dom()
            method = "dom"
            logger.info("Form analyzed using DOM extraction")

        # Extract fields for response
        fields = form_structure.get("fields", [])

        # Format fields for display
        formatted_fields = []
        for field in fields:
            formatted_fields.append(
                {
                    "name": field.get("name", ""),
                    "label": field.get("label", ""),
                    "selector": field.get("selector", ""),
                    "type": field.get("type", ""),
                    "purpose": field.get("purpose", "other"),
                    "required": field.get("required", False),
                    "placeholder": field.get("placeholder", ""),
                }
            )

        # Save JSON report to reports folder
        try:
            backend_dir = Path(__file__).parent.parent.parent
            reports_dir = backend_dir / "test" / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)

            # Create report with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"form_analysis_{timestamp}.json"
            report_path = reports_dir / report_filename

            # Create report data
            report_data = {
                "timestamp": datetime.now().isoformat(),
                "url": request.url,
                "method": method,
                "use_ai": request.use_ai,
                "fields": formatted_fields,
                "form_structure": form_structure,
            }

            # Save to file
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Form analysis report saved to {report_path}")
        except Exception as e:
            logger.warning(f"Failed to save form analysis report: {e}")

        return FormAnalysisResponse(
            success=True,
            method=method,
            form_structure=form_structure,
            fields=formatted_fields,
        )

    except Exception as e:
        logger.error(f"Form analysis error: {str(e)}", exc_info=True)
        error_msg = str(e)

        # Provide more helpful error messages
        if (
            "ECONNREFUSED" in error_msg
            or "Connection refused" in error_msg
            or "Failed to navigate" in error_msg
        ):
            error_msg = f"Test server not accessible at {request.url}. Make sure the test server is running on port 8080."
        elif "timeout" in error_msg.lower():
            error_msg = f"Request timed out while accessing {request.url}. The server may be slow or unresponsive."

        return FormAnalysisResponse(
            success=False, method="error", form_structure={}, fields=[], error=error_msg
        )
    finally:
        try:
            await browser.close()
        except:
            pass  # Ignore errors during cleanup


@router.get("/test-status")
async def get_test_status():
    """
    Get status of test services (server, Ollama, API)
    """
    import socket
    import aiohttp

    status = {
        "test_server": False,
        "ollama": False,
        "backend_api": True,  # We're in the API, so it's running
    }

    # Check test server (port 8080)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", 8080))
        sock.close()
        status["test_server"] = result == 0
    except:
        pass

    # Check Ollama (port 11434)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:11434/api/tags",
                timeout=aiohttp.ClientTimeout(
                    total=5
                ),  # Increased timeout to 5 seconds
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Check if models exist and list is not empty
                    models = data.get("models", [])
                    status["ollama"] = bool(models and len(models) > 0)
                else:
                    status["ollama"] = False
    except aiohttp.ClientError as e:
        logger.debug(f"Ollama connection error: {e}")
        status["ollama"] = False
    except Exception as e:
        logger.debug(f"Ollama check error: {e}")
        status["ollama"] = False

        return status


class SaveSubmissionRequest(BaseModel):
    timestamp: str
    form_data: Dict[str, Any]
    url: str


@router.post("/save-submission")
async def save_submission(request: SaveSubmissionRequest):
    """
    Save form submission data to a text file in reports directory
    Called by test_form.html when form is submitted
    """
    try:
        backend_dir = Path(__file__).parent.parent.parent
        reports_dir = backend_dir / "test" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Create filename with timestamp
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"form_submission_{timestamp_str}.txt"
        file_path = reports_dir / filename

        # Determine analysis method from form data
        analysis_method = request.form_data.get("analysis_method", "unknown")
        method_label = (
            "AI (Ollama)"
            if analysis_method == "ai"
            else "DOM Extraction" if analysis_method == "dom" else "Unknown"
        )

        # Format submission data
        lines = [
            "=" * 60,
            "FORM SUBMISSION DATA",
            "=" * 60,
            f"Timestamp: {request.timestamp}",
            f"URL: {request.url}",
            f"Saved at: {datetime.now().isoformat()}",
            f"Analysis Method: {method_label} ({analysis_method})",
            "",
            "Form Data:",
            "-" * 60,
        ]

        # Add form fields (exclude analysis_method from display since it's shown above)
        for key, value in request.form_data.items():
            if key != "analysis_method":  # Don't show it twice
                lines.append(f"{key}: {value}")

        lines.extend(
            [
                "",
                "=" * 60,
                "End of Submission",
                "=" * 60,
            ]
        )

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Form submission saved to {file_path}")

        return {
            "success": True,
            "message": f"Submission saved to {filename}",
            "file_path": str(file_path),
        }

    except Exception as e:
        logger.error(f"Failed to save form submission: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


class RunTestsRequest(BaseModel):
    test_type: str = "all"  # "all", "dom", "ai", or specific test name
    use_ai: bool = True


class TestResult(BaseModel):
    test_name: str
    status: str  # "passed", "failed", "skipped", "error"
    duration: float
    message: Optional[str] = None


class RunTestsResponse(BaseModel):
    success: bool
    total_tests: int
    passed: int
    failed: int
    skipped: int
    duration: float
    results: List[TestResult]
    output: str
    error: Optional[str] = None
    detected_fields: Optional[List[dict]] = None  # Fields detected from test form
    json_report: Optional[dict] = None  # Full JSON report


@router.post("/run-tests", response_model=RunTestsResponse)
async def run_tests(request: RunTestsRequest):
    """
    Run tests and return results
    Can be called from the browser to run tests and get feedback
    """
    import asyncio
    import os

    # Get backend directory
    backend_dir = Path(__file__).parent.parent.parent
    test_file = backend_dir / "test" / "test_submission.py"

    if not test_file.exists():
        return RunTestsResponse(
            success=False,
            total_tests=0,
            passed=0,
            failed=0,
            skipped=0,
            duration=0.0,
            results=[],
            output="",
            error=f"Test file not found: {test_file}",
        )

    # Build pytest command - use venv Python
    venv_python = backend_dir / "venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        # Try alternative venv paths (Linux/Mac)
        venv_python = backend_dir / "venv" / "bin" / "python"
        if not venv_python.exists():
            venv_python = Path(sys.executable)  # Fallback to current Python

    cmd = [
        str(venv_python),
        "-m",
        "pytest",
        str(test_file),
        "-v",
        "--tb=short",
    ]

    # Add test filter if specified
    if request.test_type == "dom":
        cmd.append("::TestSubmissionWorkflow::test_full_workflow_without_ai")
    elif request.test_type == "ai":
        cmd.append("::TestSubmissionWorkflow::test_full_workflow_with_ai")
    elif request.test_type != "all":
        # Specific test name
        cmd.append(f"::TestSubmissionWorkflow::{request.test_type}")

    try:
        # Run tests
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(backend_dir),
        )

        stdout, stderr = await process.communicate()
        output = stdout.decode("utf-8", errors="ignore")
        error_output = stderr.decode("utf-8", errors="ignore")

        # Parse results
        results = []
        passed = 0
        failed = 0
        skipped = 0

        # Parse pytest output
        lines = output.split("\n")
        for line in lines:
            if "PASSED" in line:
                passed += 1
                # Extract test name
                test_name = (
                    line.split("::")[-1].split()[0] if "::" in line else "unknown"
                )
                results.append(
                    TestResult(test_name=test_name, status="passed", duration=0.0)
                )
            elif "FAILED" in line:
                failed += 1
                test_name = (
                    line.split("::")[-1].split()[0] if "::" in line else "unknown"
                )
                results.append(
                    TestResult(
                        test_name=test_name,
                        status="failed",
                        duration=0.0,
                        message="Test failed",
                    )
                )
            elif "SKIPPED" in line:
                skipped += 1
                test_name = (
                    line.split("::")[-1].split()[0] if "::" in line else "unknown"
                )
                results.append(
                    TestResult(test_name=test_name, status="skipped", duration=0.0)
                )

        total = passed + failed + skipped

        # Get detected fields from test form for JSON report
        detected_fields = []
        json_report = None
        try:
            # Analyze the test form to get detected fields
            browser = BrowserAutomation()
            await browser.start()
            await browser.navigate("http://localhost:8080/test_form.html")
            form_structure = await browser.extract_form_fields_dom()
            await browser.close()

            if form_structure and form_structure.get("fields"):
                detected_fields = []
                for field in form_structure.get("fields", []):
                    detected_fields.append(
                        {
                            "name": field.get("name", ""),
                            "label": field.get("label", ""),
                            "selector": field.get("selector", ""),
                            "type": field.get("type", ""),
                            "purpose": field.get("purpose", "other"),
                            "required": field.get("required", False),
                            "placeholder": field.get("placeholder", ""),
                        }
                    )

            # Create comprehensive JSON report
            json_report = {
                "test_execution": {
                    "test_type": request.test_type,
                    "use_ai": request.use_ai,
                    "timestamp": datetime.now().isoformat(),
                    "total_tests": total,
                    "passed": passed,
                    "failed": failed,
                    "skipped": skipped,
                    "success": (failed == 0),
                },
                "test_results": [
                    {
                        "test_name": r.test_name,
                        "status": r.status,
                        "duration": r.duration,
                        "message": r.message,
                    }
                    for r in results
                ],
                "detected_form_fields": detected_fields,
                "raw_output": output + "\n" + error_output,
            }

            # Save JSON report to reports folder
            try:
                backend_dir = Path(__file__).parent.parent.parent
                reports_dir = backend_dir / "test" / "reports"
                reports_dir.mkdir(parents=True, exist_ok=True)

                # Create report filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_filename = f"test_execution_{timestamp}.json"
                report_path = reports_dir / report_filename

                # Save to file
                with open(report_path, "w", encoding="utf-8") as f:
                    json.dump(json_report, f, indent=2, ensure_ascii=False)

                logger.info(f"Test execution report saved to {report_path}")
            except Exception as e:
                logger.warning(f"Failed to save test execution report: {e}")
        except Exception as e:
            logger.warning(f"Could not analyze test form for JSON report: {e}")

        return RunTestsResponse(
            success=(failed == 0),
            total_tests=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration=0.0,
            results=results,
            output=output + "\n" + error_output,
            detected_fields=detected_fields if detected_fields else None,
            json_report=json_report,
        )

    except Exception as e:
        logger.error(f"Error running tests: {str(e)}", exc_info=True)
        return RunTestsResponse(
            success=False,
            total_tests=0,
            passed=0,
            failed=0,
            skipped=0,
            duration=0.0,
            results=[],
            output="",
            error=str(e),
        )
