import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def enter_prompt(driver, prompt):
    try:
        input_box = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "textarea"))
        )
        input_box.clear()
        input_box.send_keys(prompt)
        input_box.send_keys(Keys.RETURN)
        print(f"Sent prompt: {prompt}")
    except Exception as e:
        print(f"[ERROR] Failed to send prompt: {e}")


def wait_for_response(driver, timeout=60):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: "Stop generating" not in d.page_source
        )
        print("✅ Response completed.")
    except Exception as e:
        print(f"[WARNING] Timed out waiting for response: {e}")


def download_artifacts(driver, download_folder):
    try:
        # Look for download buttons — you may need to adapt this selector
        download_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Download')]")
        if not download_buttons:
            print("[WARNING] No download button found.")
            return

        os.makedirs(download_folder, exist_ok=True)

        for i, button in enumerate(download_buttons):
            try:
                button.click()
                time.sleep(2)  # wait for download to trigger
                print(f"✅ Download {i+1} triggered.")
            except Exception as e:
                print(f"[ERROR] Failed to click download button {i+1}: {e}")
    except Exception as e:
        print(f"[ERROR] Issue in download_artifacts: {e}")
