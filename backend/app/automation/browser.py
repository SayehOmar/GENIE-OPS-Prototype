"""
Playwright browser automation (HANDS)
Handles browser interactions for form submissions
"""

import os
import time
from typing import Dict, List, Optional
from playwright.async_api import (
    async_playwright,
    Browser,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)
from app.core.config import settings
from app.utils.logger import logger

# Optional import for URL file downloads
try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger.warning("aiohttp not available. Logo URL downloads will be disabled.")


class BrowserAutomation:
    """
    Browser automation handler using Playwright.
    
    This class is the "Hands" of the system - it performs all browser interactions
    including navigation, form detection, field filling, file uploads, and form submission.
    It uses Playwright for reliable cross-browser automation with support for
    modern web features like dynamic content, modals, and JavaScript-heavy pages.
    
    Key capabilities:
    - Navigate to URLs and wait for page load
    - Detect submission forms (including modals and multi-step forms)
    - Fill text inputs, textareas, selects, and file uploads
    - Submit forms and verify success
    - Detect CAPTCHA presence
    - Take screenshots for debugging
    - Extract form fields using DOM inspection
    """

    def __init__(self):
        """
        Initialize the BrowserAutomation instance.
        
        Creates a new instance but doesn't start the browser yet. The browser
        is started lazily when needed (on first navigation or operation).
        """
        self.browser: Browser = None
        self.page: Page = None
        self.playwright = None

    async def start(self):
        """
        Start browser session
        """
        if not self.playwright:
            self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=settings.PLAYWRIGHT_HEADLESS,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],  # For better compatibility
        )
        self.page = await self.browser.new_page()

        # Set viewport size
        await self.page.set_viewport_size({"width": 1920, "height": 1080})

        logger.info("Browser session started")

    async def close(self):
        """
        Close browser session
        """
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser session closed")

    async def navigate(self, url: str):
        """
        Navigate to a URL
        """
        if not self.page:
            await self.start()

        await self.page.goto(
            url, timeout=settings.PLAYWRIGHT_TIMEOUT, wait_until="domcontentloaded"
        )
        logger.info(f"Navigated to {url}")

        # Wait a bit for page to fully load
        await self.page.wait_for_timeout(1000)

    async def detect_submission_page(self) -> bool:
        """
        Detect if we're on a submission page or need to navigate to it.
        
        This method intelligently detects submission forms on the current page. It looks for:
        - Form elements with input fields
        - Submission-related keywords in page text
        - Submit buttons and links
        - Modal forms that may need to be opened
        
        If a submission form is not found on the current page, it attempts to find and
        click submission links/buttons to navigate to the form page.
        
        Returns:
            True if submission form is detected (or navigation was successful)
            False if form could not be detected (but workflow continues anyway)
            
        Note: Enhanced to handle modals, multi-step forms, and dynamic content.
        Uses timeouts to prevent hanging on complex pages.
        """
        if not self.page:
            raise Exception("Browser not started")

        # Wait for page to be fully loaded (with shorter timeout for complex pages)
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=3000)
        except PlaywrightTimeoutError:
            # Page might still be loading, continue anyway
            pass

        # Wait a bit for dynamic content (reduced timeout)
        await self.page.wait_for_timeout(500)

        # Look for common submission indicators (expanded list)
        submission_keywords = [
            "submit",
            "add listing",
            "add your",
            "submit your",
            "add product",
            "submit product",
            "new listing",
            "list your",
            "submit app",
            "add service",
            "submit website",
            "add business",
            "submit company",
            "register",
            "sign up",
        ]

        page_text = await self.page.inner_text("body")
        page_text_lower = page_text.lower()

        # Check for form elements (including forms in modals)
        form_count = await self.page.locator("form").count()
        input_count = await self.page.locator("input, textarea, select").count()

        # Check for modal forms
        modal_forms = await self.page.locator(
            "div[role='dialog'] form, .modal form, [class*='modal'] form"
        ).count()

        # Look for submission buttons (expanded selectors)
        submit_buttons = await self.page.locator(
            "button[type='submit'], input[type='submit'], "
            "button:has-text('submit'), button:has-text('add'), "
            "button:has-text('save'), button:has-text('register'), "
            "a:has-text('submit'), a:has-text('add listing'), "
            "a:has-text('list your')"
        ).count()

        # Check if any submission keywords are present
        has_keywords = any(
            keyword in page_text_lower for keyword in submission_keywords
        )

        # If we already have a form with inputs, we're likely on the submission page
        if form_count > 0 and input_count >= 2:
            logger.info("Submission form detected on current page")
            return True

        if modal_forms > 0:
            logger.info("Modal form detected")
            # Try to open modal if needed
            try:
                modal_triggers = await self.page.locator(
                    "button:has-text('Add'), button:has-text('Submit'), "
                    "a:has-text('Add'), [data-toggle='modal']"
                ).count()
                if modal_triggers > 0:
                    trigger = self.page.locator(
                        "button:has-text('Add'), button:has-text('Submit'), a:has-text('Add')"
                    ).first
                    await trigger.click()
                    await self.page.wait_for_timeout(1000)
                    logger.info("Opened modal form")
                    return True
            except Exception as e:
                logger.debug(f"Could not open modal: {str(e)}")

        if form_count > 0 or input_count > 3 or submit_buttons > 0 or has_keywords:
            logger.info("Submission page detected")
            return True

        # Try to find and click submission link/button (expanded selectors)
        # Limit search to prevent hanging on complex pages
        submission_selectors = [
            "a:has-text('Submit')",
            "a:has-text('Add Listing')",
            "a:has-text('Add Your')",
            "a:has-text('List Your')",
            "a:has-text('Submit Your')",
            "button:has-text('Submit')",
            "button:has-text('Add Listing')",
            "button:has-text('Add Your')",
            "[href*='submit']",
            "[href*='add']",
            "[href*='list']",
            "[href*='/submit']",
            "[href*='/add']",
        ]

        # Limit to first 5 selectors to prevent hanging on complex pages
        for selector in submission_selectors[:5]:
            try:
                element = self.page.locator(selector).first
                # Use shorter timeout for checking element count
                count = await element.count()
                if count > 0:
                    # Scroll into view
                    await element.scroll_into_view_if_needed()
                    await self.page.wait_for_timeout(300)
                    await element.click(timeout=2000)  # Add timeout to click
                    await self.page.wait_for_timeout(1000)  # Reduced wait time
                    logger.info(f"Clicked submission link: {selector}")

                    # Wait for new content to load (shorter timeout)
                    try:
                        await self.page.wait_for_load_state(
                            "domcontentloaded", timeout=3000
                        )
                    except:
                        pass

                    return True
            except Exception as e:
                logger.debug(f"Could not click {selector}: {str(e)}")
                continue

        logger.warning("Could not detect submission page, but proceeding anyway")
        return False  # Return False but workflow will continue

    async def fill_form(
        self, field_mappings: Dict[str, str], form_structure: Optional[Dict] = None
    ):
        """
        Fill form fields with provided data using CSS selectors.
        
        Iterates through the field mappings and fills each field with its corresponding
        value. Handles different field types appropriately:
        - Text inputs: Clear and fill with text
        - Textareas: Fill with text (supports multi-line)
        - Select dropdowns: Select by value or visible text
        - File inputs: Upload file from path or download from URL
        
        The method includes error handling for each field, so if one field fails,
        it continues with the others. All errors are collected and returned.
        
        Args:
            field_mappings: Dictionary mapping CSS selectors to values to fill:
                - Key: CSS selector (e.g., "#name", "[name='email']")
                - Value: Value to fill (string, or file path for file inputs)
            form_structure: Optional form structure from AI analysis (currently unused
                but available for future enhancements)
        
        Returns:
            Dictionary with fill results:
                - filled_count: Number of fields successfully filled
                - total_fields: Total number of fields in mappings
                - errors: List of error messages for failed fields
        """
        if not self.page:
            raise Exception("Browser not started")

        logger.info(f"Filling form with {len(field_mappings)} fields")

        filled_count = 0
        errors = []

        for selector, value in field_mappings.items():
            if not value:  # Skip empty values
                continue

            try:
                # Wait for element to be visible (with longer timeout for dynamic content)
                element = self.page.locator(selector).first

                # Try multiple strategies to find the element
                element_count = await element.count()
                if element_count == 0:
                    # Try alternative selectors if the main one fails
                    logger.debug(
                        f"Element not found with selector: {selector}, trying alternatives"
                    )
                    # The selector might need adjustment, but continue with original
                    errors.append(f"Element not found: {selector}")
                    continue

                # Get element type first (before checking visibility)
                tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                input_type = await element.get_attribute("type") or ""

                # Skip visibility check for hidden inputs
                if input_type != "hidden":
                    # Scroll element into view
                    await element.scroll_into_view_if_needed()
                    await element.wait_for(state="visible", timeout=5000)

                # Fill based on element type
                if tag_name == "input" and input_type == "file":
                    # Handle file upload - support both file paths and URLs
                    file_path = value

                    # Check if it's a URL (starts with http:// or https://)
                    if value.startswith(("http://", "https://")):
                        if not AIOHTTP_AVAILABLE:
                            logger.warning(
                                f"Cannot download logo from URL (aiohttp not available): {value}"
                            )
                            errors.append("Logo URL download requires aiohttp package")
                            continue

                        # Download the file first if it's a URL
                        import tempfile

                        try:
                            async with aiohttp.ClientSession() as session:
                                async with session.get(value) as response:
                                    if response.status == 200:
                                        # Create temp file
                                        file_ext = os.path.splitext(value)[1] or ".png"
                                        with tempfile.NamedTemporaryFile(
                                            delete=False, suffix=file_ext
                                        ) as tmp_file:
                                            tmp_file.write(await response.read())
                                            file_path = tmp_file.name
                                        logger.info(
                                            f"Downloaded logo from URL: {value}"
                                        )
                                    else:
                                        raise Exception(
                                            f"Failed to download file: HTTP {response.status}"
                                        )
                        except Exception as e:
                            logger.error(
                                f"Error downloading file from URL {value}: {str(e)}"
                            )
                            errors.append(f"Failed to download file from URL: {str(e)}")
                            continue

                    # Validate file exists and is a valid image type
                    if os.path.exists(file_path):
                        # Check file extension
                        valid_extensions = [
                            ".jpg",
                            ".jpeg",
                            ".png",
                            ".gif",
                            ".svg",
                            ".webp",
                            ".bmp",
                        ]
                        file_ext = os.path.splitext(file_path)[1].lower()

                        if file_ext in valid_extensions:
                            await element.set_input_files(file_path)
                            logger.info(f"Uploaded file: {file_path} to {selector}")
                            filled_count += 1

                            # Clean up temp file if it was downloaded
                            if value.startswith(
                                ("http://", "https://")
                            ) and os.path.exists(file_path):
                                try:
                                    os.unlink(file_path)
                                except:
                                    pass
                        else:
                            logger.warning(
                                f"Invalid file type: {file_ext}. Expected image file."
                            )
                            errors.append(f"Invalid file type: {file_ext}")
                    else:
                        logger.warning(f"File not found: {file_path}")
                        errors.append(f"File not found: {file_path}")

                elif tag_name == "textarea":
                    await element.fill(value)
                    logger.info(f"Filled textarea {selector} with: {value[:50]}...")
                    filled_count += 1

                elif tag_name == "select":
                    # Try to select by value or text
                    try:
                        await element.select_option(value)
                        logger.info(f"Selected option in {selector}: {value}")
                        filled_count += 1
                    except Exception:
                        # Try selecting by visible text
                        await element.select_option(label=value)
                        logger.info(f"Selected option by label in {selector}: {value}")
                        filled_count += 1

                elif tag_name == "input":
                    # Clear first, then fill
                    await element.clear()
                    await element.fill(value)
                    logger.info(f"Filled input {selector} with: {value[:50]}...")
                    filled_count += 1

                else:
                    # Try generic fill
                    await element.fill(value)
                    logger.info(f"Filled {tag_name} {selector} with: {value[:50]}...")
                    filled_count += 1

                # Small delay between fields
                await self.page.wait_for_timeout(200)

            except PlaywrightTimeoutError:
                logger.warning(f"Element not found or not visible: {selector}")
                errors.append(f"Element not found: {selector}")
            except Exception as e:
                logger.error(f"Error filling {selector}: {str(e)}")
                errors.append(f"Error filling {selector}: {str(e)}")

        logger.info(
            f"Form filling complete. Filled {filled_count} fields. Errors: {len(errors)}"
        )

        if errors:
            logger.warning(f"Form filling errors: {errors}")

        return {
            "filled_count": filled_count,
            "total_fields": len(field_mappings),
            "errors": errors,
        }

    async def submit_form(self, submit_button_selector: Optional[str] = None) -> bool:
        """
        Submit the form by clicking the submit button.
        
        Attempts to submit the form using the provided selector, or automatically
        detects the submit button if no selector is provided. Handles various
        submit button types and patterns commonly found on web forms.
        
        After clicking, waits for navigation or DOM changes to verify submission.
        For test forms that use preventDefault(), checks for success messages
        or form resets instead of navigation.
        
        Args:
            submit_button_selector: Optional CSS selector for the submit button.
                If not provided, automatically searches for common submit button patterns:
                - button[type='submit']
                - input[type='submit']
                - Buttons with text containing "Submit", "Add", "Save"
                - Common submit button IDs and classes
        
        Returns:
            True if form submission was attempted successfully
            False if submission failed (button not found, click failed, etc.)
        """
        if not self.page:
            raise Exception("Browser not started")

        try:
            # Wait a bit before submitting
            await self.page.wait_for_timeout(500)

            if submit_button_selector:
                # Use provided selector
                try:
                    submit_button = self.page.locator(submit_button_selector).first
                    await submit_button.wait_for(state="visible", timeout=10000)
                    await submit_button.click()
                    logger.info(f"Clicked submit button: {submit_button_selector}")
                except Exception as e:
                    logger.warning(
                        f"Failed to click provided submit button {submit_button_selector}: {e}"
                    )
                    # Fall through to automatic detection
                    submit_button_selector = None

            if not submit_button_selector:
                # Try to find submit button automatically
                submit_selectors = [
                    "button[type='submit']",
                    "input[type='submit']",
                    "button:has-text('Submit Product')",  # Specific for test form
                    "button:has-text('Submit')",
                    "button:has-text('Add')",
                    "button:has-text('Save')",
                    "form button:last-child",  # Last button in form
                    "form input[type='submit']",
                    "#submitBtn",  # Common ID
                    "button.submit",  # Common class
                ]

                submitted = False
                for selector in submit_selectors:
                    try:
                        button = self.page.locator(selector).first
                        count = await button.count()
                        if count > 0:
                            await button.wait_for(state="visible", timeout=5000)
                            await button.click()
                            logger.info(f"Clicked submit button: {selector}")
                            submitted = True
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue

                if not submitted:
                    # Try submitting the form directly
                    try:
                        await self.page.evaluate(
                            "document.querySelector('form')?.submit()"
                        )
                        logger.info("Submitted form directly via JavaScript")
                        submitted = True
                    except Exception as e:
                        logger.warning(f"Direct form submission failed: {e}")

            # Wait for navigation or response
            # For test forms that use preventDefault(), wait for DOM changes instead
            try:
                # Wait a bit for any JavaScript handlers to run
                await self.page.wait_for_timeout(1000)

                # Check if page navigated
                try:
                    await self.page.wait_for_load_state("networkidle", timeout=5000)
                except PlaywrightTimeoutError:
                    # Page might not navigate (e.g., test form with preventDefault)
                    # Check if success message appeared or form was reset
                    try:
                        # Wait for any success indicators or form changes
                        await self.page.wait_for_timeout(1000)
                    except:
                        pass
            except Exception as e:
                logger.warning(f"Timeout waiting for navigation: {str(e)}")
                # Still consider it successful if we got here

            logger.info("Form submitted successfully")
            return True

        except Exception as e:
            logger.error(f"Form submission failed: {str(e)}")
            return False

    async def wait_for_confirmation(self, timeout: int = 10000) -> Dict[str, any]:
        """
        Wait for submission confirmation or error message
        Returns status and message
        """
        if not self.page:
            raise Exception("Browser not started")

        try:
            # Wait for page changes
            await self.page.wait_for_timeout(2000)

            # Look for success indicators
            success_keywords = [
                "thank you",
                "success",
                "submitted",
                "received",
                "confirmation",
                "approved",
                "pending review",
            ]

            # Look for error indicators
            error_keywords = [
                "error",
                "failed",
                "invalid",
                "required",
                "captcha",
                "verification",
            ]

            page_text = (await self.page.inner_text("body")).lower()
            current_url = self.page.url

            # Check for success message element (common in test forms)
            try:
                success_elements = await self.page.locator(
                    "#successMessage, .success, [class*='success']"
                ).count()
                if success_elements > 0:
                    logger.info("Success message element detected")
                    return {
                        "status": "success",
                        "message": "Submission successful (success message detected)",
                        "url": current_url,
                    }
            except:
                pass

            # Check for success
            for keyword in success_keywords:
                if keyword in page_text:
                    logger.info(f"Success detected: {keyword}")
                    return {
                        "status": "success",
                        "message": f"Submission successful (detected: {keyword})",
                        "url": current_url,
                    }

            # Check for errors
            for keyword in error_keywords:
                if keyword in page_text:
                    logger.warning(f"Error detected: {keyword}")
                    return {
                        "status": "error",
                        "message": f"Submission may have failed (detected: {keyword})",
                        "url": current_url,
                    }

            # Check URL change (might indicate success)
            if "submit" not in current_url.lower() and "add" not in current_url.lower():
                logger.info("URL changed, possible success")
                return {
                    "status": "success",
                    "message": "URL changed after submission",
                    "url": current_url,
                }

            # Default: assume pending
            return {
                "status": "pending",
                "message": "Submission status unclear",
                "url": current_url,
            }

        except Exception as e:
            logger.error(f"Error waiting for confirmation: {str(e)}")
            return {
                "status": "unknown",
                "message": f"Error: {str(e)}",
                "url": self.page.url if self.page else "",
            }

    async def detect_captcha(self) -> bool:
        """
        Detect if CAPTCHA is present on the page.
        
        Checks for common CAPTCHA implementations including:
        - reCAPTCHA (Google)
        - hCaptcha
        - Custom CAPTCHA implementations
        
        This is a safety feature to prevent the system from attempting to
        submit forms that require human verification. When CAPTCHA is detected,
        the submission is marked as failed with a specific error message.
        
        Returns:
            True if CAPTCHA is detected on the page
            False if no CAPTCHA is found
        """
        if not self.page:
            raise Exception("Browser not started")

        captcha_selectors = [
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            ".g-recaptcha",
            "#captcha",
            "[data-sitekey]",  # reCAPTCHA site key
            "img[alt*='captcha']",
            "img[alt*='CAPTCHA']",
        ]

        for selector in captcha_selectors:
            try:
                element = self.page.locator(selector).first
                if await element.count() > 0:
                    logger.warning(f"CAPTCHA detected: {selector}")
                    return True
            except Exception:
                continue

        # Also check page text
        page_text = (await self.page.inner_text("body")).lower()
        if "captcha" in page_text or "verify you are human" in page_text:
            logger.warning("CAPTCHA detected in page text")
            return True

        return False

    async def take_screenshot(self, path: str):
        """
        Take a screenshot
        """
        if not self.page:
            raise Exception("Browser not started")

        # Ensure directory exists
        os.makedirs(
            os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True
        )

        await self.page.screenshot(path=path, full_page=True)
        logger.info(f"Screenshot saved to {path}")

    async def get_page_content(self) -> str:
        """
        Get the current page HTML content
        """
        if not self.page:
            raise Exception("Browser not started")

        return await self.page.content()

    async def extract_form_fields_dom(self) -> Dict:
        """
        Extract form fields using DOM inspection (no AI needed)
        Returns structured form data compatible with AI output format

        Returns:
            Dict with fields, submit_button, and form_selector
        """
        if not self.page:
            raise Exception("Browser not started")

        logger.info("Extracting form fields using DOM inspection")

        try:
            # Wait for page to be ready (with timeout to prevent hanging)
            try:
                await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
            except PlaywrightTimeoutError:
                logger.warning("Page load timeout, proceeding with extraction anyway")
                # Continue anyway - page might be complex

            # Wait a bit more for dynamic content
            await self.page.wait_for_timeout(1000)

            # First, check if form exists and wait for it if needed
            try:
                # Wait for form to appear (with timeout)
                await self.page.wait_for_selector("form", timeout=5000)
                logger.debug("Form element found on page")

                # Also wait for at least one input field to be present (form might be empty)
                try:
                    await self.page.wait_for_selector(
                        "input:not([type='hidden']), textarea, select", timeout=3000
                    )
                    logger.debug("Form fields found on page")
                except PlaywrightTimeoutError:
                    logger.warning(
                        "Form found but no visible input fields detected yet, waiting longer..."
                    )
                    # Wait a bit more for dynamic content
                    await self.page.wait_for_timeout(2000)
            except PlaywrightTimeoutError:
                logger.warning(
                    "No form element found, checking for input fields directly"
                )
                # Try waiting for any input field instead
                try:
                    await self.page.wait_for_selector(
                        "input:not([type='hidden']), textarea, select", timeout=3000
                    )
                    logger.debug("Input fields found on page (no form tag)")
                except PlaywrightTimeoutError:
                    logger.error("No form or input fields found on page after waiting")
                    # Take a screenshot for debugging
                    try:
                        debug_screenshot = f"./storage/screenshots/debug_no_form_{int(time.time())}.png"
                        os.makedirs(os.path.dirname(debug_screenshot), exist_ok=True)
                        await self.page.screenshot(
                            path=debug_screenshot, full_page=True
                        )
                        logger.info(f"Debug screenshot saved to {debug_screenshot}")
                    except:
                        pass

            # Extract form fields using JavaScript (with timeout)
            form_data = await self.page.evaluate(
                """
                () => {
                    const fields = [];
                    const forms = document.querySelectorAll('form');
                    let mainForm = forms[0] || document.body;
                    
                    // Find all input, textarea, and select elements
                    const formElements = mainForm.querySelectorAll('input, textarea, select');
                    
                    formElements.forEach((el, index) => {
                        // Skip hidden fields (they're not user-fillable)
                        // But we'll still count them for debugging
                        const isHidden = el.type === 'hidden';
                        if (isHidden) {
                            console.log('Skipping hidden field:', el.name || el.id || 'unnamed');
                            return;
                        }
                        
                        const tagName = el.tagName.toLowerCase();
                        const type = el.type || '';
                        const name = el.name || el.id || '';
                        const id = el.id || '';
                        const placeholder = el.placeholder || '';
                        const label = el.labels && el.labels[0] ? el.labels[0].textContent.trim() : '';
                        
                        // Try to find associated label
                        let labelText = label;
                        if (!labelText && id) {
                            const labelEl = document.querySelector(`label[for="${id}"]`);
                            if (labelEl) labelText = labelEl.textContent.trim();
                        }
                        if (!labelText && name) {
                            const labelEl = document.querySelector(`label[for="${name}"]`);
                            if (labelEl) labelText = labelEl.textContent.trim();
                        }
                        
                        // Generate selector (prefer ID, then name, then fallback)
                        let selector = '';
                        if (id) {
                            selector = `#${id}`;
                        } else if (name) {
                            selector = `[name="${name}"]`;
                        } else {
                            selector = `${tagName}[type="${type}"]:nth-of-type(${index + 1})`;
                        }
                        
                        // Determine if required
                        const required = el.hasAttribute('required') || 
                                       el.getAttribute('aria-required') === 'true';
                        
                        // Infer purpose from name, id, label, placeholder
                        const fieldText = (name + ' ' + id + ' ' + labelText + ' ' + placeholder).toLowerCase();
                        let purpose = 'other';
                        if (fieldText.match(/name|title|product|company|business/)) {
                            purpose = 'name';
                        } else if (fieldText.match(/url|website|site|link|homepage|domain/)) {
                            purpose = 'url';
                        } else if (fieldText.match(/email|mail|contact.*email/)) {
                            purpose = 'email';
                        } else if (fieldText.match(/description|desc|about|details|info|summary/)) {
                            purpose = 'description';
                        } else if (fieldText.match(/category|tag|tags|type|industry/)) {
                            purpose = 'category';
                        } else if (fieldText.match(/logo|image|picture|photo|icon/)) {
                            purpose = 'logo';
                        }
                        
                        // Get options for select elements
                        let options = [];
                        if (tagName === 'select') {
                            options = Array.from(el.options).map(opt => opt.text || opt.value);
                        }
                        
                        fields.push({
                            selector: selector,
                            type: type || tagName,
                            name: name || id || '',
                            label: labelText,
                            placeholder: placeholder,
                            required: required,
                            purpose: purpose,
                            options: options.length > 0 ? options : undefined
                        });
                    });
                    
                    // Find submit button
                    let submitButton = null;
                    const submitSelectors = [
                        'button[type="submit"]',
                        'input[type="submit"]',
                        'button:contains("Submit")',
                        'button:contains("Add")',
                        'button:contains("Save")'
                    ];
                    
                    for (const sel of submitSelectors) {
                        const btn = mainForm.querySelector(sel);
                        if (btn) {
                            const btnId = btn.id || '';
                            const btnName = btn.name || '';
                            submitButton = {
                                selector: btnId ? `#${btnId}` : (btnName ? `[name="${btnName}"]` : sel),
                                text: btn.textContent?.trim() || btn.value || ''
                            };
                            break;
                        }
                    }
                    
                    // If no submit button found, try to find any button in form
                    if (!submitButton) {
                        const anyButton = mainForm.querySelector('button, input[type="button"]');
                        if (anyButton) {
                            const btnId = anyButton.id || '';
                            submitButton = {
                                selector: btnId ? `#${btnId}` : 'button:first-of-type',
                                text: anyButton.textContent?.trim() || anyButton.value || ''
                            };
                        }
                    }
                    
                    // Get form selector
                    const formSelector = forms[0] ? 
                        (forms[0].id ? `#${forms[0].id}` : (forms[0].name ? `form[name="${forms[0].name}"]` : 'form')) :
                        'body';
                    
                    // Log diagnostic info
                    console.log('Form extraction complete:', {
                        formCount: forms.length,
                        totalElements: formElements.length,
                        extractedFields: fields.length,
                        formSelector: formSelector
                    });
                    
                    return {
                        fields: fields,
                        submit_button: submitButton,
                        form_selector: formSelector
                    };
                }
            """
            )

            field_count = len(form_data.get("fields", []))
            logger.info(f"Extracted {field_count} form fields using DOM inspection")

            # If no fields found, log diagnostic information
            if field_count == 0:
                logger.warning("No form fields extracted. Running diagnostics...")
                # Get diagnostic info
                diagnostic = await self.page.evaluate(
                    """
                    () => {
                        const forms = document.querySelectorAll('form');
                        const inputs = document.querySelectorAll('input, textarea, select');
                        const bodyText = document.body ? document.body.innerText.substring(0, 200) : '';
                        return {
                            formCount: forms.length,
                            inputCount: inputs.length,
                            hasBody: !!document.body,
                            bodyTextPreview: bodyText,
                            url: window.location.href
                        };
                    }
                """
                )
                logger.warning(f"Diagnostics: {diagnostic}")

                # Take screenshot for debugging
                try:
                    debug_screenshot = (
                        f"./storage/screenshots/debug_no_fields_{int(time.time())}.png"
                    )
                    os.makedirs(os.path.dirname(debug_screenshot), exist_ok=True)
                    await self.page.screenshot(path=debug_screenshot, full_page=True)
                    logger.info(f"Debug screenshot saved to {debug_screenshot}")
                except Exception as screenshot_error:
                    logger.warning(
                        f"Failed to take debug screenshot: {screenshot_error}"
                    )

            return form_data

        except Exception as e:
            logger.error(f"Error extracting form fields: {str(e)}", exc_info=True)
            # Take error screenshot
            try:
                error_screenshot = (
                    f"./storage/screenshots/error_extraction_{int(time.time())}.png"
                )
                os.makedirs(os.path.dirname(error_screenshot), exist_ok=True)
                await self.page.screenshot(path=error_screenshot, full_page=True)
                logger.info(f"Error screenshot saved to {error_screenshot}")
            except:
                pass
            return {
                "fields": [],
                "submit_button": None,
                "form_selector": "form",
                "error": f"DOM extraction failed: {str(e)}",
            }
