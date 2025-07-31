import pickle
import os
import time
import random
import traceback
from typing import Optional
from seleniumbase import Driver
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='automation.log', filemode='a')


def clean_file_name(file_name: str) -> str:
    return "".join(c for c in file_name if c.isalnum() or c in (' ', '-', '_')).rstrip()


def click_element(driver: webdriver.Chrome, element):
    ActionChains(driver).move_to_element(element).click().perform()


def js_click_element(driver: webdriver.Chrome, element):
    driver.execute_script("arguments[0].scrollIntoView(true);", element)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", element)


def load_cookies(account: str) -> Optional[dict]:
    cookie_file_path = os.path.join("accounts", account, "claude_cookies.pkl")
    if os.path.exists(cookie_file_path):
        with open(cookie_file_path, "rb") as f:
            return pickle.load(f)
    return None


def save_cookies(driver, account):
    all_cookies = driver.get_cookies()
    cookie_dict = {cookie["name"]: cookie["value"] for cookie in all_cookies if ".claude.ai" in cookie.get("domain", "")}
    cookie_file_path = os.path.join("accounts", account, "claude_cookies.pkl")
    with open(cookie_file_path, "wb") as f:
        pickle.dump(cookie_dict, f)
    print("Cookies saved successfully")


def random_sleep(min_seconds=1.0, max_seconds=3.0):
    time.sleep(random.uniform(min_seconds, max_seconds))


def check_limit_reached(driver: webdriver.Chrome) -> bool:
    try:
        driver.find_element(By.XPATH, '//div[contains(text(), "limit reached")]')
        return True
    except Exception:
        return False


def get_reactivation_time(driver: webdriver.Chrome) -> Optional[str]:
    try:
        el = driver.find_element(By.XPATH, '//div[contains(text(), "limit reached")]/span')
        time_str = el.text
        print(f"Reactivation time: {time_str}")
        return time_str
    except Exception:
        logging.error(f"Error getting reactivation time: {traceback.format_exc()}")
        return None


def handle_login(driver: webdriver.Chrome, account: str):
    driver.get("about:blank")
    random_sleep(0.5, 1.5)

    cookies = load_cookies(account)
    if cookies:
        print("Cookies found, attempting to log in...")
        driver.get("https://claude.ai")
        random_sleep(1, 2)
        for name, value in cookies.items():
            driver.add_cookie({"name": name, "value": value, "domain": ".claude.ai"})
        driver.get("https://claude.ai/projects")
        random_sleep(4, 5)
        if "login" in driver.current_url:
            print("Cookies expired or invalid, please log in manually")
            driver.get("https://claude.ai")
            input("Press Enter after you've logged in...")
            save_cookies(driver, account)
    else:
        print("No cookies found, please log in manually")
        driver.get("https://claude.ai")
        try:
            if driver.find_element("iframe[src*='cloudflare']", "css selector"):
                print("⚠️ Cloudflare challenge detected! Please solve it manually.")
                input("Press Enter after solving the Cloudflare challenge...")
        except:
            pass
        input("Please log in manually and press Enter when done...")
        save_cookies(driver, account)


def random_scroll(driver):
    for _ in range(random.randint(1, 3)):
        scroll_amount = random.randint(100, 300)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        random_sleep(0.3, 0.7)


