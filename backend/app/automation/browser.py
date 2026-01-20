"""
Playwright browser automation (HANDS)
Handles browser interactions for form submissions
"""
import os
import time
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
from app.core.config import settings
from app.utils.logger import logger


class BrowserAutomation:
    """
    Browser automation handler using Playwright
    Handles navigation, form filling, file uploads, and submission
    """
    
    def __init__(self):
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
            args=['--no-sandbox', '--disable-setuid-sandbox']  # For better compatibility
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
        
        await self.page.goto(url, timeout=settings.PLAYWRIGHT_TIMEOUT, wait_until="domcontentloaded")
        logger.info(f"Navigated to {url}")
        
        # Wait a bit for page to fully load
        await self.page.wait_for_timeout(1000)
    
    async def detect_submission_page(self) -> bool:
        """
        Detect if we're on a submission page or need to navigate to it
        Returns True if submission form is found
        """
        if not self.page:
            raise Exception("Browser not started")
        
        # Look for common submission indicators
        submission_keywords = [
            "submit", "add listing", "add your", "submit your", 
            "add product", "submit product", "new listing"
        ]
        
        page_text = await self.page.inner_text("body")
        page_text_lower = page_text.lower()
        
        # Check for form elements
        form_count = await self.page.locator("form").count()
        input_count = await self.page.locator("input, textarea, select").count()
        
        # Look for submission buttons
        submit_buttons = await self.page.locator(
            "button[type='submit'], input[type='submit'], "
            "button:has-text('submit'), button:has-text('add'), "
            "a:has-text('submit'), a:has-text('add listing')"
        ).count()
        
        # Check if any submission keywords are present
        has_keywords = any(keyword in page_text_lower for keyword in submission_keywords)
        
        if form_count > 0 or input_count > 3 or submit_buttons > 0 or has_keywords:
            logger.info("Submission page detected")
            return True
        
        # Try to find and click submission link/button
        submission_selectors = [
            "a:has-text('Submit')",
            "a:has-text('Add Listing')",
            "a:has-text('Add Your')",
            "button:has-text('Submit')",
            "button:has-text('Add Listing')",
            "[href*='submit']",
            "[href*='add']"
        ]
        
        for selector in submission_selectors:
            try:
                element = self.page.locator(selector).first
                if await element.count() > 0:
                    await element.click()
                    await self.page.wait_for_timeout(2000)  # Wait for navigation
                    logger.info(f"Clicked submission link: {selector}")
                    return True
            except Exception:
                continue
        
        logger.warning("Could not detect submission page")
        return False
    
    async def fill_form(self, field_mappings: Dict[str, str], form_structure: Optional[Dict] = None):
        """
        Fill form fields with provided data using selectors from AI analysis
        
        Args:
            field_mappings: Dict mapping CSS selectors to values
            form_structure: Optional form structure from AI analysis
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
                # Wait for element to be visible
                element = self.page.locator(selector).first
                await element.wait_for(state="visible", timeout=5000)
                
                # Get element type
                tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                input_type = await element.get_attribute("type") or ""
                
                # Fill based on element type
                if tag_name == "input" and input_type == "file":
                    # Handle file upload
                    if os.path.exists(value):
                        await element.set_input_files(value)
                        logger.info(f"Uploaded file: {value} to {selector}")
                        filled_count += 1
                    else:
                        logger.warning(f"File not found: {value}")
                        errors.append(f"File not found: {value}")
                
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
        
        logger.info(f"Form filling complete. Filled {filled_count} fields. Errors: {len(errors)}")
        
        if errors:
            logger.warning(f"Form filling errors: {errors}")
        
        return {
            "filled_count": filled_count,
            "total_fields": len(field_mappings),
            "errors": errors
        }
    
    async def submit_form(self, submit_button_selector: Optional[str] = None) -> bool:
        """
        Submit the form
        
        Args:
            submit_button_selector: Optional CSS selector for submit button
        """
        if not self.page:
            raise Exception("Browser not started")
        
        try:
            # Wait a bit before submitting
            await self.page.wait_for_timeout(500)
            
            if submit_button_selector:
                # Use provided selector
                submit_button = self.page.locator(submit_button_selector).first
                await submit_button.wait_for(state="visible", timeout=5000)
                await submit_button.click()
                logger.info(f"Clicked submit button: {submit_button_selector}")
            else:
                # Try to find submit button automatically
                submit_selectors = [
                    "button[type='submit']",
                    "input[type='submit']",
                    "button:has-text('Submit')",
                    "button:has-text('Add')",
                    "button:has-text('Save')",
                    "form button:last-child",  # Last button in form
                    "form input[type='submit']"
                ]
                
                submitted = False
                for selector in submit_selectors:
                    try:
                        button = self.page.locator(selector).first
                        if await button.count() > 0:
                            await button.wait_for(state="visible", timeout=2000)
                            await button.click()
                            logger.info(f"Clicked submit button: {selector}")
                            submitted = True
                            break
                    except Exception:
                        continue
                
                if not submitted:
                    # Try submitting the form directly
                    await self.page.evaluate("document.querySelector('form')?.submit()")
                    logger.info("Submitted form directly")
            
            # Wait for navigation or response
            try:
                await self.page.wait_for_load_state("networkidle", timeout=10000)
            except PlaywrightTimeoutError:
                # Page might not navigate, that's okay
                pass
            
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
                "thank you", "success", "submitted", "received", 
                "confirmation", "approved", "pending review"
            ]
            
            # Look for error indicators
            error_keywords = [
                "error", "failed", "invalid", "required", 
                "captcha", "verification"
            ]
            
            page_text = (await self.page.inner_text("body")).lower()
            current_url = self.page.url
            
            # Check for success
            for keyword in success_keywords:
                if keyword in page_text:
                    logger.info(f"Success detected: {keyword}")
                    return {
                        "status": "success",
                        "message": f"Submission successful (detected: {keyword})",
                        "url": current_url
                    }
            
            # Check for errors
            for keyword in error_keywords:
                if keyword in page_text:
                    logger.warning(f"Error detected: {keyword}")
                    return {
                        "status": "error",
                        "message": f"Submission may have failed (detected: {keyword})",
                        "url": current_url
                    }
            
            # Check URL change (might indicate success)
            if "submit" not in current_url.lower() and "add" not in current_url.lower():
                logger.info("URL changed, possible success")
                return {
                    "status": "success",
                    "message": "URL changed after submission",
                    "url": current_url
                }
            
            # Default: assume pending
            return {
                "status": "pending",
                "message": "Submission status unclear",
                "url": current_url
            }
            
        except Exception as e:
            logger.error(f"Error waiting for confirmation: {str(e)}")
            return {
                "status": "unknown",
                "message": f"Error: {str(e)}",
                "url": self.page.url if self.page else ""
            }
    
    async def detect_captcha(self) -> bool:
        """
        Detect if CAPTCHA is present on the page
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
            "img[alt*='CAPTCHA']"
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
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        
        await self.page.screenshot(path=path, full_page=True)
        logger.info(f"Screenshot saved to {path}")
    
    async def get_page_content(self) -> str:
        """
        Get the current page HTML content
        """
        if not self.page:
            raise Exception("Browser not started")
        
        return await self.page.content()