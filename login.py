# login.py

import os
import time
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv

load_dotenv()
USER = os.getenv("LINKEDIN_USER")
PASS = os.getenv("LINKEDIN_PASS")
COOKIES_FILE = "cookies.pkl"   # Will live in the same folder as login.py

def get_driver(headless=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless")
    # Ensures you have a full viewport (avoids some “element not clickable” issues)
    opts.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=opts)

def load_cookies(driver):
    """
    If cookies.pkl exists, load each cookie into the browser before visiting LinkedIn.
    Returns True if cookies were loaded, False if no cookie file was found.
    """
    if not os.path.exists(COOKIES_FILE):
        return False

    # Navigate to LinkedIn root so that cookies apply to the correct domain
    driver.get("https://www.linkedin.com")
    with open(COOKIES_FILE, "rb") as f:
        cookies = pickle.load(f)

    for cookie in cookies:
        try:
            # Some cookies may contain “sameSite” or other attributes that Selenium rejects.
            # Removing those keys if present can help.
            cookie.pop("sameSite", None)
            cookie.pop("expiry", None)
        except Exception:
            pass
        driver.add_cookie(cookie)

    driver.refresh()
    time.sleep(2)  
    return True

def save_cookies(driver):
    """
    After a successful login, grab all cookies from the driver and pickle them.
    """
    cookies = driver.get_cookies()
    with open(COOKIES_FILE, "wb") as f:
        pickle.dump(cookies, f)

def linkedin_login(driver):
    """
    1. Try to load cookies (if they exist) and hit the feed page.
    2. If load_cookies+refresh lands on /login or a checkpoint, do a full login flow (with 2FA prompt).
    3. After successful login, save cookies back to disk.
    """
    # 1) Attempt to re‐use cookies if they exist
    cookies_were_loaded = load_cookies(driver)

    # 2) Now navigate to the feed page and see if we get kicked to login
    driver.get("https://www.linkedin.com/feed/")
    time.sleep(2)

    # If LinkedIn thinks you’re not authenticated, it'll redirect you to a URL containing /login
    if "login" in driver.current_url or "checkpoint" in driver.current_url:
        # We need to do a full username/password (and possibly 2FA) login...

        driver.get("https://www.linkedin.com/login")
        time.sleep(1)

        driver.find_element(By.ID, "username").send_keys(USER)
        driver.find_element(By.ID, "password").send_keys(PASS)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(2)

        # 3) Check if LinkedIn is asking for 2FA
        if "checkpoint/challenge" in driver.current_url or driver.find_elements(By.NAME, "pin"):
            print("\n→ LinkedIn is asking for a 2FA code.")
            code = input("   Please enter the 2FA code you received: ").strip()

            # Some pages use name="pin", some use id="input__phone_verification_pin"
            try:
                pin_input = driver.find_element(By.NAME, "pin")
            except:
                pin_input = driver.find_element(By.ID, "input__phone_verification_pin")

            pin_input.clear()
            pin_input.send_keys(code)
            driver.find_element(By.XPATH, "//button[@type='submit']").click()
            time.sleep(2)

            # Verify 2FA worked
            if "checkpoint/challenge" in driver.current_url or driver.find_elements(By.NAME, "pin"):
                raise Exception("2FA code failed – check your code and try again.")

        # 4) At this point, login must have succeeded. Save new cookies to disk.
        save_cookies(driver)

    # If cookies were valid, we never entered the above block, and you remain logged in.
    return driver
