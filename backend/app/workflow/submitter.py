"""
Workflow orchestration for form submissions
Coordinates between AI (BRAIN) and Automation (HANDS)
"""
import os
import time
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
        try:
            self.form_reader = FormReader()
        except Exception as e:
            logger.warning(f"FormReader initialization failed: {e}. Some features may be disabled.")
            self.form_reader = None
    
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
            # Use timeout to prevent hanging on complex pages
            try:
                submission_detected = await self.browser.detect_submission_page()
                if not submission_detected:
                    logger.warning("Could not detect submission form, proceeding anyway")
                else:
                    logger.info("Submission form detected successfully")
                    # If detection clicked a link, wait for page to fully load
                    await self.browser.page.wait_for_load_state("domcontentloaded", timeout=5000)
                    await self.browser.page.wait_for_timeout(2000)  # Extra wait for dynamic content
            except Exception as e:
                logger.warning(f"Error during submission page detection: {e}, proceeding anyway")
                submission_detected = False
            
            # Step 3: Check for CAPTCHA
            has_captcha = await self.browser.detect_captcha()
            if has_captcha:
                logger.warning("CAPTCHA detected - manual intervention may be required")
                return {
                    "status": "captcha_required",
                    "message": "CAPTCHA detected on submission page",
                    "requires_manual_intervention": True,
                    "analysis_method": "unknown"
                }
            
            # Step 4: Get form HTML and analyze with AI or DOM extraction
            # Wait a bit more to ensure page is fully loaded
            await self.browser.page.wait_for_timeout(2000)
            
            html_content = await self.browser.get_page_content()
            logger.debug(f"Retrieved page HTML (length: {len(html_content)} chars)")
            
            # Track if we're using DOM extraction (to skip AI mapping later)
            using_dom_extraction = False
            
            # Try AI analysis first, fallback to DOM extraction
            if not self.form_reader:
                logger.warning("FormReader not available. Using DOM-based form extraction.")
                form_structure = await self.browser.extract_form_fields_dom()
                using_dom_extraction = True
            else:
                form_structure = await self.form_reader.analyze_form(html_content)
                # If AI analysis fails, fallback to DOM extraction
                if form_structure.get("error") or not form_structure.get("fields"):
                    logger.warning("AI form analysis failed or returned no fields. Falling back to DOM extraction.")
                    dom_structure = await self.browser.extract_form_fields_dom()
                    if dom_structure.get("fields"):
                        form_structure = dom_structure
                        using_dom_extraction = True
                        logger.info("Using DOM-extracted form structure")
                    else:
                        logger.error("DOM extraction also returned no fields")
                        # Still use DOM structure for error reporting
                        form_structure = dom_structure
                        using_dom_extraction = True
            
            field_count = len(form_structure.get("fields", []))
            logger.info(f"Form analysis complete. Found {field_count} fields. Method: {'DOM' if using_dom_extraction else 'AI'}")
            
            if field_count == 0:
                logger.error("No form fields detected after all extraction methods")
                # Get page URL for better error message
                current_url = self.browser.page.url
                
                # Try one more time with a longer wait - sometimes forms load very slowly
                logger.info("Retrying field extraction with longer wait...")
                await self.browser.page.wait_for_timeout(3000)
                retry_structure = await self.browser.extract_form_fields_dom()
                retry_count = len(retry_structure.get("fields", []))
                
                if retry_count > 0:
                    logger.info(f"Retry successful! Found {retry_count} fields on second attempt")
                    form_structure = retry_structure
                    using_dom_extraction = True
                    field_count = retry_count
                else:
                    # Still no fields - return error
                    return {
                        "status": "error",
                        "message": f"No form fields detected on page: {current_url}. The page may not contain a form, or the form may be dynamically loaded. Check if the form is in an iframe or requires JavaScript to render.",
                        "form_structure": form_structure,
                        "url": current_url,
                        "analysis_method": "dom" if using_dom_extraction else "ai"
                    }
            
            # Store form_structure for error handling (before any errors might occur)
            self._last_form_structure = form_structure
            
            # Step 5: Map SaaS data to form fields
            # Use DOM-based mapping if we used DOM extraction OR if AI is not available
            if using_dom_extraction or not self.form_reader or form_structure.get("error"):
                logger.warning("FormReader not available or failed. Using enhanced DOM-based field mapping.")
                # Enhanced fallback mapping using purpose field from DOM extraction
                mapped_data = {}
                for field in form_structure.get("fields", []):
                    field_name = (field.get("name", "") + " " + field.get("label", "") + " " + field.get("placeholder", "")).lower()
                    purpose = field.get("purpose", "").lower()
                    selector = field.get("selector", "")
                    
                    if not selector:
                        continue
                    
                    # Use purpose if available, otherwise infer from field name
                    # Check each field type independently (not elif) to ensure all fields are mapped
                    mapped = False
                    
                    if purpose == "name" or any(kw in field_name for kw in ["name", "title", "company", "product", "business", "app"]):
                        if saas_data.get("name"):
                            mapped_data[selector] = saas_data.get("name", "")
                            logger.debug(f"Mapped name to {selector}")
                            mapped = True
                    
                    if not mapped and (purpose == "url" or any(kw in field_name for kw in ["url", "website", "site", "link", "homepage", "domain", "web"])):
                        if saas_data.get("url"):
                            mapped_data[selector] = saas_data.get("url", "")
                            logger.debug(f"Mapped URL to {selector}")
                            mapped = True
                    
                    if not mapped and (purpose == "email" or any(kw in field_name for kw in ["email", "mail", "contact", "e-mail"])):
                        if saas_data.get("contact_email"):
                            mapped_data[selector] = saas_data.get("contact_email", "")
                            logger.debug(f"Mapped email to {selector}")
                            mapped = True
                    
                    if not mapped and (purpose == "description" or any(kw in field_name for kw in ["description", "desc", "about", "details", "info", "summary", "overview"])):
                        if saas_data.get("description"):
                            mapped_data[selector] = saas_data.get("description", "")
                            logger.debug(f"Mapped description to {selector}")
                            mapped = True
                    
                    if not mapped and (purpose == "category" or any(kw in field_name for kw in ["category", "tag", "tags", "type", "industry", "sector"])):
                        if saas_data.get("category"):
                            mapped_data[selector] = saas_data.get("category", "")
                            logger.debug(f"Mapped category to {selector}")
                            mapped = True
                    
                    if not mapped and (purpose == "logo" or any(kw in field_name for kw in ["logo", "image", "picture", "photo", "icon", "upload"])):
                        if saas_data.get("logo_path"):
                            mapped_data[selector] = saas_data.get("logo_path", "")
                            logger.debug(f"Mapped logo to {selector}")
                            mapped = True
                
                logger.info(f"Mapped {len(mapped_data)} fields using enhanced fallback mapping")
            else:
                mapped_data = await self.form_reader.map_data_to_form(form_structure, saas_data)
            
            if not mapped_data:
                logger.warning("No fields could be mapped")
                return {
                    "status": "error",
                    "message": "Could not map SaaS data to form fields",
                    "form_structure": form_structure
                }
            
            # Step 6: Fill form
            # Add analysis method to mapped data (for tracking in form submission)
            analysis_method = "dom" if using_dom_extraction else "ai"
            
            # Set analysis method in hidden field using JavaScript (more reliable)
            try:
                await self.browser.page.evaluate("""
                    (method) => {
                        const field = document.getElementById('analysis_method') || 
                                    document.querySelector('[name="analysis_method"]');
                        if (field) {
                            field.value = method;
                            console.log('Set analysis_method to:', method);
                        }
                    }
                """, analysis_method)
                logger.info(f"Set analysis_method hidden field to: {analysis_method}")
            except Exception as e:
                logger.warning(f"Failed to set analysis_method field: {e}")
            
            # Also add to mapped_data as backup
            try:
                method_field = self.browser.page.locator("#analysis_method")
                if await method_field.count() > 0:
                    mapped_data["#analysis_method"] = analysis_method
                else:
                    method_field = self.browser.page.locator("[name='analysis_method']")
                    if await method_field.count() > 0:
                        mapped_data["[name='analysis_method']"] = analysis_method
            except:
                pass  # Field might not exist, that's okay
            
            fill_result = await self.browser.fill_form(
                mapped_data, 
                form_structure=form_structure
            )
            
            if fill_result["filled_count"] == 0:
                logger.error("No fields were filled")
                return {
                    "status": "error",
                    "message": "Failed to fill any form fields",
                    "fill_result": fill_result,
                    "form_structure": form_structure  # Include for debugging
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
                    "fill_result": fill_result,
                    "form_structure": form_structure  # Include for debugging
                }
            
            # Step 8: Wait for confirmation
            confirmation = await self.browser.wait_for_confirmation()
            
            # Step 9: Take screenshot if requested
            if screenshot_path:
                await self.browser.take_screenshot(screenshot_path)
            
            # Compile result
            analysis_method = "dom" if using_dom_extraction else "ai"
            result = {
                "status": confirmation["status"],
                "message": confirmation["message"],
                "url": confirmation.get("url", directory_url),
                "fields_filled": fill_result["filled_count"],
                "total_fields": fill_result["total_fields"],
                "form_structure": form_structure,
                "fill_errors": fill_result.get("errors", []),
                "analysis_method": analysis_method  # Track which method was used
            }
            
            if result["status"] == "success":
                logger.info("Submission workflow completed successfully")
            else:
                logger.warning(f"Submission workflow completed with status: {result['status']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Submission workflow failed: {str(e)}", exc_info=True)
            
            # Take error screenshot for debugging
            try:
                error_screenshot_path = f"./storage/screenshots/error_{int(time.time())}.png"
                os.makedirs(os.path.dirname(error_screenshot_path), exist_ok=True)
                await self.browser.take_screenshot(error_screenshot_path)
                logger.info(f"Error screenshot saved to {error_screenshot_path}")
            except Exception as screenshot_error:
                logger.warning(f"Failed to take error screenshot: {str(screenshot_error)}")
            
            # Include form_structure if available for debugging
            error_result = {
                "status": "error",
                "message": f"Workflow error: {str(e)}",
                "error_type": type(e).__name__,
                "error_details": str(e),
                "analysis_method": "unknown"  # Default to unknown if we can't determine
            }
            
            # Try to include form_structure if we have it
            try:
                if hasattr(self, '_last_form_structure'):
                    error_result["form_structure"] = self._last_form_structure
                    # Try to determine analysis method from form structure
                    if self._last_form_structure and self._last_form_structure.get("fields"):
                        # If we have fields, we likely used DOM extraction
                        error_result["analysis_method"] = "dom"
            except:
                pass
            
            return error_result
        
        finally:
            await self.browser.close()
    
    async def submit_form(self, saas_url: str, form_data: dict) -> dict:
        """
        Legacy method for backward compatibility
        """
        return await self.submit_to_directory(saas_url, form_data)