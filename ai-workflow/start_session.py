import argparse
import random
import time
from playwright.sync_api import sync_playwright
from prompt import generate_session_prompts


def human_type(page, locator, text):
    """Type text with random small breaks to mimic human typing."""
    locator.click()
    for char in text:
        if char == "\n":
            # Shift+Enter for newline (avoids sending the message)
            page.keyboard.press("Shift+Enter")
            time.sleep(random.uniform(0.05, 0.15))
            continue
        page.keyboard.type(char, delay=random.randint(20, 80))
        # Occasional longer pause (simulates thinking)
        if random.random() < 0.05:
            time.sleep(random.uniform(0.3, 0.8))
        # Small pause between words
        if char == " " and random.random() < 0.15:
            time.sleep(random.uniform(0.1, 0.4))


def send_prompt(page, text):
    """Type a prompt and send it with human-like typing."""
    input_box = page.locator('div#prompt-textarea[contenteditable="true"]')
    human_type(page, input_box, text)
    time.sleep(random.uniform(0.5, 1.5))
    page.keyboard.press("Enter")


def send_prompt_fast(page, text):
    """Fill the prompt instantly and send it."""
    input_box = page.locator('div#prompt-textarea[contenteditable="true"]')
    input_box.click()
    input_box.fill(text)
    time.sleep(random.uniform(0.3, 0.8))
    page.keyboard.press("Enter")


def wait_for_response(page, timeout=300):
    """Wait until ChatGPT finishes generating."""
    stop_btn = page.locator('button[aria-label="Stop answering"]')
    voice_btn = page.locator('button[aria-label="Start Voice"]')

    # If stop button is present, wait for it to disappear
    if stop_btn.is_visible():
        stop_btn.wait_for(state="hidden", timeout=timeout * 1000)

    # Wait for Start Voice button to appear — confirms generation is complete
    voice_btn.wait_for(state="visible", timeout=timeout * 1000)


def run_session(fast_input=False):
    master_prompt, image_prompts, config_row = generate_session_prompts()
    send = send_prompt_fast if fast_input else send_prompt
    print(f"[Session] Mode: {'fast' if fast_input else 'human-type'}")
    print(f"[Session] Setup: {config_row['Setup Name']}")
    print(f"[Session] Images: {len(image_prompts)}")

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = context.pages[0]

        page.goto("https://chatgpt.com")
        time.sleep(3)

        # Send master prompt first
        print("[Session] Sending master prompt...")
        send(page, master_prompt)
        print("[Session] Master prompt sent...")
        wait_for_response(page)

        # Wait random 10-30s before starting images
        delay = random.uniform(10, 30)
        print(f"[Session] Waiting {delay:.0f}s before images...")
        time.sleep(delay)

        # Send one prompt per image
        for i, image_prompt in enumerate(image_prompts, 1):
            print(f"[Session] Sending image {i}/{len(image_prompts)}...")
            send(page, image_prompt)
            wait_for_response(page)

            # Take random 2-4min break after each image (except last)
            if i < len(image_prompts):
                break_time = random.uniform(120, 240)
                print(f"[Session] Break: {break_time:.0f}s...")
                time.sleep(break_time)

        print("[Session] All images complete.")
        input("Press ENTER to close...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-fast-input", type=str, default="false", choices=["true", "false"])
    args = parser.parse_args()
    run_session(fast_input=args.fast_input == "true")