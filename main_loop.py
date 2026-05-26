import time
import base64
import requests
import json
import os
import sys

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


print("📦 Script loaded, starting main...", flush=True)


EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
GH_TOKEN = os.getenv("GH_TOKEN")
GH_REPO = os.getenv("GH_REPO")
GH_FILE_PATH = os.getenv("GH_FILE_PATH", "tk.txt")
GH_BRANCH = os.getenv("GH_BRANCH", "main")

CHROME_BIN = os.getenv("CHROME_BIN", "/usr/bin/chromium")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")


def start_driver():
    print("🚀 Driver starting...", flush=True)
    
    options = webdriver.ChromeOptions()
    options.binary_location = CHROME_BIN
    
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--remote-debugging-port=9222")
    
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    
    print(f"🔧 Chrome binary: {CHROME_BIN}", flush=True)
    print(f"🔧 Chromedriver: {CHROMEDRIVER_PATH}", flush=True)
    
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd("Network.enable", {})
    
    print("✅ Driver ready!", flush=True)
    return driver


def login(driver):
    print("🔐 Logging in...", flush=True)
    wait = WebDriverWait(driver, 40)
    
    driver.get(
        "https://studio.speechify.com/sign-in"
        "?returnTo=https%3A%2F%2Fstudio.speechify.com%2F"
    )
    print("📄 Page loaded", flush=True)
    
    email_input = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'input[data-testid="email-input"]')
        )
    )
    email_input.clear()
    email_input.send_keys(EMAIL)
    print("📧 Email entered", flush=True)
    time.sleep(1)
    
    pass_input = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'input[data-testid="password-input"]')
        )
    )
    pass_input.clear()
    pass_input.send_keys(PASSWORD)
    pass_input.send_keys(Keys.ENTER)
    print("🔑 Password entered, waiting...", flush=True)
    
    time.sleep(15)
    driver.get("https://studio.speechify.com/")
    time.sleep(10)
    print("✅ Login complete!", flush=True)


def get_token(driver):
    logs = driver.get_log("performance")
    
    for entry in logs:
        try:
            msg = json.loads(entry["message"])["message"]
            
            if msg.get("method") == "Network.requestWillBeSent":
                request = msg["params"]["request"]
                url = request.get("url", "")
                
                if "videostudio.api.speechify.com/graphql" in url:
                    headers = request.get("headers", {})
                    token = headers.get("authorization") or headers.get("Authorization")
                    
                    if token:
                        return token
        except Exception:
            pass
    
    return None


def update_github(token):
    print("📤 Updating GitHub...", flush=True)
    
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{GH_FILE_PATH}"
    
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    
    encoded = base64.b64encode(token.encode()).decode()
    
    res = requests.get(url, headers=headers, params={"ref": GH_BRANCH})
    
    data = {
        "message": "auto update token",
        "content": encoded,
        "branch": GH_BRANCH
    }
    
    if res.status_code == 200:
        data["sha"] = res.json()["sha"]
    
    r = requests.put(url, headers=headers, json=data)
    
    if r.status_code in [200, 201]:
        print("✅ Token saved on GitHub!", flush=True)
    else:
        print(f"❌ Failed: {r.status_code} - {r.text}", flush=True)


def main():
    driver = None
    
    try:
        print("=" * 50, flush=True)
        print("🤖 BOT STARTING...", flush=True)
        print("=" * 50, flush=True)
        
        if not EMAIL or not PASSWORD:
            print("❌ EMAIL/PASSWORD missing", flush=True)
            return
        
        if not GH_TOKEN or not GH_REPO:
            print("❌ GH_TOKEN/GH_REPO missing", flush=True)
            return
        
        print(f"📧 Email: {EMAIL[:5]}***", flush=True)
        print(f"📦 Repo: {GH_REPO}", flush=True)
        
        driver = start_driver()
        login(driver)
        
        print("🔍 Searching for token...", flush=True)
        token = None
        
        for i in range(30):
            token = get_token(driver)
            if token:
                print(f"✅ Token found ({i+1} tries)", flush=True)
                break
            print(f"⏳ Try {i+1}/30...", flush=True)
            time.sleep(3)
        
        driver.quit()
        driver = None
        
        if not token:
            print("❌ Token not found", flush=True)
        else:
            print(f"🎯 TOKEN: {token[:30]}...", flush=True)
            update_github(token)
            
    except Exception as e:
        print(f"💥 ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        
        try:
            if driver:
                driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
