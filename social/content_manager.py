import argparse
import asyncio
import json
import os
import subprocess
import tkinter as tk
import urllib.request
from playwright.async_api import async_playwright, Page as AsyncPage

BROWSER_PATH_FILE = os.path.join(os.path.dirname(__file__), "browser_path.txt")
PROFILE_BASE_DIR = os.path.join(os.path.dirname(__file__), "browsers")
POLL_INTERVAL = 5  # seconds between re-checks when waiting for login
CDP_PORT = 9223
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"

PLATFORMS = [
    {
        "name": "YouTube",
        "url": "https://www.youtube.com",
        "logged_in_selector": 'button[aria-label="Account menu"]',
    },
    {
        "name": "Facebook",
        "url": "https://www.facebook.com",
        "logged_in_selector": '[aria-label="Your profile"]',
    },
    {
        "name": "Instagram",
        "url": "https://www.instagram.com",
        "logged_in_selector": 'a[href*="/direct/inbox/"]',
    },
    {
        "name": "TikTok",
        "url": "https://www.tiktok.com",
        "logged_in_selector": [ '[data-e2e="profile-icon"]', '[data-e2e="inbox-icon"]' ],
    },
]

STATUS_STYLES = {
    "checking": ("#888888", "Checking..."),
    "logged_in": ("#22c55e", "Logged In"),
    "waiting":   ("#f97316", "Waiting for Login"),
    "confirmed": ("#22c55e", "Login Confirmed"),
    "failed":    ("#ef4444", "Error"),
}


# ── UI ────────────────────────────────────────────────────────────────────────

class LoginUI:
    BG = "#16213e"
    ROW_BG = "#1a1a2e"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Content Manager")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self._rows: dict[str, tuple] = {}
        self._build()

    def _build(self):
        tk.Label(
            self.root, text="Login Status",
            bg=self.BG, fg="#ffffff",
            font=("Segoe UI", 13, "bold"),
            padx=20, pady=14,
        ).pack(fill="x")

        tk.Frame(self.root, bg="#2a2a45", height=1).pack(fill="x")

        for p in PLATFORMS:
            row = tk.Frame(self.root, bg=self.ROW_BG, padx=20, pady=11)
            row.pack(fill="x")

            dot = tk.Label(row, text="●", bg=self.ROW_BG, fg="#888888",
                           font=("Segoe UI", 11))
            dot.pack(side="left")

            tk.Label(row, text=f"  {p['name']}", bg=self.ROW_BG, fg="#dddddd",
                     font=("Segoe UI", 10), width=11, anchor="w").pack(side="left")

            status = tk.Label(row, text="Checking...", bg=self.ROW_BG, fg="#888888",
                              font=("Segoe UI", 10, "italic"), anchor="e")
            status.pack(side="right")

            self._rows[p["name"]] = (dot, status)

        tk.Frame(self.root, bg=self.BG, height=10).pack(fill="x")
        self.root.geometry(f"320x{58 + len(PLATFORMS) * 48}")

    def set_status(self, name: str, state: str):
        self.root.after(0, lambda: self._apply(name, state))

    def _apply(self, name: str, state: str):
        color, text = STATUS_STYLES.get(state, ("#888888", state))
        dot, lbl = self._rows[name]
        dot.configure(fg=color)
        lbl.configure(fg=color, text=text)

    def run(self):
        self.root.mainloop()


# ── CDP helpers ──────────────────────────────────────────────────────────────

def _fix_exit_type(profile_dir: str):
    """Mark the profile as cleanly exited so Brave won't show the restore dialog."""
    prefs_path = os.path.join(profile_dir, "Default", "Preferences")
    if not os.path.isfile(prefs_path):
        return
    try:
        with open(prefs_path, "r", encoding="utf-8") as f:
            prefs = json.load(f)
        changed = False
        if prefs.get("profile", {}).get("exit_type") != "Normal":
            prefs.setdefault("profile", {})["exit_type"] = "Normal"
            changed = True
        if prefs.get("profile", {}).get("exited_cleanly") is not True:
            prefs.setdefault("profile", {})["exited_cleanly"] = True
            changed = True
        if changed:
            with open(prefs_path, "w", encoding="utf-8") as f:
                json.dump(prefs, f)
    except Exception:
        pass


def _is_cdp_ready() -> bool:
    try:
        urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=2)
        return True
    except Exception:
        return False


