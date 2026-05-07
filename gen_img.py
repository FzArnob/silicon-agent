from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")

    context = browser.contexts[0]
    page = context.pages[0]  # Use the first existing tab instead of creating a new one
    
    page.goto("https://chatgpt.com")

    input_box = page.locator("textarea")
    input_box.fill("Hello, ChatGPT! Can you generate an image of a cat wearing a hat?")
    page.keyboard.press("Enter")
    
    input("Press ENTER to close...")