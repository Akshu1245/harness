import os
import time
from dotenv import load_dotenv
from openai import OpenAI
import requests

load_dotenv()

respan_key = os.environ.get("RESPAN_API_KEY")
explabs_key = os.environ.get("EXPLABS_API_KEY")
apinex_key = os.environ.get("APINEX_API_KEY")
coarena_key = os.environ.get("COARENA_API_KEY")
free_ai_key = os.environ.get("FREE_AI_API_KEY")

results = []

def test_model(gateway_name, base_url, api_key, model_id, category, max_tokens=25):
    start = time.time()
    try:
        client = OpenAI(base_url=base_url, api_key=api_key)
        tokens = 250 if "r1" in model_id.lower() or "thinking" in model_id.lower() else max_tokens
        resp = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "Return the exact word OK"}],
            max_tokens=tokens,
            timeout=15
        )
        latency = round((time.time() - start) * 1000, 1)
        content = (resp.choices[0].message.content or resp.choices[0].message.reasoning or "").strip()
        results.append({
            "gateway": gateway_name,
            "model": model_id,
            "category": category,
            "status": "ONLINE",
            "latency_ms": latency,
            "response": content[:30]
        })
        print(f"[{gateway_name}] {model_id} -> ONLINE ({latency}ms)")
    except Exception as e:
        latency = round((time.time() - start) * 1000, 1)
        err_msg = str(e)
        if "401" in err_msg:
            status = "401 Unauthorized / Needs Credits"
        elif "402" in err_msg:
            status = "402 Payment Required"
        elif "403" in err_msg:
            status = "403 Model Not Granted / Quota"
        elif "404" in err_msg:
            status = "404 Not Found"
        elif "429" in err_msg:
            status = "429 Rate Limit"
        else:
            status = f"ERROR: {err_msg[:60]}"
        results.append({
            "gateway": gateway_name,
            "model": model_id,
            "category": category,
            "status": status,
            "latency_ms": latency,
            "response": None
        })
        print(f"[{gateway_name}] {model_id} -> {status} ({latency}ms)")

print("=== AUDITING ALL MODELS ACROSS GATEWAYS ===")

# 1. Respan Models
test_model("Respan", "https://gateway.respan.ai/v1", respan_key, "respan/gemini-4-carbon:free", "Frontier Reasoning")
test_model("Respan", "https://gateway.respan.ai/v1", respan_key, "meta/muse-ember:free", "UI & Design")
test_model("Respan", "https://gateway.respan.ai/v1", respan_key, "claude-fable-5.2", "Paid Claude")

# 2. Experiential Labs
test_model("Experiential", "https://api.experientiallabs.ai/v1", explabs_key, "claude-fable-5.2:free", "Audit & Architecture")

# 3. APInex Free Mesh
test_model("APInex", "https://api.apinex.bond/v1", apinex_key, "free/qwen-3.8-max", "Rust & Tokio Systems")
test_model("APInex", "https://api.apinex.bond/v1", apinex_key, "free/deepseek-v4-pro-0813", "Red Team & Bug Bounty")
test_model("APInex", "https://api.apinex.bond/v1", apinex_key, "free/kimi-k3", "Hackathon Recon & Docs")
test_model("APInex", "https://api.apinex.bond/v1", apinex_key, "free/gpt-6-luna", "Code Synthesis")
test_model("APInex", "https://api.apinex.bond/v1", apinex_key, "free/gemini-3.8-flash", "High-Speed Dispatch")
test_model("APInex", "https://api.apinex.bond/v1", apinex_key, "free/deepseek-v4.1-flash", "Fast Agent Loops")
test_model("APInex", "https://api.apinex.bond/v1", apinex_key, "free/glm-5.3", "Multimodal Analysis")
test_model("APInex", "https://api.apinex.bond/v1", apinex_key, "free/jev-1.13", "Probabilistic Router")
test_model("APInex", "https://api.apinex.bond/v1", apinex_key, "free/minimax-m3.1-flash", "Context Compaction")
test_model("APInex", "https://api.apinex.bond/v1", apinex_key, "free/hy4", "General Reasoning")

# 4. APInex Paid Claude endpoint
test_model("APInex", "https://api.apinex.bond/v1", apinex_key, "claude-fable-5.2", "Paid Claude")

# 5. Free.ai Startup Grant Models (15M Tokens)
if free_ai_key:
    test_model("Free.ai", "https://api.free.ai/v1", free_ai_key, "qwen-coder", "Grant Code")
    test_model("Free.ai", "https://api.free.ai/v1", free_ai_key, "qwen7b", "Grant General")
    test_model("Free.ai", "https://api.free.ai/v1", free_ai_key, "deepseek-r1-7b", "Grant Deep Thinking")

# 6. Coarena Emergency Gate
test_model("Coarena", "https://coarena.ai/api/v1", coarena_key, "gpt-6-1-sol", "Emergency Tie-Breaker")

import json
with open(r"d:\unreseted ai\all_models_live_status.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nSaved full audit to d:\\unreseted ai\\all_models_live_status.json")
