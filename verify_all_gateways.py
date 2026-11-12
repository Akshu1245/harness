import os
from dotenv import load_dotenv
from openai import OpenAI
import requests

load_dotenv()

results = {}

# 1. Respan Gateway
try:
    client_respan = OpenAI(base_url="https://gateway.respan.ai/v1", api_key=os.environ.get("RESPAN_API_KEY"))
    r_carbon = client_respan.chat.completions.create(
        model="respan/gemini-4-carbon:free",
        messages=[{"role": "user", "content": "Ping"}],
        max_tokens=10
    )
    results["Respan: Google Gemini 4 Carbon"] = "LIVE & WORKING (200 OK)"
    
    r_muse = client_respan.chat.completions.create(
        model="meta/muse-ember:free",
        messages=[{"role": "user", "content": "Ping"}],
        max_tokens=10
    )
    results["Respan: Meta Muse Ember"] = "LIVE & WORKING (200 OK)"
except Exception as e:
    results["Respan Gateway"] = f"FAILED: {e}"

# 2. Experiential Labs Gateway
try:
    client_exp = OpenAI(base_url="https://api.experientiallabs.ai/v1", api_key=os.environ.get("EXPLABS_API_KEY"))
    r_fable = client_exp.chat.completions.create(
        model="claude-fable-5.2:free",
        messages=[{"role": "user", "content": "Ping"}],
        max_tokens=10
    )
    results["Experiential: Anthropic Claude Fable 5.2"] = "LIVE & WORKING (200 OK)"
except Exception as e:
    results["Experiential Labs"] = f"FAILED: {e}"

# 3. APInex Gateway
try:
    client_apx = OpenAI(base_url="https://api.apinex.bond/v1", api_key=os.environ.get("APINEX_API_KEY"))
    
    r_qwen = client_apx.chat.completions.create(
        model="free/qwen-3.8-max",
        messages=[{"role": "user", "content": "Ping"}],
        max_tokens=10
    )
    results["APInex: Qwen 3.8 MAX"] = "LIVE & WORKING (200 OK)"
    
    r_deepseek = client_apx.chat.completions.create(
        model="free/deepseek-v4-pro-0813",
        messages=[{"role": "user", "content": "Ping"}],
        max_tokens=10
    )
    results["APInex: DeepSeek V4 Pro"] = "LIVE & WORKING (200 OK)"

    r_luna = client_apx.chat.completions.create(
        model="free/gpt-6-luna",
        messages=[{"role": "user", "content": "Ping"}],
        max_tokens=10
    )
    results["APInex: GPT-6 Luna"] = "LIVE & WORKING (200 OK)"

    # APInex Web Search Tool
    tool_res = requests.post(
        "https://api.apinex.bond/v1/tools/web/search",
        headers={"Authorization": f"Bearer {os.environ.get('APINEX_API_KEY')}", "Content-Type": "application/json"},
        json={"query": "test", "count": 1},
        timeout=10
    )
    if tool_res.status_code == 200:
        results["APInex: Live Web Search Tool"] = "LIVE & WORKING (200 OK)"
    else:
        results["APInex: Live Web Search Tool"] = f"FAILED: HTTP {tool_res.status_code}"
except Exception as e:
    results["APInex Gateway"] = f"FAILED: {e}"

print("\n" + "="*50)
print("       ALL GATEWAYS & API KEYS STATUS CHECK")
print("="*50)
for service, status in results.items():
    print(f"  ✓ {service:<38} -> {status}")
print("="*50 + "\n")
