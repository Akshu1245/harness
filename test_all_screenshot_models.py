import os
import time
from dotenv import load_dotenv
from openai import OpenAI
import requests

load_dotenv()

APINEX_BASE_URL = "https://api.apinex.bond/v1"
APINEX_API_KEY = os.environ.get("APINEX_API_KEY")

client = OpenAI(base_url=APINEX_BASE_URL, api_key=APINEX_API_KEY)

# All 13 models from screenshots
CHAT_MODELS = [
    "free/kimi-k3",
    "free/deepseek-v4.1-flash",
    "free/gemini-3.8-flash",
    "free/qwen-3.8-max",
    "free/glm-5.3-flash",
    "free/deepseek-v4-pro-0813",
    "free/deepseek-v4-flash-0731",
    "free/hy4",
    "free/muse-spark-1.3",
    "free/minimax-m3.1-flash",
    "free/gpt-6-luna",
    "free/glm-5.3",
]

DECISION_MODELS = [
    "free/jev-1.13",
]

results = []

print("Starting complete test of all screenshot models on APInex...\n")

for model_id in CHAT_MODELS:
    start_t = time.time()
    try:
        resp = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "Respond with 'READY' and your name in 5 words."}],
            max_tokens=25,
            timeout=20,
        )
        latency = round(time.time() - start_t, 2)
        content = resp.choices[0].message.content.strip().replace("\n", " ")
        results.append({
            "model": model_id,
            "status": "ONLINE (200)",
            "latency": f"{latency}s",
            "reply": content[:40],
        })
        print(f"[OK] {model_id:<28} | {latency}s | {content[:35]}")
    except Exception as e:
        latency = round(time.time() - start_t, 2)
        err_msg = str(e).split("\n")[0][:40]
        results.append({
            "model": model_id,
            "status": "ERROR",
            "latency": f"{latency}s",
            "reply": err_msg,
        })
        print(f"[ERR] {model_id:<28} | {latency}s | {err_msg}")

# Test Jev 1.13 Decision Model
for model_id in DECISION_MODELS:
    start_t = time.time()
    try:
        payload = {
            "model": model_id,
            "state": "Test state for decision verification.",
            "questions": {
                "test_q": {
                    "type": "noul",
                    "instructions": "Is this system online?"
                }
            }
        }
        res = requests.post(
            f"{APINEX_BASE_URL}/decisions",
            headers={"Authorization": f"Bearer {APINEX_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=15,
        )
        latency = round(time.time() - start_t, 2)
        if res.status_code == 200:
            data = res.json()
            val = data.get("answers", {}).get("test_q", {}).get("noul", "OK")
            results.append({
                "model": model_id + " (Decisions API)",
                "status": "ONLINE (200)",
                "latency": f"{latency}s",
                "reply": f"Prob: {val}",
            })
            print(f"[OK] {model_id:<28} | {latency}s | Prob: {val}")
        else:
            results.append({
                "model": model_id + " (Decisions API)",
                "status": f"HTTP {res.status_code}",
                "latency": f"{latency}s",
                "reply": res.text[:40],
            })
            print(f"[ERR] {model_id:<28} | {latency}s | HTTP {res.status_code}")
    except Exception as e:
        latency = round(time.time() - start_t, 2)
        results.append({
            "model": model_id,
            "status": "ERROR",
            "latency": f"{latency}s",
            "reply": str(e)[:40],
        })
        print(f"[ERR] {model_id:<28} | {latency}s | {e}")

print("\nFinished testing all 13 models.")
