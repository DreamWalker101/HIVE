#!/usr/bin/env python3
"""
RiRi LinkedIn poster — HEADFUL (visible browser).
Ahmed can watch and handle login if needed.
"""
import os, subprocess, sys, time

DISPLAY = os.environ.get("DISPLAY", ":1")
os.environ["DISPLAY"] = DISPLAY

POST_TEXT = """Built an ambient local-first AI stack over the last few weeks. Here's what's running:

🧠 RiRi — a transparent AI overlay that lives at the top of the screen. Invisible at idle, appears on hover. 4-tier brain fallback: local Ollama → Gemini CLI → Groq → OpenAI, so ~95% of queries are free.

📡 Claude Code Pipeline Awareness — hooks into every Claude Code session. When a session ends, a local model distills what was built, what was fixed, and what's still todo — all queryable via natural language.

🗂️ Tool Knowledge Base — ChromaDB + nomic-embed-text semantic index of all CLI tools. When RiRi gets a task, it looks up the right tool automatically. No more hallucinated commands.

📧 Outreach Engine — automated personalised cold outreach via real Gmail (OAuth, not SMTP). AI-generated copy per lead, full status tracking.

All of this runs on a single Ubuntu workstation. The goal was maximum capability at minimum cloud spend — and it mostly works.

Case studies: https://github.com/DreamWalker101/tavren-ai-case-studies

#AI #LocalAI #BuildInPublic #Automation #Python"""

LOG = os.path.expanduser("~/.local/share/riri/linkedin.log")

