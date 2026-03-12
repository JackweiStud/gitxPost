import sys
import os
from pathlib import Path
import time
from browser_cdp_session import create_session

try:
    from patchright.sync_api import Error as PlaywrightError
    from patchright.sync_api import TimeoutError as PlaywrightTimeoutError
    from patchright.sync_api import Page
except Exception:
    PlaywrightError = Exception
    PlaywrightTimeoutError = Exception
    Page = object

output_dir = Path('./debug_output')
output_dir.mkdir(exist_ok=True)

session = None
try:
    session = create_session()
    browser, context, page = session.start()

    print(f"Navigating to https://x.com")
    page.goto('https://x.com', wait_until="domcontentloaded", timeout=60000)
    time.sleep(2) # Give some time for JavaScript to execute

    js_enabled = page.evaluate('navigator.javaEnabled()')
    print(f"JavaScript enabled: {js_enabled}")

except Exception as e:
    print(f"Error during debugging script: {e}")
finally:
    if session:
        session.close()