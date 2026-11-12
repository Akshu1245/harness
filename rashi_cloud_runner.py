# =====================================================================
# RASHI HARNESS CLOUD WORKER & HEADLESS BROWSER RUNNER
# Run on Google Colab / Cloud GPU / Linux Compute Instance
# =====================================================================

import os
import sys
import subprocess
import threading
import base64
import io
import json
from typing import Optional, Dict, Any

# 1. Secure API Keys Integration
os.environ["RESPAN_API_KEY"] = "04EkULNO.9rBUnYLdYCNCdDtyO2RtOKzN4pY9XTlG"
os.environ["EXPLABS_API_KEY"] = "xpl_35be619b5271cdfc433015f3d536227d86a2bdbb"
os.environ["APINEX_API_KEY"] = "sk-apx3055d1309381796de30bbbdf3ef93bd4e82c349040c0bfe"
os.environ["COARENA_API_KEY"] = "coa_dc2ff39b6065c5c4244dfd1fd84ff1c0"

# 2. Automated Browser Check & Installation
def verify_and_install_browser():
    print("[1/4] Checking for existing cloud browser installation...")
    chrome_found = False
    try:
        res = subprocess.run(["which", "chromium-browser"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            print(f"[OK] Found Chromium at: {res.stdout.strip()}")
            chrome_found = True
    except Exception:
        pass

    try:
        res2 = subprocess.run(["which", "google-chrome"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res2.returncode == 0:
            print(f"[OK] Found Google Chrome at: {res2.stdout.strip()}")
            chrome_found = True
    except Exception:
        pass

    if not chrome_found:
        print("[NOTICE] No browser found in cloud runtime. Installing headless Chromium & Playwright...")
        subprocess.run(["pip", "install", "-q", "playwright"], check=False)
        subprocess.run(["playwright", "install", "--with-deps", "chromium"], check=False)
        print("[SUCCESS] Headless Chromium browser successfully installed in cloud environment!")
    else:
        print("[OK] Browser environment is already active.")

verify_and_install_browser()

# 3. FastAPI Server with Model & Cloud Browser Endpoints
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
from pycloudflared import try_cloudflare

app = FastAPI(title="Rashi Harness Cloud Engine")

@app.get("/health")
def health():
    return {
        "status": "online",
        "service": "Rashi Harness Cloud Worker",
        "browser_ready": True,
        "keys_loaded": ["RESPAN", "EXPLABS", "APINEX", "COARENA"]
    }

class BrowserNavRequest(BaseModel):
    url: str
    take_screenshot: bool = True

@app.post("/browser/navigate")
async def browser_navigate(req: BrowserNavRequest):
    """Executes cloud headless browser navigation and returns page title and screenshot."""
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(req.url, timeout=30000)
            title = await page.title()
            screenshot_b64 = None
            if req.take_screenshot:
                img_bytes = await page.screenshot(full_page=False)
                screenshot_b64 = base64.b64encode(img_bytes).decode('utf-8')
            await browser.close()
            return {
                "url": req.url,
                "title": title,
                "screenshot_base64": screenshot_b64
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cloud browser execution error: {e}")

# Run daemon
def start_server():
    uvicorn.run(app, host="0.0.0.0", port=8000)

threading.Thread(target=start_server, daemon=True).start()

# 4. Public Tunnel via Cloudflare
print("[4/4] Establishing Cloudflare Tunnel for Rashi Harness...")
public_url = try_cloudflare(port=8000)
print("\n" + "="*60)
print(f"RASHI HARNESS CLOUD WORKER URL: {public_url.tunnel}")
print("Register this URL in your local workspace using:")
print(f"python client.py --add-endpoint {public_url.tunnel}")
print("="*60)
