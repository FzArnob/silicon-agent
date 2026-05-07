from playwright.sync_api import sync_playwright

with sync_playwright() as p:

    browser = p.chromium.launch_persistent_context(
        user_data_dir="./brave_profile",

        executable_path="C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe",

        headless=False,
        viewport=None,

        ignore_default_args=["--enable-automation"],

        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--start-maximized"
        ]
    )

    page = browser.new_page()

    page.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    })
    """)

    page.goto("https://chatgpt.com")

    input("Log in manually, then press ENTER here...")