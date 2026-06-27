import sys
import asyncio

# Fix NotImplementedError for Playwright on Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import os
import io
import time
import logging
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page, Browser, Playwright
from PIL import Image
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebDriverManager")

class WebDriverManager:
    def __init__(self):
        self.playwright: Playwright = None
        self.browser: Browser = None
        self.page: Page = None
        
    def start(self, headless: bool = None, slow_mo: int = None):
        """Start the browser session"""
        if self.page:
            return
            
        headless = headless if headless is not None else Config.HEADLESS
        slow_mo = slow_mo if slow_mo is not None else Config.SLOW_MO
        
        logger.info(f"Starting Playwright Browser (headless={headless}, slow_mo={slow_mo}ms)...")
        self.playwright = sync_playwright().start()
        
        # Launch Chromium
        self.browser = self.playwright.chromium.launch(
            headless=headless,
            slow_mo=slow_mo
        )
        
        # Create context and page
        context = self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.page = context.new_page()
        self.page.set_default_timeout(Config.DEFAULT_TIMEOUT)
        logger.info("Browser session started successfully.")

    def navigate(self, url: str):
        """Navigate to a URL"""
        self.start()
        logger.info(f"Navigating to {url}...")
        self.page.goto(url)
        self.page.wait_for_load_state("networkidle")

    def get_screenshot(self) -> bytes:
        """Capture page screenshot and return compressed jpeg bytes to save token cost"""
        if not self.page:
            raise RuntimeError("Browser not started. Call start() or navigate() first.")
            
        raw_screenshot = self.page.screenshot(type="png")
        
        # Compress and resize using PIL
        image = Image.open(io.BytesIO(raw_screenshot))
        # Resize to max width 1024 while maintaining aspect ratio
        max_size = 1024
        if image.width > max_size:
            ratio = max_size / float(image.width)
            new_height = int(float(image.height) * float(ratio))
            image = image.resize((max_size, new_height), Image.Resampling.LANCZOS)
            
        # Convert to JPEG with 80% quality
        output = io.BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=80)
        return output.getvalue()

    def get_dom_structure(self) -> str:
        """
        Extract a cleaned, token-efficient HTML representation of the interactive elements.
        """
        if not self.page:
            return ""
            
        html_content = self.page.content()
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove non-visual and script elements
        for s in soup(["script", "style", "svg", "path", "head", "noscript", "iframe", "link", "meta"]):
            s.decompose()
            
        # We want to keep:
        # - Interactive elements: a, button, input, select, textarea
        # - Structural/Text elements that provide error messages or key page context (h1-h6, div with errors)
        interactive_elements = []
        
        # Walk and extract
        for element in soup.find_all(True):
            name = element.name
            attrs = element.attrs
            
            # Identify interactive or contextual elements
            is_interactive = name in ['input', 'button', 'select', 'textarea', 'a', 'form']
            is_header = name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
            
            # Check for error container classes or ids
            class_str = " ".join(attrs.get("class", [])).lower()
            id_str = attrs.get("id", "").lower()
            is_error = "error" in class_str or "error" in id_str or "message" in class_str
            
            # Check for data-test or data-testid attributes
            has_qa_attributes = any(key in attrs for key in ['data-test', 'data-testid'])
            
            if is_interactive or is_header or is_error or has_qa_attributes:
                # Reconstruct a simplified tag representation
                simplified_attrs = {}
                # Keep only useful attributes for automation and layout analysis
                for attr in ['id', 'class', 'name', 'type', 'placeholder', 'value', 'data-test', 'data-testid', 'href']:
                    if attr in attrs:
                        val = attrs[attr]
                        if isinstance(val, list):
                            simplified_attrs[attr] = " ".join(val)
                        else:
                            simplified_attrs[attr] = val
                            
                # Capture text content inside the element (truncated if too long)
                inner_text = element.get_text(strip=True)
                if len(inner_text) > 80:
                    inner_text = inner_text[:77] + "..."
                    
                # Create a mini tag structure
                tag_attrs = " ".join([f'{k}="{v}"' for k, v in simplified_attrs.items()])
                tag_open = f"<{name} {tag_attrs}>" if tag_attrs else f"<{name}>"
                
                if inner_text:
                    tag_repr = f"{tag_open}{inner_text}</{name}>"
                else:
                    tag_repr = f"{tag_open}</{name}>"
                    
                interactive_elements.append(tag_repr)
                
        return "\n".join(interactive_elements)

    def safe_click(self, selector: str, timeout: int = None) -> bool:
        """Click an element, handling exceptions and returning success status"""
        timeout = timeout or Config.DEFAULT_TIMEOUT
        try:
            # Wait for element to be visible and stable
            self.page.wait_for_selector(selector, state="visible", timeout=timeout)
            # Scroll to element to ensure it's in view
            self.page.locator(selector).scroll_into_view_if_needed()
            self.page.click(selector, timeout=timeout)
            # Wait a small duration for actions to take effect
            self.page.wait_for_load_state("load")
            return True
        except Exception as e:
            logger.error(f"Failed to click selector '{selector}': {e}")
            raise e

    def safe_type(self, selector: str, value: str, timeout: int = None) -> bool:
        """Type text into an input field, clearing it first"""
        timeout = timeout or Config.DEFAULT_TIMEOUT
        try:
            self.page.wait_for_selector(selector, state="visible", timeout=timeout)
            self.page.locator(selector).scroll_into_view_if_needed()
            # Clear field
            self.page.fill(selector, "")
            # Type character-by-character if slow_mo is set, or just fill
            self.page.fill(selector, value, timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"Failed to type value '{value}' into selector '{selector}': {e}")
            raise e

    def safe_select(self, selector: str, value: str, timeout: int = None) -> bool:
        """Select an option in a dropdown"""
        timeout = timeout or Config.DEFAULT_TIMEOUT
        try:
            self.page.wait_for_selector(selector, state="visible", timeout=timeout)
            self.page.locator(selector).scroll_into_view_if_needed()
            self.page.select_option(selector, value=value, timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"Failed to select option '{value}' in selector '{selector}': {e}")
            raise e

    def safe_verify(self, expected_text: str, timeout: int = 5000) -> bool:
        """Verify if specific text exists on the page"""
        try:
            # Check if text is present in the visible page text
            # We can search by text selector in Playwright
            # E.g. locator("text=expected_text")
            locator = self.page.get_by_text(expected_text)
            # Check count
            count = locator.count()
            if count > 0:
                logger.info(f"Verification Success: found text '{expected_text}'")
                return True
            
            # Alternative check in HTML body text
            body_text = self.page.locator("body").inner_text()
            if expected_text.lower() in body_text.lower():
                logger.info(f"Verification Success: found text '{expected_text}' inside body text")
                return True
                
            logger.warning(f"Verification Failed: text '{expected_text}' not found")
            return False
        except Exception as e:
            logger.error(f"Verification Error: {e}")
            return False

    def close(self):
        """Close browser resources"""
        logger.info("Closing browser session...")
        try:
            if self.page:
                self.page.close()
                self.page = None
            if self.browser:
                self.browser.close()
                self.browser = None
            if self.playwright:
                self.playwright.stop()
                self.playwright = None
            logger.info("Browser session closed.")
        except Exception as e:
            logger.error(f"Error during browser close: {e}")
