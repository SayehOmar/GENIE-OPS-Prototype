"""
Test suite for submission workflow
Tests both AI (Ollama) and DOM fallback modes
"""

import pytest
import pytest_asyncio
import asyncio
import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.workflow.submitter import SubmissionWorkflow
from app.automation.browser import BrowserAutomation
from app.ai.form_reader import FormReader
from app.core.config import settings

# Set headless mode for tests (False = visible browser so you can watch it fill forms)
settings.PLAYWRIGHT_HEADLESS = False

# Set headless mode for tests (False = visible browser so you can watch it fill forms)
settings.PLAYWRIGHT_HEADLESS = False


# Test data
TEST_SAAS_DATA = {
    "name": "Test SaaS Product",
    "url": "https://example.com",
    "contact_email": "test@example.com",
    "description": "This is a test product for automation testing. It demonstrates the capabilities of the GENIE OPS system.",
    "category": "SaaS",
    "logo_path": None,  # Optional: can add path to test logo
}

TEST_FORM_URL = "http://localhost:8080/test_form.html"


def _save_test_report(test_name: str, result: dict, saas_data: dict):
    """Save test result as JSON report to reports folder"""
    try:
        # Get test directory
        test_dir = Path(__file__).parent
        reports_dir = test_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Create report filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"{test_name}_{timestamp}.json"
        report_path = reports_dir / report_filename
        
        # Extract detected fields from result
        detected_fields = []
        if result.get("form_structure") and result["form_structure"].get("fields"):
            for field in result["form_structure"]["fields"]:
                detected_fields.append({
                    "name": field.get("name", ""),
                    "label": field.get("label", ""),
                    "selector": field.get("selector", ""),
                    "type": field.get("type", ""),
                    "purpose": field.get("purpose", "other"),
                    "required": field.get("required", False),
                    "placeholder": field.get("placeholder", "")
                })
        
        # Create report data
        report_data = {
            "test_name": test_name,
            "timestamp": datetime.now().isoformat(),
            "test_url": TEST_FORM_URL,
            "test_result": {
                "status": result.get("status"),
                "message": result.get("message"),
                "fields_filled": result.get("fields_filled", 0),
                "total_fields": result.get("total_fields", 0),
                "url": result.get("url"),
            },
            "saas_data": saas_data,
            "detected_form_fields": detected_fields,
            "form_structure": result.get("form_structure", {}),
            "fill_errors": result.get("fill_errors", [])
        }
        
        # Save to file
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Test report saved to: {report_path}")
    except Exception as e:
        print(f"\n⚠ Failed to save test report: {e}")


@pytest_asyncio.fixture
async def workflow():
    """Create a SubmissionWorkflow instance for testing."""
    wf = SubmissionWorkflow()
    try:
        yield wf
    finally:
        # Cleanup: ensure browser is closed
        if wf.browser:
            try:
                await wf.browser.close()
            except:
                pass


@pytest_asyncio.fixture
async def browser():
    """Create a BrowserAutomation instance for testing."""
    br = BrowserAutomation()
    try:
        yield br
    finally:
        try:
            await br.close()
        except:
            pass


