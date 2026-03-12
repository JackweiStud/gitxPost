import os
from pathlib import Path
from playwright.sync_api import sync_playwright # Changed import

output_dir = Path('./debug_output')
output_dir.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://example.com", timeout=60000) # Test with example.com
    js_result = page.evaluate('1 + 1') # Direct JavaScript execution test
    print(f"Standalone Playwright - JavaScript evaluation result: {js_result}")
    
    js_enabled_nav = page.evaluate('navigator.javaEnabled()')
    print(f"Standalone Playwright - navigator.javaEnabled(): {js_enabled_nav}")

    browser.close()