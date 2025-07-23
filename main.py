import traceback, tempfile, json, os, sys, logging, time
from seleniumbase import Driver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from modules.automation_parts import *

def atomic_write(filepath, data):
    with tempfile.NamedTemporaryFile("w", delete=False, dir=os.path.dirname(filepath)) as tmp:
        json.dump(data, tmp)
        tempname = tmp.name
    os.replace(tempname, filepath)

def select_account():
    accounts = [f for f in os.listdir("accounts") if os.path.isdir(os.path.join("accounts", f))]
    if not accounts:
        print("No accounts found."); sys.exit(1)
    for i, acc in enumerate(accounts): print(f"{i + 1}. {acc}")
    while True:
        choice = input(f"Select account (1-{len(accounts)}): ")
        if choice.isdigit() and 1 <= int(choice) <= len(accounts):
            return accounts[int(choice)-1]

def select_config():
    if not os.path.exists("configs"): os.makedirs("configs")
    configs = [f for f in os.listdir("configs") if os.path.isdir(os.path.join("configs", f))]
    if not configs:
        print("No configs found."); sys.exit(1)
    for i, cfg in enumerate(configs): print(f"{i + 1}. {cfg}")
    while True:
        choice = input(f"Select config (1-{len(configs)}): ")
        if choice.isdigit() and 1 <= int(choice) <= len(configs):
            return configs[int(choice)-1]

def load_config(name):
    path = os.path.join("configs", name, "config.json")
    try:
        with open(path, "r") as f:
            config = json.load(f)
        for k in ["project_link", "initial_prompt", "generation_prompts", "text_to_be_replaced_by_video_number"]:
            if k not in config: raise KeyError(f"Missing: {k}")
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

def claude_automation():
    print("\n" + "="*70)
    print(" Claude Automation Script ".center(70))
    print("="*70)

    account = select_account()
    config_name = select_config()
    config = load_config(config_name)
    if not config: return

    while True:
        try:
            rng = input("Enter video numbers (e.g. 3-7): ").split("-")
            if len(rng) != 2: raise ValueError
            video_start, video_end = map(int, rng)
            break
        except:
            print("❌ Invalid input. Use format 3-7.")

    progress_dir = os.path.join("progress_files", f"{account}_{config_name}")
    os.makedirs(progress_dir, exist_ok=True)

    # Detect which videos were completed
    completed = []
    for f in os.listdir(progress_dir):
        if f.endswith(".json"):
            try:
                num = int(f.split(".")[0])
                completed.append(num)
            except:
                continue

    if completed:
        last_done = max(completed)
        if last_done >= video_start:
            video_start = last_done + 1
            print(f"▶️ Resuming from video: {video_start}")

    while True:
        try:
            headless = config.get("headless_mode", False)
            close_browser = config.get("close_browser_on_crash", True)

            driver = Driver(
                uc=True,
                headless2=headless,
                chromium_arg=[
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding"
                ]
            )
            driver.maximize_window()
            handle_login(driver, account)

            for video_number in range(video_start, video_end + 1):
                progress_file = os.path.join(progress_dir, f"{video_number}.json")
                if os.path.exists(progress_file):
                    print(f"⏩ Skipping video {video_number} (already completed)")
                    continue

                try:
                    print(f"\n🎬 Processing Video #{video_number}")
                    driver.get(config["project_link"])
                    if check_limit_reached(driver): limit_reached_seq(driver)

                    prompt = config["initial_prompt"].replace(
                        config["text_to_be_replaced_by_video_number"], str(video_number)
                    )
                    enter_prompt(driver, prompt)
                    wait_for_response(driver)

                    for i, prompt2 in enumerate(config["generation_prompts"]):
                        print(f"➕ Gen Prompt {i+1}")
                        enter_prompt(driver, prompt2)
                        if check_limit_reached(driver): limit_reached_seq(driver)
                        wait_for_response(driver)

                    download_artifacts(driver, str(video_number), f"{account}-{config_name}")
                    atomic_write(progress_file, {"completed": True})
                    print(f"✅ Progress saved for {video_number}")

                except Exception as ve:
                    print(f"🚫 Error during video {video_number}: {ve}")
                    raise ve

            save_cookies(driver, account)
            driver.quit()
            break
        except Exception as outer:
            print(f"🛑 Script crashed: {outer}")
            logging.info(traceback.format_exc())
            try:
                if close_browser:
                    driver.quit()
            except: pass
            time.sleep(10)

if __name__ == "__main__":
    claude_automation()
