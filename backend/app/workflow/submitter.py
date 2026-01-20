"""
Workflow orchestration for form submissions
Coordinates between AI (BRAIN) and Automation (HANDS)
"""
from typing import Dict, Optional
from app.automation.browser import BrowserAutomation
from app.ai.form_reader import FormReader
from app.utils.logger import logger


class SubmissionWorkflow:
    """
    Orchestrates the submission workflow
    """
    
    def __init__(self):
        self.browser = BrowserAutomation()
        self.form_reader = FormReader()
    
    async def submit_to_directory(
        self, 
        directory_url: str, 
        saas_data: Dict,
        screenshot_path: Optional[str] = None
    ) -> Dict:
        """
        Complete workflow for form submission:
        1. Navigate to directory submission page
        2. Detect submission form
        3. Analyze form with AI
        4. Map SaaS data to form fields
        5. Fill and submit form
        6. Verify submission
        7. Handle CAPTCHA detection
        
        Args:
            directory_url: URL of the directory submission page
            saas_data: Dictionary containing SaaS product data (name, url, email, description, category, logo_path)
            screenshot_path: Optional path to save screenshot after submission
        
        Returns:
            Dict with status, message, and details
        """
        try:
            logger.info(f"Starting submission workflow for {directory_url}")
            
            # Step 1: Navigate to directory
            await self.browser.navigate(directory_url)
            
            # Step 2: Detect submission page (may need to click "Submit" link)
            submission_detected = await self.browser.detect_submission_page()
            if not submission_detected:
                logger.warning("Could not detect submission form, proceeding anyway")
            
            # Step 3: Check for CAPTCHA
            has_captcha = await self.browser.detect_captcha()
            if has_captcha:
                logger.warning("CAPTCHA detected - manual intervention may be required")
                return {
                    "status": "captcha_required",
                    "message": "CAPTCHA detected on submission page",
                    "requires_manual_intervention": True
                }
            
            # Step 4: Get form HTML and analyze with AI
            html_content = await self.browser.get_page_content()
            form_structure = await self.form_reader.analyze_form(html_content)
            
            if form_structure.get("error"):
                logger.error(f"Form analysis failed: {form_structure.get('error')}")
                return {
                    "status": "error",
                    "message": f"Form analysis failed: {form_structure.get('error')}",
                    "form_structure": form_structure
                }
            
            if not form_structure.get("fields"):
                logger.warning("No form fields detected")
                return {
                    "status": "error",
                    "message": "No form fields detected on page",
                    "form_structure": form_structure
                }
            
            # Step 5: Map SaaS data to form fields
            mapped_data = await self.form_reader.map_data_to_form(form_structure, saas_data)
            
            if not mapped_data:
                logger.warning("No fields could be mapped")
                return {
                    "status": "error",
                    "message": "Could not map SaaS data to form fields",
                    "form_structure": form_structure
                }
            
            # Step 6: Fill form
            fill_result = await self.browser.fill_form(
                mapped_data, 
                form_structure=form_structure
            )
            
            if fill_result["filled_count"] == 0:
                logger.error("No fields were filled")
                return {
                    "status": "error",
                    "message": "Failed to fill any form fields",
                    "fill_result": fill_result
                }
            
            # Step 7: Submit form
            submit_button_selector = None
            if form_structure.get("submit_button"):
                submit_button_selector = form_structure["submit_button"].get("selector")
            
            submitted = await self.browser.submit_form(submit_button_selector)
            
            if not submitted:
                logger.error("Form submission failed")
                return {
                    "status": "error",
                    "message": "Failed to submit form",
                    "fill_result": fill_result
                }
            
            # Step 8: Wait for confirmation
            confirmation = await self.browser.wait_for_confirmation()
            
            # Step 9: Take screenshot if requested
            if screenshot_path:
                await self.browser.take_screenshot(screenshot_path)
            
            # Compile result
            result = {
                "status": confirmation["status"],
                "message": confirmation["message"],
                "url": confirmation.get("url", directory_url),
                "fields_filled": fill_result["filled_count"],
                "total_fields": fill_result["total_fields"],
                "form_structure": form_structure,
                "fill_errors": fill_result.get("errors", [])
            }
            
            if result["status"] == "success":
                logger.info("Submission workflow completed successfully")
            else:
                logger.warning(f"Submission workflow completed with status: {result['status']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Submission workflow failed: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Workflow error: {str(e)}",
                "error_type": type(e).__name__
            }
        
        finally:
            await self.browser.close()
    
    async def submit_form(self, saas_url: str, form_data: dict) -> dict:
        """
        Legacy method for backward compatibility
        """
        return await self.submit_to_directory(saas_url, form_data)