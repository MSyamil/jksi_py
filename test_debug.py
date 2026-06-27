import sys
import asyncio
import time
import os

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from dotenv import load_dotenv
load_dotenv()

from web_driver import WebDriverManager
from ai_client import AIClient

driver = WebDriverManager()

try:
    print("1. Navigating...")
    driver.navigate("https://www.saucedemo.com/")
    
    print("2. Typing username...")
    driver.safe_type("input#user-name", "standard_user")
    
    print("3. Typing password...")
    driver.safe_type("input#password", "secret_sauce")
    
    print("4. Getting DOM structure...")
    dom = driver.get_dom_structure()
    print("DOM Length:", len(dom))
    
    print("5. Getting screenshot...")
    start_time = time.time()
    screenshot = driver.get_screenshot()
    print("Screenshot Size:", len(screenshot), "bytes (took", time.time() - start_time, "seconds)")
    
    print("6. Calling Gemini API...")
    start_time = time.time()
    res = AIClient.analyze_page_state(
        dom_structure=dom,
        screenshot_bytes=screenshot,
        goal="Login dan lakukan checkout",
        history=[],
        model="gemini-3.1-flash-lite"
    )
    print("Gemini response (took", time.time() - start_time, "seconds):")
    print(res)
    
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    driver.close()
