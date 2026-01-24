"""
Browser worker process that runs Playwright in isolation.

This module runs in a separate process to avoid Windows threading issues.
Each worker process handles one browser operation at a time.
"""

import os
import sys
import asyncio
import traceback
from typing import Dict, Any, Optional
from multiprocessing import Queue
from playwright.async_api import (
    async_playwright,
    Browser,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)
from app.core.config import settings
from app.automation.commands import BrowserCommand, BrowserResult
from app.utils.logger import logger

# Optional import for URL file downloads
try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


class BrowserWorker:
    """
    Browser worker that runs in a separate process.

    This worker handles all Playwright operations in isolation,
    avoiding Windows threading issues. It receives commands via
    a queue and returns results via another queue.
    """

    def __init__(self, command_queue: Queue, result_queue: Queue, worker_id: int):
        """
        Initialize the browser worker.

        Args:
            command_queue: Queue to receive commands from main process
            result_queue: Queue to send results back to main process
            worker_id: Unique identifier for this worker
        """
        self.command_queue = command_queue
        self.result_queue = result_queue
        self.worker_id = worker_id
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.current_url: Optional[str] = (
            None  # Track current URL to re-navigate if page closes
        )
        self.is_running = False

    async def initialize_browser(self):
        """
        Initialize Playwright and browser instance.
        Called lazily on first command or when page is closed.
        """
        # Clean up existing browser if it exists but is invalid
        if self.page:
            try:
                # Test if page is still valid by checking URL
                _ = self.page.url
                # Page is valid, no need to reinitialize
                logger.debug(
                    f"Browser worker {self.worker_id} browser already initialized and valid (URL: {self.page.url})"
                )
                return
            except Exception as e:
                # Page is invalid, clean up before reinitializing
                logger.warning(
                    f"Browser worker {self.worker_id} existing page is invalid ({str(e)}), cleaning up..."
                )
                try:
                    await self.cleanup_browser(
                        full_cleanup=False
                    )  # Keep browser alive, just close page
                except:
                    pass  # Ignore cleanup errors

        try:
            logger.info(f"Browser worker {self.worker_id} initializing Playwright...")
            if not self.playwright:
                self.playwright = await async_playwright().start()

            logger.info(
                f"Browser worker {self.worker_id} launching Chromium (headless={settings.PLAYWRIGHT_HEADLESS})..."
            )
            if not self.browser:
                self.browser = await self.playwright.chromium.launch(
                    headless=settings.PLAYWRIGHT_HEADLESS,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                    ],
                )

            logger.info(f"Browser worker {self.worker_id} creating new page...")
            # Close old page if it exists but is invalid (shouldn't happen after cleanup, but just in case)
            if self.page:
                try:
                    await self.page.close()
                except:
                    pass
                self.page = None

            self.page = await self.browser.new_page()
            await self.page.set_viewport_size({"width": 1920, "height": 1080})

            # Set up page event listeners to detect if page closes unexpectedly
            def on_page_close(page):
                logger.warning(
                    f"Browser worker {self.worker_id} page closed unexpectedly"
                )
                self.page = None

            self.page.on("close", on_page_close)

            # Verify page is ready
            current_url = self.page.url
            logger.info(
                f"Browser worker {self.worker_id} initialized successfully (headless={settings.PLAYWRIGHT_HEADLESS}, initial URL: {current_url})"
            )
        except Exception as e:
            logger.error(f"Browser worker {self.worker_id} initialization failed: {e}")
            import traceback

            traceback.print_exc()
            raise

    async def cleanup_browser(self, full_cleanup: bool = False):
        """
        Clean up browser resources.

        Args:
            full_cleanup: If True, closes browser and playwright (on shutdown).
                         If False, only closes page (for page reinitialization).
        """
        try:
            if self.page:
                try:
                    # Check if page is still valid before closing
                    _ = self.page.url
                    await self.page.close()
                except:
                    pass  # Page already closed or invalid
                self.page = None

            if full_cleanup:
                # Full cleanup on shutdown
                if self.browser:
                    await self.browser.close()
                    self.browser = None
                if self.playwright:
                    await self.playwright.stop()
                    self.playwright = None
                logger.info(f"Browser worker {self.worker_id} fully cleaned up")
            else:
                # Partial cleanup - just page, keep browser alive
                logger.debug(
                    f"Browser worker {self.worker_id} page cleaned up (browser kept alive)"
                )
        except Exception as e:
            logger.error(f"Error cleaning up browser worker {self.worker_id}: {e}")

    async def handle_command(self, command: BrowserCommand) -> BrowserResult:
        """
        Handle a browser command and return result.

        Args:
            command: BrowserCommand to execute

        Returns:
            BrowserResult with command execution result
        """
        try:
            command_type = command.command_type
            params = command.params

            if command_type == "navigate":
                return await self._handle_navigate(command.command_id, params)
            elif command_type == "fill_form":
                return await self._handle_fill_form(command.command_id, params)
            elif command_type == "submit_form":
                return await self._handle_submit_form(command.command_id, params)
            elif command_type == "detect_captcha":
                return await self._handle_detect_captcha(command.command_id, params)
            elif command_type == "get_page_content":
                return await self._handle_get_page_content(command.command_id, params)
            elif command_type == "extract_form_fields_dom":
                return await self._handle_extract_form_fields_dom(
                    command.command_id, params
                )
            elif command_type == "take_screenshot":
                return await self._handle_take_screenshot(command.command_id, params)
            elif command_type == "detect_submission_page":
                return await self._handle_detect_submission_page(
                    command.command_id, params
                )
            elif command_type == "wait_for_confirmation":
                return await self._handle_wait_for_confirmation(
                    command.command_id, params
                )
            elif command_type == "close":
                return await self._handle_close(command.command_id, params)
            else:
                return BrowserResult.error_result(
                    command.command_id,
                    f"Unknown command type: {command_type}",
                    "UnknownCommandError",
                )
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            logger.error(
                f"Browser worker {self.worker_id} error handling {command.command_type}: {error_msg}\n{error_trace}"
            )
            return BrowserResult.error_result(
                command.command_id, error_msg, type(e).__name__
            )

    async def _handle_navigate(self, command_id: str, params: Dict) -> BrowserResult:
        """Handle navigate command"""
        # Initialize browser lazily on first navigation command
        if not self.page or not self.browser:
            try:
                await self.initialize_browser()
            except Exception as e:
                logger.error(
                    f"Browser worker {self.worker_id} failed to initialize: {e}"
                )
                return BrowserResult.error_result(
                    command_id,
                    f"Failed to initialize browser: {str(e)}",
                    "BrowserInitFailed",
                )

        # Verify page is still valid
        try:
            _ = self.page.url
        except Exception:
            # Page was closed, reinitialize
            logger.warning(
                f"Browser worker {self.worker_id} page was closed, reinitializing..."
            )
            try:
                await self.initialize_browser()
            except Exception as e:
                return BrowserResult.error_result(
                    command_id,
                    f"Failed to reinitialize browser: {str(e)}",
                    "BrowserReinitFailed",
                )

        url = params.get("url")
        if not url:
            return BrowserResult.error_result(
                command_id, "No URL provided", "MissingURL"
            )

        try:
            # Navigate with proper error handling
            response = await self.page.goto(
                url, timeout=settings.PLAYWRIGHT_TIMEOUT, wait_until="domcontentloaded"
            )

            # Verify navigation actually succeeded
            if response is None:
                return BrowserResult.error_result(
                    command_id,
                    f"Navigation to {url} returned None (page may not have loaded)",
                    "NavigationFailed",
                )

            # Check response status
            status = response.status
            if status >= 400:
                return BrowserResult.error_result(
                    command_id,
                    f"Navigation failed with HTTP {status}",
                    f"HTTPError{status}",
                )

            # Verify we're actually on the target URL (or redirected to it)
            final_url = self.page.url
            if not final_url or final_url == "about:blank":
                return BrowserResult.error_result(
                    command_id,
                    f"Navigation failed - page is blank or URL is invalid",
                    "InvalidPageState",
                )

            # Wait for page to be ready
            await self.page.wait_for_timeout(1000)

            # Get page title and basic info for verification
            try:
                page_title = await self.page.title()
            except:
                page_title = "Unknown"

            logger.info(
                f"Successfully navigated to {url} (final URL: {final_url}, status: {status})"
            )

            # Store current URL for potential re-navigation
            self.current_url = final_url

            return BrowserResult.success(
                command_id,
                {
                    "url": url,
                    "final_url": final_url,
                    "status": status,
                    "title": page_title,
                },
            )

        except PlaywrightTimeoutError as e:
            return BrowserResult.error_result(
                command_id, f"Navigation timeout: {str(e)}", "TimeoutError"
            )
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Navigation error: {error_msg}")
            return BrowserResult.error_result(
                command_id, f"Navigation failed: {error_msg}", type(e).__name__
            )

    async def _handle_fill_form(self, command_id: str, params: Dict) -> BrowserResult:
        """Handle fill_form command"""
        # Check if page exists and is still open
        if not self.page:
            # Try to reinitialize
            try:
                await self.initialize_browser()
            except Exception as e:
                return BrowserResult.error_result(
                    command_id,
                    f"Browser not initialized and reinitialization failed: {str(e)}",
                    "BrowserNotInitialized",
                )

        # Verify page is still open
        try:
            # Quick check to see if page is still valid
            await self.page.url
        except Exception as e:
            # Page was closed, reinitialize and re-navigate if we have a URL
            logger.warning(
                f"Page was closed, reinitializing browser for worker {self.worker_id}"
            )
            try:
                await self.initialize_browser()
                # Re-navigate if we have a stored URL
                if self.current_url:
                    logger.info(
                        f"Re-navigating to {self.current_url} after page was closed"
                    )
                    try:
                        response = await self.page.goto(
                            self.current_url,
                            timeout=settings.PLAYWRIGHT_TIMEOUT,
                            wait_until="domcontentloaded",
                        )
                        await self.page.wait_for_timeout(1000)
                        # Update current_url after re-navigation to ensure it's set
                        final_url = self.page.url
                        self.current_url = final_url
                        logger.info(f"Successfully re-navigated to {self.current_url}")
                    except Exception as nav_error:
                        logger.error(
                            f"Failed to re-navigate to {self.current_url}: {nav_error}"
                        )
                        return BrowserResult.error_result(
                            command_id,
                            f"Page was closed and re-navigation failed: {str(nav_error)}",
                            "PageClosed",
                        )
            except Exception as reinit_error:
                return BrowserResult.error_result(
                    command_id,
                    f"Page was closed and reinitialization failed: {str(reinit_error)}",
                    "PageClosed",
                )

        field_mappings = params.get("field_mappings", {})
        filled_count = 0
        errors = []

        logger.info(
            f"Worker {self.worker_id} attempting to fill {len(field_mappings)} fields"
        )

        for selector, value in field_mappings.items():
            if not value:
                continue

            try:
                element = self.page.locator(selector).first
                element_count = await element.count()
                if element_count == 0:
                    errors.append(f"Element not found: {selector}")
                    logger.debug(
                        f"Worker {self.worker_id}: Element not found for selector: {selector}"
                    )
                    continue

                logger.debug(
                    f"Worker {self.worker_id}: Found element for {selector}, attempting to fill with value: {value[:50] if value else 'empty'}"
                )

                tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                input_type = await element.get_attribute("type") or ""

                logger.debug(
                    f"Worker {self.worker_id}: Element {selector} is {tag_name}, type={input_type}"
                )

                if input_type != "hidden":
                    await element.scroll_into_view_if_needed()
                    await element.wait_for(state="visible", timeout=5000)

                if tag_name == "input" and input_type == "file":
                    # Handle file upload
                    file_path = value
                    if value.startswith(("http://", "https://")):
                        if not AIOHTTP_AVAILABLE:
                            errors.append("Logo URL download requires aiohttp package")
                            continue

                        import tempfile

                        async with aiohttp.ClientSession() as session:
                            async with session.get(value) as response:
                                if response.status == 200:
                                    file_ext = os.path.splitext(value)[1] or ".png"
                                    with tempfile.NamedTemporaryFile(
                                        delete=False, suffix=file_ext
                                    ) as tmp_file:
                                        tmp_file.write(await response.read())
                                        file_path = tmp_file.name
                                else:
                                    raise Exception(
                                        f"Failed to download file: HTTP {response.status}"
                                    )

                    if os.path.exists(file_path):
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
                            filled_count += 1
                            # Clean up temp file if downloaded
                            if value.startswith(
                                ("http://", "https://")
                            ) and os.path.exists(file_path):
                                try:
                                    os.unlink(file_path)
                                except:
                                    pass
                        else:
                            errors.append(f"Invalid file type: {file_ext}")
                    else:
                        errors.append(f"File not found: {file_path}")

                elif tag_name == "textarea":
                    await element.clear()
                    await element.fill(value)
                    # Verify value was set
                    try:
                        actual_value = await element.input_value()
                        if actual_value != value:
                            logger.warning(
                                f"Worker {self.worker_id}: Textarea value didn't stick for {selector}, retrying..."
                            )
                            await element.clear()
                            await element.fill(value)
                            await self.page.wait_for_timeout(300)
                        filled_count += 1
                    except:
                        filled_count += 1  # Assume it worked if we can't verify

                elif tag_name == "select":
                    try:
                        # Try to select by value first
                        await element.select_option(value, timeout=10000)
                        filled_count += 1
                        logger.debug(
                            f"Worker {self.worker_id}: Selected option by value: {value}"
                        )
                    except Exception as value_error:
                        try:
                            # Try to select by label
                            await element.select_option(label=value, timeout=10000)
                            filled_count += 1
                            logger.debug(
                                f"Worker {self.worker_id}: Selected option by label: {value}"
                            )
                        except Exception as label_error:
                            # Try to find a partial match in options
                            try:
                                options = await element.evaluate(
                                    """
                                    (el) => {
                                        return Array.from(el.options).map(opt => ({
                                            value: opt.value,
                                            text: opt.text.trim()
                                        }));
                                    }
                                """
                                )

                                # Try to find a match (case-insensitive, partial)
                                value_lower = value.lower()
                                matched = False
                                for opt in options:
                                    if (
                                        opt["value"].lower() == value_lower
                                        or opt["text"].lower() == value_lower
                                        or value_lower in opt["text"].lower()
                                        or opt["text"].lower() in value_lower
                                    ):
                                        await element.select_option(
                                            opt["value"], timeout=10000
                                        )
                                        filled_count += 1
                                        logger.info(
                                            f"Worker {self.worker_id}: Matched '{value}' to option '{opt['text']}' (value: {opt['value']})"
                                        )
                                        matched = True
                                        break

                                if not matched:
                                    errors.append(
                                        f"Could not find matching option for select {selector} with value '{value}'. Available options: {[opt['text'] for opt in options[:5]]}"
                                    )
                                    logger.warning(
                                        f"Worker {self.worker_id}: No match for select {selector} value '{value}'"
                                    )
                            except Exception as match_error:
                                errors.append(
                                    f"Error selecting option '{value}' in {selector}: {str(match_error)}"
                                )
                                logger.warning(
                                    f"Worker {self.worker_id}: Failed to select option: {str(match_error)}"
                                )

                elif tag_name == "input":
                    # Clear and fill, then verify the value was set
                    await element.clear()
                    await element.fill(value)
                    # Verify the value was actually set (important for required fields)
                    try:
                        actual_value = await element.input_value()
                        if actual_value != value:
                            # Value didn't stick, try again
                            logger.warning(
                                f"Worker {self.worker_id}: Value didn't stick for {selector}, retrying..."
                            )
                            await element.clear()
                            await element.fill(value)
                            await self.page.wait_for_timeout(300)
                            actual_value = await element.input_value()
                            if actual_value != value:
                                errors.append(
                                    f"Value not set correctly for {selector}: expected '{value}', got '{actual_value}'"
                                )
                                continue
                        filled_count += 1
                        logger.debug(
                            f"Worker {self.worker_id}: Verified value set for {selector}: '{actual_value}'"
                        )
                    except Exception as verify_error:
                        # If we can't verify, assume it worked
                        filled_count += 1
                        logger.debug(
                            f"Worker {self.worker_id}: Could not verify value for {selector}: {verify_error}"
                        )

                else:
                    await element.fill(value)
                    filled_count += 1

                await self.page.wait_for_timeout(200)

            except PlaywrightTimeoutError as e:
                error_msg = f"Element not found or not visible: {selector}"
                errors.append(error_msg)
                logger.warning(
                    f"Worker {self.worker_id}: Timeout filling {selector}: {str(e)}"
                )
            except Exception as e:
                error_msg = f"Error filling {selector}: {str(e)}"
                errors.append(error_msg)
                logger.warning(
                    f"Worker {self.worker_id}: Exception filling {selector}: {str(e)}"
                )

        logger.info(
            f"Worker {self.worker_id} fill_form complete: "
            f"filled {filled_count}/{len(field_mappings)} fields, "
            f"{len(errors)} errors"
        )
        if errors:
            logger.warning(
                f"Worker {self.worker_id} fill_form errors: {errors[:5]}"
            )  # Log first 5 errors

        return BrowserResult.success(
            command_id,
            {
                "filled_count": filled_count,
                "total_fields": len(field_mappings),
                "errors": errors,
            },
        )

    async def _handle_submit_form(self, command_id: str, params: Dict) -> BrowserResult:
        """Handle submit_form command"""
        # Get form URL from params if provided (fallback if current_url not set)
        form_url = params.get("form_url")
        if form_url and not self.current_url:
            self.current_url = form_url
            logger.info(f"Worker {self.worker_id}: Using form URL from params: {form_url}")
        
        # Initialize browser if needed
        if not self.page:
            try:
                await self.initialize_browser()
                # If we have a stored URL, navigate to it
                if self.current_url:
                    logger.info(
                        f"Worker {self.worker_id}: Navigating to stored URL before submit: {self.current_url}"
                    )
                    await self.page.goto(
                        self.current_url,
                        timeout=settings.PLAYWRIGHT_TIMEOUT,
                        wait_until="domcontentloaded",
                    )
                    await self.page.wait_for_timeout(2000)
            except Exception as e:
                return BrowserResult.error_result(
                    command_id,
                    f"Browser not initialized and initialization failed: {str(e)}",
                    "BrowserNotInitialized",
                )

        # Verify page is still on the form and re-navigate if needed
        try:
            current_url = self.page.url
            # Check if we need to re-navigate
            needs_navigation = False
            
            # If no current_url is stored, try to get it from the page
            if not self.current_url:
                if current_url and current_url != "about:blank" and "localhost:5500" in current_url:
                    # Use current page URL as fallback if it looks like the form URL
                    self.current_url = current_url
                    logger.info(f"Worker {self.worker_id}: No stored URL, using current page URL: {self.current_url}")
                else:
                    logger.warning(f"Worker {self.worker_id}: No stored URL and page is on {current_url}")
                    # Don't fail immediately - try to continue if page looks valid
                    if current_url and current_url != "about:blank":
                        self.current_url = current_url
                        logger.info(f"Worker {self.worker_id}: Using current page URL as fallback: {self.current_url}")
                    else:
                        return BrowserResult.error_result(
                            command_id,
                            f"No stored URL available for form submission (current page: {current_url}). Worker may not have navigated to form yet.",
                            "NoURL"
                        )

            if current_url == "about:blank" or (current_url != self.current_url and "localhost:5500" not in current_url):
                needs_navigation = True
                logger.info(
                    f"Worker {self.worker_id}: Page is not on form URL (current: {current_url}, expected: {self.current_url}), re-navigating..."
                )

            if needs_navigation:
                await self.page.goto(
                    self.current_url,
                    timeout=settings.PLAYWRIGHT_TIMEOUT,
                    wait_until="domcontentloaded",
                )
                await self.page.wait_for_timeout(2000)
                # Update current_url after navigation
                final_url = self.page.url
                self.current_url = final_url
                # Wait for form to be present
                try:
                    await self.page.wait_for_selector("form", timeout=5000)
                except:
                    pass  # Form might already be there
        except Exception as e:
            logger.warning(
                f"Worker {self.worker_id}: Could not verify/navigate to page URL: {e}"
            )
            # Try to navigate anyway if we have a URL
            if self.current_url:
                try:
                    await self.page.goto(
                        self.current_url,
                        timeout=settings.PLAYWRIGHT_TIMEOUT,
                        wait_until="domcontentloaded",
                    )
                    await self.page.wait_for_timeout(2000)
                    # Update current_url after navigation
                    final_url = self.page.url
                    self.current_url = final_url
                except Exception as nav_error:
                    return BrowserResult.error_result(
                        command_id,
                        f"Failed to navigate to form URL: {str(nav_error)}",
                        "NavigationError",
                    )

        # Wait for page to be fully loaded and form to be ready
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
        except:
            pass

        # Wait a bit for any animations or dynamic content
        await self.page.wait_for_timeout(1000)

        # Verify form exists on the page
        try:
            form_count = await self.page.locator("form").count()
            if form_count == 0:
                logger.warning(
                    f"Worker {self.worker_id}: No form found on page, waiting and retrying..."
                )
                await self.page.wait_for_timeout(2000)
                form_count = await self.page.locator("form").count()
                if form_count == 0:
                    return BrowserResult.error_result(
                        command_id,
                        "Form not found on page - cannot submit",
                        "FormNotFound",
                    )
        except Exception as e:
            logger.warning(
                f"Worker {self.worker_id}: Could not verify form presence: {e}"
            )

        submit_button_selector = params.get("submit_button_selector")
        submitted = False
        submit_error = None

        # Try provided selector first
        if submit_button_selector:
            try:
                logger.info(
                    f"Worker {self.worker_id}: Attempting to submit using provided selector: {submit_button_selector}"
                )
                submit_button = self.page.locator(submit_button_selector).first
                count = await submit_button.count()
                if count > 0:
                    await submit_button.scroll_into_view_if_needed()
                    await submit_button.wait_for(state="visible", timeout=10000)
                    await submit_button.wait_for(state="attached", timeout=5000)
                    await submit_button.click(timeout=10000)
                    submitted = True
                    logger.info(
                        f"Worker {self.worker_id}: Successfully clicked submit button using selector: {submit_button_selector}"
                    )
                else:
                    logger.warning(
                        f"Worker {self.worker_id}: Submit button not found with selector: {submit_button_selector}"
                    )
            except Exception as e:
                submit_error = str(e)
                logger.warning(
                    f"Worker {self.worker_id}: Failed to click submit with provided selector: {submit_error}"
                )
                submit_button_selector = None

        # Try common submit button selectors
        if not submitted:
            submit_selectors = [
                "button[type='submit']",  # Most common
                "form button[type='submit']",  # Within form
                "#submissionForm button[type='submit']",  # Specific form ID
                "button:has-text('Submit Product')",  # Text match
                "button:has-text('Submit')",  # Generic submit text
                "input[type='submit']",  # Input submit button
                "form button",  # Any button in form
                "button:has-text('Add')",  # Alternative text
                "button:has-text('Save')",  # Alternative text
            ]

            logger.info(
                f"Worker {self.worker_id}: Trying common submit button selectors..."
            )
            for selector in submit_selectors:
                try:
                    button = self.page.locator(selector).first
                    count = await button.count()
                    if count > 0:
                        # Verify button is actually visible and enabled
                        is_visible = await button.is_visible()
                        is_enabled = await button.is_enabled()

                        if not is_visible:
                            logger.debug(
                                f"Worker {self.worker_id}: Button found with {selector} but not visible, trying next selector..."
                            )
                            continue

                        if not is_enabled:
                            logger.debug(
                                f"Worker {self.worker_id}: Button found with {selector} but disabled, waiting..."
                            )
                            await self.page.wait_for_timeout(1000)
                            is_enabled = await button.is_enabled()
                            if not is_enabled:
                                logger.debug(
                                    f"Worker {self.worker_id}: Button still disabled, trying next selector..."
                                )
                                continue

                        logger.info(
                            f"Worker {self.worker_id}: Found submit button with selector: {selector} (visible: {is_visible}, enabled: {is_enabled})"
                        )
                        await button.scroll_into_view_if_needed()
                        await button.wait_for(state="visible", timeout=10000)
                        await button.wait_for(state="attached", timeout=5000)

                        # Wait a bit for any animations
                        await self.page.wait_for_timeout(500)

                        # Try multiple click methods
                        try:
                            # Method 1: Normal click
                            await button.click(timeout=10000)
                            logger.info(
                                f"Worker {self.worker_id}: Clicked button using normal click"
                            )
                        except Exception as click_error:
                            try:
                                # Method 2: Force click
                                await button.click(force=True, timeout=10000)
                                logger.info(
                                    f"Worker {self.worker_id}: Clicked button using force click"
                                )
                            except Exception as force_error:
                                # Method 3: JavaScript click to ensure event handlers are called
                                await self.page.evaluate(
                                    """
                                    (selector) => {
                                        const button = document.querySelector(selector);
                                        if (button) {
                                            // Create and dispatch click event
                                            const clickEvent = new MouseEvent('click', {
                                                bubbles: true,
                                                cancelable: true,
                                                view: window,
                                                buttons: 1
                                            });
                                            button.dispatchEvent(clickEvent);
                                            return true;
                                        }
                                        return false;
                                    }
                                """,
                                    selector,
                                )
                                logger.info(
                                    f"Worker {self.worker_id}: Clicked button using JavaScript event"
                                )

                        submitted = True
                        logger.info(
                            f"Worker {self.worker_id}: Successfully triggered submit button: {selector}"
                        )

                        # Wait for form submission to process (form might have async submission)
                        await self.page.wait_for_timeout(2000)

                        # Verify form was submitted by checking if success/error message appeared
                        # Wait a bit more for async operations
                        await self.page.wait_for_timeout(2000)
                        try:
                            # Check if form is still present (if gone, likely submitted)
                            form_count = await self.page.locator("form").count()

                            success_msg = await self.page.locator(
                                "#successMessage"
                            ).count()
                            error_msg = await self.page.locator("#errorMessage").count()

                            if success_msg > 0:
                                success_visible = await self.page.locator(
                                    "#successMessage"
                                ).first.is_visible()
                                if success_visible:
                                    logger.info(
                                        f"Worker {self.worker_id}: Success message appeared and is visible after submit"
                                    )
                            elif error_msg > 0:
                                error_visible = await self.page.locator(
                                    "#errorMessage"
                                ).first.is_visible()
                                if error_visible:
                                    error_text = await self.page.locator(
                                        "#errorMessage"
                                    ).inner_text()
                                    logger.warning(
                                        f"Worker {self.worker_id}: Error message appeared: {error_text[:200]}"
                                    )
                                    # Check if it's a validation error (form still present)
                                    if form_count > 0:
                                        # Form still there - might be validation error
                                        # Check required fields
                                        required_fields = await self.page.locator(
                                            "input[required], textarea[required]"
                                        ).count()
                                        logger.warning(
                                            f"Worker {self.worker_id}: Form still present with {required_fields} required fields - validation may have failed"
                                        )
                        except Exception as e:
                            logger.debug(
                                f"Worker {self.worker_id}: Could not verify submission status: {e}"
                            )

                        break
                except Exception as e:
                    logger.debug(
                        f"Worker {self.worker_id}: Selector {selector} failed: {str(e)}"
                    )
                    continue

        # Last resort: submit form via JavaScript
        # Try to trigger the submit button click event instead of form.submit()
        # This ensures event handlers are called
        if not submitted:
            try:
                logger.info(
                    f"Worker {self.worker_id}: Attempting form submission via JavaScript (triggering button click)"
                )
                form_submitted = await self.page.evaluate(
                    """
                    () => {
                        // Try multiple selectors to find submit button
                        const selectors = [
                            'button[type="submit"]',
                            'form button[type="submit"]',
                            '#submissionForm button[type="submit"]',
                            'input[type="submit"]',
                            'form button'
                        ];
                        
                        let submitButton = null;
                        for (const selector of selectors) {
                            try {
                                submitButton = document.querySelector(selector);
                                if (submitButton && submitButton.offsetParent !== null) { // Check if visible
                                    break;
                                }
                            } catch (e) {
                                continue;
                            }
                        }
                        
                        // Also try to find by text content
                        if (!submitButton) {
                            const buttons = document.querySelectorAll('button, input[type="submit"]');
                            for (const btn of buttons) {
                                const text = btn.textContent || btn.value || '';
                                if (text.toLowerCase().includes('submit') && btn.offsetParent !== null) {
                                    submitButton = btn;
                                    break;
                                }
                            }
                        }
                        
                        if (submitButton) {
                            // Scroll into view first
                            submitButton.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            
                            // Create and dispatch click event to trigger all handlers
                            const clickEvent = new MouseEvent('click', {
                                bubbles: true,
                                cancelable: true,
                                view: window,
                                buttons: 1
                            });
                            submitButton.dispatchEvent(clickEvent);
                            
                            // Also try actual click as fallback
                            try {
                                submitButton.click();
                            } catch (e) {
                                // Ignore if click fails, event dispatch should work
                            }
                            
                            return true;
                        }
                        
                        // Fallback to form.submit() if no button found
                        const form = document.querySelector('form');
                        if (form) {
                            // Try to trigger submit event first
                            const submitEvent = new Event('submit', {
                                bubbles: true,
                                cancelable: true
                            });
                            form.dispatchEvent(submitEvent);
                            return true;
                        }
                        return false;
                    }
                """
                )
                if form_submitted:
                    submitted = True
                    logger.info(
                        f"Worker {self.worker_id}: Form submitted via JavaScript (button click event)"
                    )
                else:
                    logger.warning(
                        f"Worker {self.worker_id}: No form or button found for JavaScript submission"
                    )
            except Exception as e:
                submit_error = str(e)
                logger.error(
                    f"Worker {self.worker_id}: JavaScript form submission failed: {submit_error}"
                )

        # Wait for submission to process and verify
        await self.page.wait_for_timeout(3000)

        # Double-check if form was actually submitted
        if submitted:
            try:
                # Check for success or error messages
                success_count = await self.page.locator(
                    "#successMessage, .success-message"
                ).count()
                error_count = await self.page.locator(
                    "#errorMessage, .error-message"
                ).count()

                # Check if messages are visible
                success_visible = False
                error_visible = False
                error_text = ""

                if success_count > 0:
                    success_visible = await self.page.locator(
                        "#successMessage, .success-message"
                    ).first.is_visible()
                    if success_visible:
                        logger.info(
                            f"Worker {self.worker_id}: Success message is visible after submit"
                        )

                if error_count > 0:
                    error_element = self.page.locator(
                        "#errorMessage, .error-message"
                    ).first
                    error_visible = await error_element.is_visible()
                    if error_visible:
                        error_text = await error_element.inner_text()
                        logger.warning(
                            f"Worker {self.worker_id}: Error message is visible after submit: {error_text[:200]}"
                        )

                        # If error is visible, check if it's a validation error
                        # Check if form is still present (validation errors keep form visible)
                        form_count = await self.page.locator("form").count()
                        if form_count > 0:
                            # Form still there - check required fields
                            try:
                                # Check if required fields are filled
                                required_inputs = await self.page.locator(
                                    "input[required], textarea[required]"
                                ).all()
                                unfilled_required = []
                                for req_input in required_inputs:
                                    value = await req_input.input_value()
                                    if not value or value.strip() == "":
                                        name = (
                                            await req_input.get_attribute("name")
                                            or await req_input.get_attribute("id")
                                            or "unknown"
                                        )
                                        unfilled_required.append(name)

                                if unfilled_required:
                                    logger.error(
                                        f"Worker {self.worker_id}: Required fields not filled: {unfilled_required}"
                                    )
                                    return BrowserResult.error_result(
                                        command_id,
                                        f"Form validation failed: Required fields not filled: {', '.join(unfilled_required)}",
                                        "ValidationError",
                                    )
                            except Exception as check_error:
                                logger.debug(
                                    f"Worker {self.worker_id}: Could not check required fields: {check_error}"
                                )

                        # Return error if error message is visible
                        return BrowserResult.error_result(
                            command_id,
                            f"Form submission failed: {error_text[:200]}",
                            "SubmissionError",
                        )

                # If success is visible, return success
                if success_visible:
                    return BrowserResult.success(command_id, {"submitted": True})

            except Exception as e:
                logger.debug(
                    f"Worker {self.worker_id}: Could not verify submission status: {e}"
                )

        if not submitted:
            error_msg = f"Failed to submit form. Last error: {submit_error or 'No submit button found'}"
            logger.error(f"Worker {self.worker_id}: {error_msg}")
            return BrowserResult.error_result(command_id, error_msg, "SubmitFailed")

        logger.info(f"Worker {self.worker_id}: Form submission completed successfully")
        return BrowserResult.success(command_id, {"submitted": submitted})

    async def _handle_detect_captcha(
        self, command_id: str, params: Dict
    ) -> BrowserResult:
        """Handle detect_captcha command"""
        # Check if page exists and is still open
        if not self.page:
            try:
                await self.initialize_browser()
            except Exception as e:
                return BrowserResult.error_result(
                    command_id,
                    f"Browser not initialized: {str(e)}",
                    "BrowserNotInitialized",
                )

        # Verify page is still open
        try:
            await self.page.url
        except Exception as e:
            # Page was closed, try to reinitialize and re-navigate
            logger.warning(
                f"Page was closed during detect_captcha, reinitializing for worker {self.worker_id}"
            )
            try:
                await self.initialize_browser()
                if self.current_url:
                    await self.page.goto(
                        self.current_url,
                        timeout=settings.PLAYWRIGHT_TIMEOUT,
                        wait_until="domcontentloaded",
                    )
                    await self.page.wait_for_timeout(1000)
            except Exception as reinit_error:
                return BrowserResult.error_result(
                    command_id,
                    f"Page was closed and reinitialization failed: {str(reinit_error)}",
                    "PageClosed",
                )

        captcha_selectors = [
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            ".g-recaptcha",
            "#captcha",
            "[data-sitekey]",
        ]

        for selector in captcha_selectors:
            try:
                element = self.page.locator(selector).first
                if await element.count() > 0:
                    return BrowserResult.success(command_id, {"has_captcha": True})
            except Exception:
                continue

        page_text = (await self.page.inner_text("body")).lower()
        has_captcha = "captcha" in page_text or "verify you are human" in page_text

        return BrowserResult.success(command_id, {"has_captcha": has_captcha})

    async def _handle_get_page_content(
        self, command_id: str, params: Dict
    ) -> BrowserResult:
        """Handle get_page_content command"""
        # Check if page exists and is still open
        if not self.page:
            try:
                await self.initialize_browser()
            except Exception as e:
                return BrowserResult.error_result(
                    command_id,
                    f"Browser not initialized: {str(e)}",
                    "BrowserNotInitialized",
                )

        # Verify page is still open
        try:
            content = await self.page.content()
            return BrowserResult.success(command_id, {"content": content})
        except Exception as e:
            # Page was closed, try to reinitialize and re-navigate
            logger.warning(
                f"Page was closed during get_page_content, reinitializing for worker {self.worker_id}"
            )
            try:
                await self.initialize_browser()
                if self.current_url:
                    await self.page.goto(
                        self.current_url,
                        timeout=settings.PLAYWRIGHT_TIMEOUT,
                        wait_until="domcontentloaded",
                    )
                    await self.page.wait_for_timeout(1000)
                    content = await self.page.content()
                    return BrowserResult.success(command_id, {"content": content})
            except Exception as reinit_error:
                return BrowserResult.error_result(
                    command_id,
                    f"Page was closed and reinitialization failed: {str(reinit_error)}",
                    "PageClosed",
                )
            return BrowserResult.error_result(
                command_id, f"Failed to get page content: {str(e)}", "PageClosed"
            )

    async def _handle_extract_form_fields_dom(
        self, command_id: str, params: Dict
    ) -> BrowserResult:
        """Handle extract_form_fields_dom command"""
        # Check if page exists and is still open
        if not self.page:
            try:
                await self.initialize_browser()
            except Exception as e:
                return BrowserResult.error_result(
                    command_id,
                    f"Browser not initialized: {str(e)}",
                    "BrowserNotInitialized",
                )

        # Verify page is still open
        try:
            await self.page.url
        except Exception as e:
            # Page was closed, try to reinitialize and re-navigate
            logger.warning(
                f"Page was closed during extract_form_fields_dom, reinitializing for worker {self.worker_id}"
            )
            try:
                await self.initialize_browser()
                if self.current_url:
                    await self.page.goto(
                        self.current_url,
                        timeout=settings.PLAYWRIGHT_TIMEOUT,
                        wait_until="domcontentloaded",
                    )
                    await self.page.wait_for_timeout(1000)
            except Exception as reinit_error:
                return BrowserResult.error_result(
                    command_id,
                    f"Page was closed and reinitialization failed: {str(reinit_error)}",
                    "PageClosed",
                )

        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
        except PlaywrightTimeoutError:
            pass

        await self.page.wait_for_timeout(1000)

        form_data = await self.page.evaluate(
            """
            () => {
                const fields = [];
                const forms = document.querySelectorAll('form');
                let mainForm = forms[0] || document.body;
                
                const formElements = mainForm.querySelectorAll('input, textarea, select');
                
                formElements.forEach((el, index) => {
                    const isHidden = el.type === 'hidden';
                    if (isHidden) return;
                    
                    const tagName = el.tagName.toLowerCase();
                    const type = el.type || '';
                    const name = el.name || el.id || '';
                    const id = el.id || '';
                    const placeholder = el.placeholder || '';
                    const label = el.labels && el.labels[0] ? el.labels[0].textContent.trim() : '';
                    
                    let labelText = label;
                    if (!labelText && id) {
                        const labelEl = document.querySelector(`label[for="${id}"]`);
                        if (labelEl) labelText = labelEl.textContent.trim();
                    }
                    if (!labelText && name) {
                        const labelEl = document.querySelector(`label[for="${name}"]`);
                        if (labelEl) labelText = labelEl.textContent.trim();
                    }
                    
                    let selector = '';
                    if (id) {
                        selector = `#${id}`;
                    } else if (name) {
                        selector = `[name="${name}"]`;
                    } else {
                        selector = `${tagName}[type="${type}"]:nth-of-type(${index + 1})`;
                    }
                    
                    const required = el.hasAttribute('required') || 
                                   el.getAttribute('aria-required') === 'true';
                    
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
                
                let submitButton = null;
                const submitSelectors = [
                    'button[type="submit"]',
                    'input[type="submit"]',
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
                
                const formSelector = forms[0] ? 
                    (forms[0].id ? `#${forms[0].id}` : (forms[0].name ? `form[name="${forms[0].name}"]` : 'form')) :
                    'body';
                
                return {
                    fields: fields,
                    submit_button: submitButton,
                    form_selector: formSelector
                };
            }
        """
        )

        return BrowserResult.success(command_id, form_data)

    async def _handle_take_screenshot(
        self, command_id: str, params: Dict
    ) -> BrowserResult:
        """Handle take_screenshot command"""
        if not self.page:
            return BrowserResult.error_result(
                command_id, "Browser not initialized", "BrowserNotInitialized"
            )

        path = params.get("path")
        os.makedirs(
            os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True
        )
        await self.page.screenshot(path=path, full_page=True)

        return BrowserResult.success(command_id, {"path": path})

    async def _handle_detect_submission_page(
        self, command_id: str, params: Dict
    ) -> BrowserResult:
        """Handle detect_submission_page command"""
        # Initialize browser if needed
        if not self.page:
            try:
                await self.initialize_browser()
                # If we have a stored URL, navigate to it
                if self.current_url:
                    logger.info(
                        f"Worker {self.worker_id}: Navigating to stored URL: {self.current_url}"
                    )
                    await self.page.goto(
                        self.current_url,
                        timeout=settings.PLAYWRIGHT_TIMEOUT,
                        wait_until="domcontentloaded",
                    )
                    await self.page.wait_for_timeout(1000)
            except Exception as e:
                return BrowserResult.error_result(
                    command_id,
                    f"Browser not initialized and initialization failed: {str(e)}",
                    "BrowserNotInitialized",
                )

        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=3000)
        except PlaywrightTimeoutError:
            pass

        await self.page.wait_for_timeout(500)

        submission_keywords = [
            "submit",
            "add listing",
            "add your",
            "submit your",
            "add product",
            "submit product",
            "new listing",
            "list your",
        ]

        page_text = await self.page.inner_text("body")
        page_text_lower = page_text.lower()

        form_count = await self.page.locator("form").count()
        input_count = await self.page.locator("input, textarea, select").count()
        submit_buttons = await self.page.locator(
            "button[type='submit'], input[type='submit']"
        ).count()
        has_keywords = any(
            keyword in page_text_lower for keyword in submission_keywords
        )

        detected = (
            (form_count > 0 and input_count >= 2) or submit_buttons > 0 or has_keywords
        )

        return BrowserResult.success(command_id, {"detected": detected})

    async def _handle_wait_for_confirmation(
        self, command_id: str, params: Dict
    ) -> BrowserResult:
        """Handle wait_for_confirmation command"""
        if not self.page:
            return BrowserResult.error_result(
                command_id, "Browser not initialized", "BrowserNotInitialized"
            )

        timeout_ms = params.get("timeout", 10000)
        # Wait longer for success message to appear (test forms often show it after a delay)
        await self.page.wait_for_timeout(min(3000, timeout_ms))

        # Wait for page to potentially navigate or update after submission
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
        except:
            pass

        # Wait a bit more for dynamic content (success messages, etc.)
        await self.page.wait_for_timeout(1000)

        success_keywords = [
            "thank you",
            "success",
            "submitted",
            "received",
            "confirmation",
            "form submitted",
            "submission successful",
            "thank you for",
            "your submission",
            "successfully submitted",
            "form received",
        ]
        error_keywords = [
            "error",
            "failed",
            "invalid",
            "required",
            "captcha",
            "verification failed",
        ]

        page_text = (await self.page.inner_text("body")).lower()
        current_url = self.page.url

        # Check for success message elements (common in test forms)
        try:
            # Check multiple selectors for success messages
            success_selectors = [
                "#successMessage",
                ".success",
                "[class*='success']",
                "#submission-success",
                ".submission-success",
                "[id*='success']",
                "[class*='alert-success']",
            ]

            for selector in success_selectors:
                try:
                    element = self.page.locator(selector).first
                    count = await element.count()
                    if count > 0:
                        # Check if element is visible
                        is_visible = await element.is_visible()
                        if is_visible:
                            success_text = await element.inner_text()
                            logger.info(
                                f"Worker {self.worker_id}: Success message element detected AND visible: {selector} - '{success_text[:100]}'"
                            )
                            return BrowserResult.success(
                                command_id,
                                {
                                    "status": "success",
                                    "message": f"Submission successful (success message detected: {success_text[:200]})",
                                    "url": current_url,
                                },
                            )
                        else:
                            logger.debug(
                                f"Worker {self.worker_id}: Success element {selector} exists but is hidden"
                            )
                except Exception:
                    continue
        except Exception as e:
            logger.debug(
                f"Worker {self.worker_id}: Error checking for success elements: {e}"
            )

        # Check for error message elements (only if visible!)
        try:
            error_selector = (
                "#errorMessage, .error, [class*='error'], .alert-danger, .alert-error"
            )
            error_elements = await self.page.locator(error_selector).count()
            if error_elements > 0:
                # Check if error message is actually visible
                error_element = self.page.locator(error_selector).first
                is_visible = await error_element.is_visible()
                if is_visible:
                    error_text = await error_element.inner_text()
                    logger.warning(
                        f"Worker {self.worker_id}: Error message element detected AND visible: {error_text[:100]}"
                    )
                    return BrowserResult.success(
                        command_id,
                        {
                            "status": "error",
                            "message": f"Submission failed (error message detected): {error_text[:200]}",
                            "url": current_url,
                        },
                    )
                else:
                    logger.debug(
                        f"Worker {self.worker_id}: Error message element exists but is hidden (not an error)"
                    )
        except:
            pass

        status = "pending"
        message = "Submission status unclear"

        # Check for success keywords
        for keyword in success_keywords:
            if keyword in page_text:
                status = "success"
                message = f"Submission successful (detected: {keyword})"
                logger.info(f"Worker {self.worker_id}: {message}")
                break

        # Check for error keywords (only if no success found)
        if status == "pending":
            for keyword in error_keywords:
                if keyword in page_text:
                    status = "error"
                    message = f"Submission may have failed (detected: {keyword})"
                    logger.warning(f"Worker {self.worker_id}: {message}")
                    break

        # If still pending, check if URL changed (indicates navigation after submission)
        if status == "pending":
            if self.current_url and current_url != self.current_url:
                # URL changed after submission - likely success
                status = "success"
                message = f"Submission likely successful (URL changed from {self.current_url} to {current_url})"
                logger.info(f"Worker {self.worker_id}: {message}")
            elif "form" not in page_text.lower() or len(page_text) < 100:
                # Form is gone and page is different - likely success
                status = "success"
                message = (
                    "Submission likely successful (form no longer present on page)"
                )
                logger.info(f"Worker {self.worker_id}: {message}")
            else:
                # Still unclear, but if we got here, form was submitted
                # Default to success if form submission returned True
                status = "success"
                message = "Submission completed (status unclear but form was submitted)"
                logger.info(f"Worker {self.worker_id}: {message}")

        return BrowserResult.success(
            command_id, {"status": status, "message": message, "url": current_url}
        )

    async def _handle_close(self, command_id: str, params: Dict) -> BrowserResult:
        """Handle close command - only closes page, keeps browser alive"""
        await self.cleanup_browser(full_cleanup=False)
        return BrowserResult.success(command_id, {})

    async def run(self):
        """
        Main worker loop that processes commands.
        Runs until shutdown command is received.

        Browser is initialized lazily on first command, not on startup,
        to avoid issues with pages closing before first use.
        """
        self.is_running = True
        logger.info(
            f"Browser worker {self.worker_id} started and ready (browser will be initialized on first command)"
        )

        while self.is_running:
            try:
                # Get command from queue (blocking with timeout)
                try:
                    command_dict = self.command_queue.get(timeout=1.0)
                except:
                    continue

                if command_dict is None:  # Shutdown signal
                    logger.info(
                        f"Browser worker {self.worker_id} received shutdown signal"
                    )
                    break

                command = BrowserCommand.from_dict(command_dict)

                # Handle command
                result = await self.handle_command(command)

                # Send result back
                self.result_queue.put(result.to_dict())

            except Exception as e:
                logger.error(f"Browser worker {self.worker_id} error in main loop: {e}")
                traceback.print_exc()

        # Cleanup - full cleanup on shutdown
        await self.cleanup_browser(full_cleanup=True)
        logger.info(f"Browser worker {self.worker_id} stopped")


def worker_main(command_queue: Queue, result_queue: Queue, worker_id: int):
    """
    Main entry point for worker process.

    This function runs in a separate process and creates an event loop
    to run the browser worker asynchronously.

    Args:
        command_queue: Queue to receive commands
        result_queue: Queue to send results
        worker_id: Unique worker identifier
    """
    # Re-initialize logger in worker process (multiprocessing requires this on Windows)
    # Use the same colored logger setup as main process
    from app.utils.logger import setup_logger

    worker_logger = setup_logger()

    worker = BrowserWorker(command_queue, result_queue, worker_id)

    # Create and run event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(worker.run())
    except KeyboardInterrupt:
        worker_logger.info(f"Browser worker {worker_id} interrupted")
    except Exception as e:
        worker_logger.error(f"Browser worker {worker_id} crashed: {e}")
        traceback.print_exc()
    finally:
        loop.close()