class TestSubmissionWorkflow:
    """Test suite for the complete submission workflow"""

    @pytest.mark.asyncio
    async def test_form_detection(self, browser):
        """Test that the system can detect forms on a page"""
        await browser.start()
        await browser.navigate(TEST_FORM_URL)

        detected = await browser.detect_submission_page()
        assert detected is True, "Form should be detected on test page"

        # Verify form elements exist
        form_count = await browser.page.locator("form").count()
        assert form_count > 0, "At least one form should be present"

        input_count = await browser.page.locator("input, textarea, select").count()
        assert input_count >= 5, "Should have at least 5 form inputs"

    @pytest.mark.asyncio
    async def test_dom_form_extraction(self, browser):
        """Test DOM-based form field extraction (no AI needed)"""
        await browser.start()
        await browser.navigate(TEST_FORM_URL)

        form_structure = await browser.extract_form_fields_dom()

        assert "fields" in form_structure, "Form structure should contain fields"
        assert len(form_structure["fields"]) > 0, "Should extract at least one field"

        # Verify expected fields are extracted
        field_names = [f.get("name", "").lower() for f in form_structure["fields"]]
        assert any(
            "name" in name or "product" in name for name in field_names
        ), "Should extract product name field"
        assert any(
            "url" in name or "website" in name for name in field_names
        ), "Should extract URL field"
        assert any(
            "email" in name for name in field_names
        ), "Should extract email field"

        # Verify selectors are present
        for field in form_structure["fields"]:
            assert "selector" in field, "Each field should have a selector"
            assert field["selector"], "Selector should not be empty"

    @pytest.mark.asyncio
    async def test_ai_form_extraction(self, browser):
        """Test AI-based form field extraction (requires Ollama)"""
        # Check if Ollama is available
        try:
            form_reader = FormReader()
            if not form_reader.client:
                pytest.skip("Ollama not available. Skipping AI test.")
        except Exception as e:
            pytest.skip(f"Ollama initialization failed: {e}. Skipping AI test.")

        await browser.start()
        await browser.navigate(TEST_FORM_URL)

        html_content = await browser.get_page_content()
        form_structure = await form_reader.analyze_form(html_content)

        if form_structure.get("error"):
            pytest.skip(f"AI form analysis failed: {form_structure.get('error')}")

        assert "fields" in form_structure, "Form structure should contain fields"
        assert (
            len(form_structure["fields"]) > 0
        ), "Should extract at least one field with AI"

    @pytest.mark.asyncio
    async def test_field_mapping(self, browser):
        """Test that SaaS data maps correctly to form fields"""
        await browser.start()
        await browser.navigate(TEST_FORM_URL)

        form_structure = await browser.extract_form_fields_dom()

        # Test mapping logic
        mapped_data = {}
        for field in form_structure.get("fields", []):
            field_name = (
                field.get("name", "")
                + " "
                + field.get("label", "")
                + " "
                + field.get("placeholder", "")
            ).lower()
            purpose = field.get("purpose", "").lower()
            selector = field.get("selector", "")

            if not selector:
                continue

            if purpose == "name" or any(
                kw in field_name for kw in ["name", "title", "product"]
            ):
                mapped_data[selector] = TEST_SAAS_DATA["name"]
            elif purpose == "url" or any(
                kw in field_name for kw in ["url", "website", "site"]
            ):
                mapped_data[selector] = TEST_SAAS_DATA["url"]
            elif purpose == "email" or any(
                kw in field_name for kw in ["email", "mail"]
            ):
                mapped_data[selector] = TEST_SAAS_DATA["contact_email"]
            elif purpose == "description" or any(
                kw in field_name for kw in ["description", "desc"]
            ):
                mapped_data[selector] = TEST_SAAS_DATA["description"]
            elif purpose == "category" or any(kw in field_name for kw in ["category"]):
                mapped_data[selector] = TEST_SAAS_DATA["category"]

        assert (
            len(mapped_data) >= 4
        ), "Should map at least 4 fields (name, url, email, description)"
        assert TEST_SAAS_DATA["name"] in mapped_data.values(), "Name should be mapped"
        assert TEST_SAAS_DATA["url"] in mapped_data.values(), "URL should be mapped"
        assert (
            TEST_SAAS_DATA["contact_email"] in mapped_data.values()
        ), "Email should be mapped"

    @pytest.mark.asyncio
    async def test_form_filling(self, browser):
        """Test that form fields can be filled correctly"""
        await browser.start()
        await browser.navigate(TEST_FORM_URL)

        form_structure = await browser.extract_form_fields_dom()

        # Create field mappings
        mapped_data = {}
        for field in form_structure.get("fields", []):
            field_name = (field.get("name", "") + " " + field.get("label", "")).lower()
            selector = field.get("selector", "")

            if not selector:
                continue

            if "name" in field_name or "product" in field_name:
                mapped_data[selector] = TEST_SAAS_DATA["name"]
            elif "url" in field_name or "website" in field_name:
                mapped_data[selector] = TEST_SAAS_DATA["url"]
            elif "email" in field_name:
                mapped_data[selector] = TEST_SAAS_DATA["contact_email"]
            elif "description" in field_name:
                mapped_data[selector] = TEST_SAAS_DATA["description"]
            elif "category" in field_name:
                mapped_data[selector] = TEST_SAAS_DATA["category"]

        # Fill the form
        fill_result = await browser.fill_form(mapped_data, form_structure)

        assert fill_result["filled_count"] > 0, "Should fill at least one field"
        assert fill_result["filled_count"] >= 4, "Should fill at least 4 fields"

        # Verify values were actually filled
        for selector, value in mapped_data.items():
            try:
                element = browser.page.locator(selector).first
                if await element.count() > 0:
                    element_value = await element.input_value()
                    if element_value:  # Some fields might be textarea or select
                        assert (
                            value in element_value or element_value in value
                        ), f"Field {selector} should contain {value}"
            except Exception:
                # Some fields might not have input_value (like file inputs)
                pass

    @pytest.mark.asyncio
    async def test_form_submission(self, browser):
        """Test that forms can be submitted successfully"""
        await browser.start()
        await browser.navigate(TEST_FORM_URL)

        form_structure = await browser.extract_form_fields_dom()

        # Fill form first
        mapped_data = {}
        for field in form_structure.get("fields", []):
            field_name = (field.get("name", "") + " " + field.get("label", "")).lower()
            selector = field.get("selector", "")

            if not selector:
                continue

            if "name" in field_name or "product" in field_name:
                mapped_data[selector] = TEST_SAAS_DATA["name"]
            elif "url" in field_name or "website" in field_name:
                mapped_data[selector] = TEST_SAAS_DATA["url"]
            elif "email" in field_name:
                mapped_data[selector] = TEST_SAAS_DATA["contact_email"]
            elif "description" in field_name:
                mapped_data[selector] = TEST_SAAS_DATA["description"]
            elif "category" in field_name:
                mapped_data[selector] = TEST_SAAS_DATA["category"]

        await browser.fill_form(mapped_data, form_structure)

        # Submit form
        submit_button_selector = None
        if form_structure.get("submit_button"):
            submit_button_selector = form_structure["submit_button"].get("selector")

        submitted = await browser.submit_form(submit_button_selector)
        assert submitted is True, "Form should submit successfully"

        # Wait for confirmation
        confirmation = await browser.wait_for_confirmation()
        assert confirmation["status"] in [
            "success",
            "pending",
        ], f"Submission should succeed or be pending, got: {confirmation['status']}"

    @pytest.mark.asyncio
    async def test_full_workflow_without_ai(self, workflow):
        """Test complete workflow using DOM fallback (no AI)"""
        # Ensure screenshots directory exists
        os.makedirs("./storage/screenshots", exist_ok=True)
        screenshot_path = "./storage/screenshots/test_workflow_dom.png"

        result = await workflow.submit_to_directory(
            directory_url=TEST_FORM_URL,
            saas_data=TEST_SAAS_DATA,
            screenshot_path=screenshot_path,
        )

        assert result["status"] in [
            "success",
            "pending",
        ], f"Workflow should succeed, got: {result['status']}"
        assert result["fields_filled"] > 0, "Should fill at least one field"
        assert result["fields_filled"] >= 4, "Should fill at least 4 fields"
        assert "form_structure" in result, "Result should contain form structure"

        # Verify screenshot was created
        if os.path.exists(screenshot_path):
            assert (
                os.path.getsize(screenshot_path) > 0
            ), "Screenshot should not be empty"
        
        # Save JSON report
        _save_test_report("test_full_workflow_without_ai", result, TEST_SAAS_DATA)

    @pytest.mark.asyncio
    async def test_full_workflow_with_ai(self, workflow):
        """Test complete workflow using AI (requires Ollama)"""
        # Check if Ollama is available
        try:
            form_reader = FormReader()
            if not form_reader.client:
                pytest.skip("Ollama not available. Skipping AI workflow test.")
        except Exception as e:
            pytest.skip(
                f"Ollama initialization failed: {e}. Skipping AI workflow test."
            )

        # Ensure screenshots directory exists
        os.makedirs("./storage/screenshots", exist_ok=True)
        screenshot_path = "./storage/screenshots/test_workflow_ai.png"

        result = await workflow.submit_to_directory(
            directory_url=TEST_FORM_URL,
            saas_data=TEST_SAAS_DATA,
            screenshot_path=screenshot_path,
        )

        # AI might fail, so we check for success or graceful fallback
        assert result["status"] in [
            "success",
            "pending",
            "error",
        ], f"Workflow should return valid status, got: {result['status']}"

        if result["status"] == "error":
            # If AI fails, it should fallback to DOM extraction
            assert (
                "form_structure" in result
            ), "Error result should contain form structure for debugging"
        
        # Save JSON report
        _save_test_report("test_full_workflow_with_ai", result, TEST_SAAS_DATA)

    @pytest.mark.asyncio
    async def test_captcha_detection(self, browser):
        """Test CAPTCHA detection (should not find CAPTCHA on test form)"""
        await browser.start()
        await browser.navigate(TEST_FORM_URL)

        has_captcha = await browser.detect_captcha()
        assert has_captcha is False, "Test form should not have CAPTCHA"

    @pytest.mark.asyncio
    async def test_screenshot_capture(self, browser):
        """Test that screenshots can be captured"""
        os.makedirs("./storage/screenshots", exist_ok=True)
        screenshot_path = "./storage/screenshots/test_screenshot.png"

        await browser.start()
        await browser.navigate(TEST_FORM_URL)
        await browser.take_screenshot(screenshot_path)

        assert os.path.exists(screenshot_path), "Screenshot file should be created"
        assert os.path.getsize(screenshot_path) > 0, "Screenshot should not be empty"

    @pytest.mark.asyncio
    async def test_error_handling_invalid_url(self, workflow):
        """Test error handling for invalid URL"""
        result = await workflow.submit_to_directory(
            directory_url="http://invalid-url-that-does-not-exist-12345.com",
            saas_data=TEST_SAAS_DATA,
        )

        assert result["status"] == "error", "Should return error for invalid URL"
        assert "message" in result, "Error result should contain message"

    @pytest.mark.asyncio
    async def test_error_handling_missing_form(self, workflow):
        """Test error handling when form is not found"""
        # Use a simple URL that doesn't have a form
        # Using a simple example.com page instead of Google (which is too complex)
        import pytest
        import asyncio
        
        # Use a timeout to prevent hanging
        try:
            result = await asyncio.wait_for(
                workflow.submit_to_directory(
                    directory_url="https://example.com",  # Simple page without submission form
                    saas_data=TEST_SAAS_DATA
                ),
                timeout=30.0  # 30 second timeout
            )
        except asyncio.TimeoutError:
            pytest.fail("Test timed out after 30 seconds - workflow is hanging")

        # Should either error or return no fields detected
        assert result["status"] in [
            "error",
            "pending",
        ], f"Should handle missing form gracefully, got status: {result['status']}"
        if result["status"] == "error":
            assert "message" in result, "Error result should contain message"


if __name__ == "__main__":
    # Run tests with: python -m pytest backend/test/test_submission.py -v
    pytest.main([__file__, "-v", "-s"])