def download_artifacts(driver: webdriver.Chrome, video_number: str, account: str):
    try:
        artifact_buttons = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((
                By.XPATH, '//div[contains(@class, "artifact-block-cell ")]/parent::button[@aria-label="Preview contents"]'
            ))
        )
    except TimeoutException:
        print("❌ No artifacts found.")
        return

    video_name = ""
    failed_chapters = []

    for i, artifact_button in enumerate(artifact_buttons):
        chapter_name = f"Chapter_{i+1}"
        success = False

        for attempt in range(3):
            try:
                js_click_element(driver, artifact_button)
                time.sleep(2)

                complete_text = ""

                # Try clipboard
                try:
                    import pyperclip
                    pyperclip.copy("")
                    copy_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, '//div[contains(text(),"Copy")]/parent::div/parent::button'))
                    )
                    click_element(driver, copy_button)
                    time.sleep(2)
                    complete_text = pyperclip.paste().strip()
                    if len(complete_text) < 10:
                        raise ValueError("Too short from clipboard.")
                    print(f"✅ Clipboard worked for {chapter_name}")
                except:
                    # Fallback
                    paras = WebDriverWait(driver, 5).until(
                        EC.presence_of_all_elements_located((By.XPATH, '//div[@id="markdown-artifact"]//p'))
                    )
                    complete_text = "\n".join(p.text.strip() for p in paras if p.text.strip())
                    if len(complete_text) < 10:
                        raise ValueError("Too short from fallback.")
                    print(f"✅ Fallback worked for {chapter_name}")

                if not video_name:
                    try:
                        title_el = driver.find_element(By.XPATH, '//button[@data-testid="chat-menu-trigger"]/div/div')
                        video_name = clean_file_name(title_el.text) + f"_{video_number}"
                    except:
                        video_name = f"Video_{video_number}"

                output_dir = os.path.join("outputFiles", account, video_name)
                os.makedirs(output_dir, exist_ok=True)
                chapter_path = os.path.join(output_dir, f"{chapter_name}.txt")
                with open(chapter_path, "w", encoding="utf-8") as f:
                    f.write(complete_text)

                print(f"✅ Saved {chapter_name}.txt")
                success = True
                break  # done with retries

            except Exception as e:
                print(f"⚠️ Retry {attempt+1} failed for {chapter_name}: {e}")
                time.sleep(2)

        if not success:
            failed_chapters.append(chapter_name)

    if failed_chapters:
        print(f"❌ Failed to save chapters: {failed_chapters}")

 

def enter_prompt(driver: webdriver.Chrome, prompt: str):
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            print(f"🔍 Attempt {attempt}: locating input field...")
            input_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//div[@aria-label="Write your prompt to Claude"]'))
            )
            input_field.click()
            print("✅ Input field found and clicked.")
            break
        except TimeoutException:
            print(f"⚠️ Attempt {attempt}: Input field not found. Retrying...")
            random_sleep(1, 2)
    else:
        raise Exception("❌ Input field not found after multiple retries.")

    actions = ActionChains(driver)
    for char in prompt:
        actions.send_keys(char)
        actions.perform()
        random_sleep(0.01, 0.04)

    for attempt in range(1, max_retries + 1):
        try:
            print(f"🔍 Attempt {attempt}: locating Send button...")
            send_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Send message"]'))
            )
            driver.execute_script("arguments[0].click();", send_button)
            print("✅ Prompt sent.")
            random_sleep(1, 1.5)
            return
        except TimeoutException:
            print(f"⚠️ Attempt {attempt}: Send button not found. Retrying...")
            if check_limit_reached(driver):
                print("⚠️ Limit reached during send. Executing limit handling...")
                limit_reached_seq(driver)
                return
            random_sleep(2, 3)

    raise Exception("❌ Send button not found after multiple retries.")



def wait_for_response(driver: webdriver.Chrome):
    start = time.time()
    while True:
        if time.time() - start > 900:
            print("⚠️ Timeout: 15 minutes waiting for response.")
            return
        try:
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.XPATH, '//button[@aria-label="Stop response"]'))
            )
            break
        except:
            pass
        random_sleep(0.5, 1.5)

    while True:
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//button[@aria-label="Stop response"]'))
            )
        except TimeoutException:
            break
        random_sleep(0.5, 1.5)



def limit_reached_seq(driver):
    print("⚠️ Limit reached. Waiting...")
    get_reactivation_time(driver)
    time.sleep(10)
    driver.get(driver.current_url)
    ActionChains(driver).send_keys(Keys.RETURN).perform()