def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def notify(msg):
    try:
        subprocess.Popen(
            ["python3", os.path.expanduser("~/projects/riri/notify.py"), msg],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        pass

def try_selenium():
    """Try with selenium + Chrome."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    import pyperclip

    opts = Options()
    # HEADFUL — no headless flag
    opts.add_argument(f"--display={DISPLAY}")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1200,800")
    opts.add_argument("--window-position=100,50")
    # Use existing Chrome profile if available (may already be logged in)
    profile = os.path.expanduser("~/.config/google-chrome/Default")
    if os.path.isdir(profile):
        opts.add_argument(f"--user-data-dir={os.path.expanduser('~/.config/google-chrome')}")
        opts.add_argument("--profile-directory=Default")

    log("Launching Chrome (headful)...")
    driver = webdriver.Chrome(options=opts)
    wait = WebDriverWait(driver, 30)

    try:
        log("Navigating to LinkedIn feed...")
        driver.get("https://www.linkedin.com/feed/")
        time.sleep(3)

        # Check if logged in
        if "login" in driver.current_url or "authwall" in driver.current_url:
            log("Not logged in — waiting up to 120s for Ahmed to log in...")
            notify("LinkedIn needs login — please log in in the browser window")
            deadline = time.time() + 120
            while time.time() < deadline:
                time.sleep(2)
                if "feed" in driver.current_url or "mynetwork" in driver.current_url:
                    log("Login detected — continuing...")
                    break
            else:
                log("Login timeout — saving draft")
                return False

        time.sleep(2)
        log("Looking for 'Start a post' button...")

        # Try multiple selectors for the post button
        post_btn = None
        selectors = [
            "//span[contains(text(),'Start a post')]",
            "//button[contains(@class,'share-box-feed-entry')]",
            "//div[contains(@class,'share-creation-state')]//button",
            "//button[contains(text(),'Post')]",
        ]
        for sel in selectors:
            try:
                post_btn = wait.until(EC.element_to_be_clickable((By.XPATH, sel)))
                if post_btn:
                    break
            except Exception:
                continue

        if not post_btn:
            log("Could not find post button — taking screenshot")
            driver.save_screenshot(os.path.expanduser("~/Desktop/case-studies/linkedin-debug.png"))
            return False

        log("Clicking 'Start a post'...")
        post_btn.click()
        time.sleep(2)

        log("Looking for text editor...")
        editor = None
        editor_selectors = [
            "//div[@role='textbox']",
            "//div[contains(@class,'ql-editor')]",
            "//div[contains(@class,'mentions-texteditor')]",
        ]
        for sel in editor_selectors:
            try:
                editor = wait.until(EC.element_to_be_clickable((By.XPATH, sel)))
                if editor:
                    break
            except Exception:
                continue

        if not editor:
            log("Could not find text editor")
            driver.save_screenshot(os.path.expanduser("~/Desktop/case-studies/linkedin-debug.png"))
            return False

        log("Typing post content...")
        editor.click()
        time.sleep(0.5)

        # Use clipboard paste for emoji support
        try:
            import pyperclip
            pyperclip.copy(POST_TEXT)
            editor.send_keys(Keys.CONTROL + "v")
            log("Pasted via clipboard")
        except Exception:
            # Fallback: type directly (emojis may not work)
            for line in POST_TEXT.split("\n"):
                editor.send_keys(line)
                editor.send_keys(Keys.SHIFT + Keys.ENTER)
            log("Typed directly (no pyperclip)")

        time.sleep(2)
        log("Looking for Post button...")

        submit_btn = None
        submit_selectors = [
            "//button[.//span[text()='Post']]",
            "//button[@data-control-name='share.post']",
            "//div[@class='share-actions__primary-action']//button",
            "//button[contains(@class,'share-actions__primary-action')]",
        ]
        for sel in submit_selectors:
            try:
                submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, sel)))
                if submit_btn:
                    break
            except Exception:
                continue

        if not submit_btn:
            log("Could not find Post submit button — taking screenshot")
            driver.save_screenshot(os.path.expanduser("~/Desktop/case-studies/linkedin-review.png"))
            log("Post is composed — Ahmed can submit manually")
            notify("LinkedIn post ready — please click Post in the browser")
            time.sleep(60)  # Give Ahmed time to review and submit
            return True

        # Take screenshot before posting
        driver.save_screenshot(os.path.expanduser("~/Desktop/case-studies/linkedin-preview.png"))
        log("Screenshot saved: linkedin-preview.png")

        log("Clicking Post...")
        submit_btn.click()
        time.sleep(4)

        # Take post-submit screenshot
        driver.save_screenshot(os.path.expanduser("~/Desktop/case-studies/linkedin-screenshot.png"))
        log("Post submitted! Screenshot saved: linkedin-screenshot.png")
        notify("LinkedIn post published ✓")
        return True

    finally:
        time.sleep(5)
        driver.quit()


def try_browser_use():
    """Fallback: use browser-use agent."""
    import asyncio
    from browser_use import Agent as BUAgent
    from browser_use.browser.browser import Browser, BrowserConfig

    browser = Browser(config=BrowserConfig(headless=False))

    task = f"""
Go to https://www.linkedin.com/feed/ in the browser.
If you see a login page, stop and wait — do not log in automatically.
Once on the feed, click the "Start a post" area.
When the post composer opens, type the following text exactly:

---
{POST_TEXT}
---

After typing, take a screenshot, then click the "Post" button to publish.
"""
    log("Trying browser-use agent...")

    async def run():
        agent = BUAgent(task=task, llm=None, browser=browser)
        await agent.run()

    asyncio.run(run())


def save_draft_fallback():
    draft_path = os.path.expanduser("~/Desktop/linkedin-post-draft.txt")
    with open(draft_path, "w") as f:
        f.write(POST_TEXT)
    log(f"Saved draft to {draft_path}")
    notify("LinkedIn post saved as draft on Desktop — paste manually")


if __name__ == "__main__":
    log("=== LinkedIn post task starting ===")
    log(f"DISPLAY={DISPLAY}")

    # Try selenium first (most reliable with existing Chrome profile)
    try:
        from selenium import webdriver
        success = try_selenium()
        if success:
            log("=== Done via Selenium ===")
            sys.exit(0)
    except ImportError:
        log("Selenium not available — installing...")
        subprocess.run(
            ["pip", "install", "selenium", "--break-system-packages", "-q"],
            check=False
        )
        # Try installing chromedriver
        subprocess.run(
            ["pip", "install", "webdriver-manager", "--break-system-packages", "-q"],
            check=False
        )
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            # patch options to use managed driver
            success = try_selenium()
            if success:
                sys.exit(0)
        except Exception as e:
            log(f"Selenium failed: {e}")

    # Save draft as fallback
    save_draft_fallback()
    log("=== LinkedIn task complete (draft saved) ===")