def _launch_browser(executable: str, profile_dir: str) -> subprocess.Popen:
    return subprocess.Popen(
        [
            executable,
            f"--remote-debugging-port={CDP_PORT}",
            "--remote-debugging-address=127.0.0.1",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-session-crashed-bubble",
            "--disable-restore-session-state",
            "--disable-blink-features=AutomationControlled",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def _wait_for_cdp(timeout: int = 30) -> bool:
    for _ in range(timeout):
        if _is_cdp_ready():
            return True
        await asyncio.sleep(1)
    return False


# ── Playwright async logic ────────────────────────────────────────────────────

async def is_logged_in(page: AsyncPage, selector: str | list, timeout: int = 6000) -> bool:
    selectors = selector if isinstance(selector, list) else [selector]

    for s in selectors:
        try:
            if await page.locator(s).count() > 0:
                return True
        except Exception:
            continue

    return False


async def check_platform(page: AsyncPage, platform: dict, ui: LoginUI):
    name = platform["name"]
    ui.set_status(name, "checking")

    try:
        try:
            await page.goto(platform["url"], wait_until="domcontentloaded", timeout=30000)
        except Exception as nav_err:
            if "net::ERR_HTTP_RESPONSE_CODE_FAILURE" in str(nav_err):
                print(f"[{name}] Blocked — retrying with JS navigation...")
                await asyncio.sleep(3)
                await page.evaluate(f'window.location.href = "{platform["url"]}"')
                await page.wait_for_load_state("domcontentloaded", timeout=30000)
            else:
                raise
        await asyncio.sleep(3)

        if await is_logged_in(page, platform["logged_in_selector"]):
            ui.set_status(name, "logged_in")
            return

        ui.set_status(name, "waiting")

        while True:
            await asyncio.sleep(POLL_INTERVAL)
            if await is_logged_in(page, platform["logged_in_selector"], timeout=3000):
                ui.set_status(name, "confirmed")
                return

    except Exception as e:
        print(f"[{name}] Error: {e}")
        ui.set_status(name, "failed")


async def browser_main(browser_name: str, ui: LoginUI, context_holder: list = []):
    profile_dir = os.path.join(PROFILE_BASE_DIR, browser_name)
    os.makedirs(profile_dir, exist_ok=True)
    executable = _get_browser_path(browser_name)

    print(f"[ContentManager] Browser : {browser_name}")
    print(f"[ContentManager] Profile : {profile_dir}")
    print(f"[ContentManager] CDP     : {CDP_URL}")

    proc: subprocess.Popen | None = None
    if not _is_cdp_ready():
        _fix_exit_type(profile_dir)
        print(f"[ContentManager] Launching browser on port {CDP_PORT}...")
        proc = _launch_browser(executable, profile_dir)
        if not await _wait_for_cdp():
            print("[ContentManager] ERROR: CDP endpoint not ready after 30s.")
            return

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()

        context_holder.append((browser, context, proc))

        # Close extra tabs from session restore
        for extra in context.pages[1:]:
            await extra.close()
        first_page = context.pages[0] if context.pages else await context.new_page()

        # One fixed tab per platform
        pages = [first_page] + [await context.new_page() for _ in PLATFORMS[1:]]

        # Check all platforms concurrently
        await asyncio.gather(*(
            check_platform(page, platform, ui)
            for platform, page in zip(PLATFORMS, pages)
        ))

        print("[ContentManager] All checks complete.")


def run(browser_name: str = "brave"):
    ui = LoginUI()
    _loop = asyncio.new_event_loop()
    _context_holder: list = []  # shared ref so on_close can access the context

    async def _async_main():
        await browser_main(browser_name, ui, _context_holder)

    async def _cleanup():
        if _context_holder:
            browser, ctx, proc = _context_holder[0]
            try:
                await asyncio.gather(*(
                    page.goto("about:blank") for page in ctx.pages
                ), return_exceptions=True)
                # Wait for Chromium to flush cookies/session to disk before killing
                await asyncio.sleep(2)
                await browser.close()
            except Exception:
                pass
            if proc and proc.poll() is None:
                proc.terminate()

    def on_close():
        if _loop.is_running():
            asyncio.run_coroutine_threadsafe(_cleanup(), _loop)
        else:
            # Loop already finished — run a fresh loop for graceful shutdown
            if _context_holder:
                browser, ctx, proc = _context_holder[0]
                async def _sync_cleanup():
                    try:
                        await asyncio.gather(*(
                            page.goto("about:blank") for page in ctx.pages
                        ), return_exceptions=True)
                        await asyncio.sleep(2)
                        await browser.close()
                    except Exception:
                        pass
                    if proc and proc.poll() is None:
                        proc.terminate()
                asyncio.run(_sync_cleanup())
        ui.root.after(100, ui.root.destroy)

    ui.root.protocol("WM_DELETE_WINDOW", on_close)

    import threading
    def _run_async():
        _loop.run_until_complete(_async_main())

    threading.Thread(target=_run_async, daemon=True).start()
    ui.run()


def _get_browser_path(browser_name: str) -> str:
    if not os.path.isfile(BROWSER_PATH_FILE):
        raise FileNotFoundError(
            f"browser_path.txt not found at: {BROWSER_PATH_FILE}"
        )

    with open(BROWSER_PATH_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            name, _, path = line.partition("=")
            if name.strip().lower() == browser_name.lower():
                path = path.strip()
                if not os.path.isfile(path):
                    raise FileNotFoundError(
                        f"Executable for '{browser_name}' not found: {path}"
                    )
                return path

    raise KeyError(
        f"Browser '{browser_name}' not found in {BROWSER_PATH_FILE}. "
        f"Add a line like: {browser_name}=C:\\path\\to\\browser.exe"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--browser",
        type=str,
        default="brave",
        help="Browser name as defined in social/browser_path.txt (default: brave)",
    )
    args = parser.parse_args()
    run(browser_name=args.browser)
