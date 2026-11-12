import os
import time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url="https://api.experientiallabs.ai/v1", api_key=os.environ.get("EXPLABS_API_KEY"))

# Test the promotional models shown in the user's screenshot
candidates = [
    "clef",
    "clef-flash",
    "gpt-6-luna",
    "gpt-6-luna-decisions",
    "deepseek-v4.1-flash-uncensored",
    "deepseek-v4.1-flash-1017",
    "deepseek-v4-flash",
    "jev-latest",
    "qwen3.8-27b",
    "unslopnemo-12b",
    "ui-tars-1.5-7b",
    "weaver"
]

print("=== TESTING EXPERIENTIAL LABS PROMOTIONAL & FREE MODELS ===")
working = []

for m in candidates:
    start = time.time()
    try:
        resp = client.chat.completions.create(
            model=m,
            messages=[{"role": "user", "content": "Respond with the word SUCCESS"}],
            max_tokens=15,
            timeout=10
        )
        latency = round((time.time() - start) * 1000, 1)
        content = (resp.choices[0].message.content or "").strip()
        print(f"[ONLINE] {m} ({latency}ms) -> {content}")
        working.append({"model": m, "latency": latency, "response": content})
    except Exception as e:
        latency = round((time.time() - start) * 1000, 1)
        err = str(e)
        if "403" in err:
            status = "403 Not Granted"
        elif "402" in err:
            status = "402 Payment Required"
        elif "404" in err:
            status = "404 Not Found"
        else:
            status = err[:50]
        print(f"[FAILED] {m} ({latency}ms) -> {status}")

import json
with open(os.path.join(os.environ.get("RASHI_DATA_DIR","."), "explabs_working_free_models.json"), "w", encoding="utf-8") as f:
    json.dump(working, f, indent=2)

print(f"\nTotal working models found: {len(working)}")
