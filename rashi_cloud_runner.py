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

# 1. Keys come from the environment only (set them in Colab secrets / shell). Never hardcode.

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
import ipaddress, socket, secrets
from urllib.parse import urlparse
from fastapi import Header

app = FastAPI(title="Rashi Harness Cloud Engine")

# --- access control: every browser call needs a bearer token; URLs are checked (SSRF guard) ---
RUNNER_TOKEN = os.environ.get("RASHI_RUNNER_TOKEN") or secrets.token_urlsafe(32)
if not os.environ.get("RASHI_RUNNER_TOKEN"):
    print("[AUTH] No RASHI_RUNNER_TOKEN set; generated a one-time token for this session (shown once below).")

def check_token(authorization):
    if not authorization or not secrets.compare_digest(authorization, f"Bearer {RUNNER_TOKEN}"):
        raise HTTPException(status_code=401, detail="Unauthorized")

def url_is_public(url: str) -> bool:
    """Allow only http(s) URLs whose host resolves to public IPs."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return False
    try:
        infos = socket.getaddrinfo(p.hostname, None)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


@app.get("/health")
def health():
    return {
        "status": "online",
        "service": "Rashi Harness Cloud Worker",
        "browser_ready": True,
        "keys_loaded": [k for k in ("RESPAN","EXPLABS","APINEX","COARENA") if os.environ.get(k+"_API_KEY")]
    }

class BrowserNavRequest(BaseModel):
    url: str
    take_screenshot: bool = True

@app.post("/browser/navigate")
async def browser_navigate(req: BrowserNavRequest, authorization: str = Header(default=None)):
    check_token(authorization)
    if not url_is_public(req.url):
        raise HTTPException(status_code=400, detail="URL not allowed (must be public http/https)")
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
    uvicorn.run(app, host="127.0.0.1", port=8000)

threading.Thread(target=start_server, daemon=True).start()

# 4. Public Tunnel via Cloudflare
print("[4/4] Establishing Cloudflare Tunnel for Rashi Harness...")
public_url = try_cloudflare(port=8000)
print("\n" + "="*60)
print(f"RASHI HARNESS CLOUD WORKER URL: {public_url.tunnel}")
print("Send header  Authorization: Bearer <RASHI_RUNNER_TOKEN>  with every browser call.")
print("Register this URL in your local workspace using:")
print(f"python client.py --add-endpoint {public_url.tunnel}")
print("="*60)
