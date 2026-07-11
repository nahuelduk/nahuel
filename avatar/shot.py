#!/usr/bin/env python3
"""Captura vistas del avatar con Chromium headless (Playwright)."""
import sys
import subprocess
import time
import os

from playwright.sync_api import sync_playwright

VIEWS = sys.argv[1].split(",") if len(sys.argv) > 1 else [
    "front", "face", "side", "back", "threeq"]
EXPR = sys.argv[2] if len(sys.argv) > 2 else ""

os.chdir(os.path.dirname(os.path.abspath(__file__)))
server = subprocess.Popen(
    ["python3", "-m", "http.server", "8734"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
            if os.path.exists("/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
            else None,
            args=["--use-gl=angle", "--use-angle=swiftshader",
                  "--no-sandbox"])
        page = browser.new_page(viewport={"width": 900, "height": 1000})
        errors = []
        page.on("console", lambda m: errors.append(m.text)
                if m.type == "error" else None)
        for view in VIEWS:
            url = f"http://localhost:8734/viewer.html?view={view}"
            if EXPR:
                url += f"&expr={EXPR}"
            page.goto(url)
            try:
                page.wait_for_function(
                    "window.__ready === true || window.__error", timeout=30000)
            except Exception:
                print(f"[{view}] TIMEOUT; console: {errors[-3:]}")
                continue
            err = page.evaluate("window.__error || ''")
            if err:
                print(f"[{view}] ERROR: {err}")
                print("console:", errors[-5:])
            else:
                name = f"shot_{view}{'_' + EXPR.replace(':', '-').replace(',', '_') if EXPR else ''}.png"
                page.screenshot(path=name)
                print(f"[{view}] OK -> {name}")
        browser.close()
finally:
    server.terminate()
