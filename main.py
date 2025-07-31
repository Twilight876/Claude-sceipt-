import time
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from automation_parts import enter_prompt, wait_for_response, download_artifacts

def load_config():
    with open("config.json") as f:
        return json.load(f)

def setup_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_experimental_option("prefs", {
        "download.prompt_for_download": False,
        "download.directory_upgrade": True
    })
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def main():
    config = load_config()
    driver = setup_browser()

    driver.get(config["claude_url"])
    input("🔒 Login to Claude manually, then press ENTER to continue...")

    for idx, prompt in enumerate(config["prompts"]):
        print(f"\n➡️ Sending prompt {idx+1}/{len(config['prompts'])}")
        enter_prompt(driver, prompt)
        wait_for_response(driver)
        download_artifacts(driver, config["download_folder"])
        time.sleep(config.get("delay_between_prompts", 10))

    print("\n✅ Automation complete.")
    driver.quit()

if __name__ == "__main__":
    main()
