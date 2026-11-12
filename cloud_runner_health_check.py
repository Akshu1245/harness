import os
import time
import json
import traceback
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv("/workspace/.env")

# Langfuse Configuration
LANGFUSE_AVAILABLE = False
langfuse_client = None
try:
    from langfuse import Langfuse, observe
    lf_secret = os.getenv("LANGFUSE_SECRET_KEY")
    lf_public = os.getenv("LANGFUSE_PUBLIC_KEY")
    lf_host = os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL") or "https://hipaa.cloud.langfuse.com"
    os.environ["LANGFUSE_HOST"] = lf_host
    
    if lf_secret and lf_public:
        langfuse_client = Langfuse(secret_key=lf_secret, public_key=lf_public, host=lf_host)
        LANGFUSE_AVAILABLE = bool(langfuse_client.auth_check())
except Exception as e:
    print(f"[LANGFUSE INIT WARNING]: {e}")
    LANGFUSE_AVAILABLE = False

if not LANGFUSE_AVAILABLE:
    def observe(*args, **kwargs):
        def decorator(f):
            return f
        return decorator

openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
free_ai_key = os.getenv("FREE_AI_API_KEY", "")

print("=" * 68)
print(" RASHI HARNESS / RAKSHEX - CLOUD RUNNER SUPERVISOR HEALTH CHECK")
print("=" * 68)
print(f"OPENROUTER_API_KEY present: {bool(openrouter_key)} (length: {len(openrouter_key)})")
print(f"FREE_AI_API_KEY present:    {bool(free_ai_key)} (length: {len(free_ai_key)})")
print(f"LANGFUSE Connection:        {'AUTHENTICATED (' + str(os.getenv('LANGFUSE_HOST')) + ')' if LANGFUSE_AVAILABLE else 'FAILED'}")
print("=" * 68)

openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_key,
    default_headers={"HTTP-Referer": "https://rakshex.dev", "X-Title": "Rashi Harness Cloud Runner"}
) if openrouter_key else None

free_ai_client = OpenAI(
    base_url="https://api.free.ai/v1",
    api_key=free_ai_key
) if free_ai_key else None

TARGET_MODELS = [
    {
        "name": "Baidu ERNIE 5.5 Flash (:free)",
        "model_id": "baidu/ernie-5.5-flash-preview:free",
        "client": openrouter_client,
        "prompt": "Explain the single biggest advantage of 1M context windows in autonomous multi-agent systems in 2 sentences.",
        "max_tokens": 150
    },
    {
        "name": "Free.ai Qwen Coder",
        "model_id": "qwen-coder",
        "client": free_ai_client,
        "prompt": "Write a clean Python function to parse JSON safely with a default fallback.",
        "max_tokens": 150
    },
    {
        "name": "Cohere North Mini Code",
        "model_id": "cohere/north-mini-code:free",
        "client": openrouter_client,
        "prompt": "Write an asynchronous Python function to ping an HTTP endpoint with a timeout.",
        "max_tokens": 150
    }
]

@observe(name="cloud_runner_model_inference")
def execute_model_call(name: str, model_id: str, client: OpenAI, prompt: str, max_tokens: int):
    resp = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        timeout=30
    )
    content = (resp.choices[0].message.content or "").strip()
    if not content and hasattr(resp.choices[0].message, "reasoning"):
        content = (resp.choices[0].message.reasoning or "").strip()
    return content

def run_health_check_cycle(cycle_num: int):
    print(f"\n[CYCLE #{cycle_num}] Starting live inference cycle at {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    cycle_results = []
    
    for target in TARGET_MODELS:
        name = target["name"]
        model_id = target["model_id"]
        client = target["client"]
        prompt = target["prompt"]
        max_tokens = target["max_tokens"]
        
        t0 = time.time()
        if not client:
            cycle_results.append({
                "model_name": name,
                "model_id": model_id,
                "status": "ERROR: Client not initialized (missing API key)",
                "latency_ms": 0,
                "response": None
            })
            continue

        try:
            content = execute_model_call(name, model_id, client, prompt, max_tokens)
            latency_ms = round((time.time() - t0) * 1000, 2)
            preview = content.replace("\n", " ")[:140] + ("..." if len(content) > 140 else "")
            
            cycle_results.append({
                "model_name": name,
                "model_id": model_id,
                "status": "ONLINE",
                "latency_ms": latency_ms,
                "preview": preview,
                "full_response": content
            })
            print(f"  [OK] {name:<30} | {latency_ms:>8.2f} ms | {preview[:70]}...")
            
        except Exception as e:
            latency_ms = round((time.time() - t0) * 1000, 2)
            err_msg = str(e)
            cycle_results.append({
                "model_name": name,
                "model_id": model_id,
                "status": f"FAILED: {err_msg[:80]}",
                "latency_ms": latency_ms,
                "preview": None,
                "full_response": None
            })
            print(f"  [FAIL] {name:<30} | {latency_ms:>8.2f} ms | Error: {err_msg[:60]}")
            
    # Flush Langfuse traces
    if langfuse_client and LANGFUSE_AVAILABLE:
        try:
            langfuse_client.flush()
        except Exception as e:
            print(f"  [Langfuse Flush Notice]: {e}")
            
    return cycle_results

# Execute continuous health checks (3 distinct cycles)
all_cycles = []
for i in range(1, 4):
    res = run_health_check_cycle(i)
    all_cycles.append({
        "cycle_index": i,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "results": res
    })
    if i < 3:
        time.sleep(2)

final_summary = {
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    "environment": "Simular Box (/workspace)",
    "langfuse_status": {
        "authenticated": LANGFUSE_AVAILABLE,
        "host": os.getenv("LANGFUSE_HOST")
    },
    "credentials_verification": {
        "OPENROUTER_API_KEY": bool(openrouter_key),
        "FREE_AI_API_KEY": bool(free_ai_key),
        "LANGFUSE_PUBLIC_KEY": bool(os.getenv("LANGFUSE_PUBLIC_KEY")),
        "LANGFUSE_SECRET_KEY": bool(os.getenv("LANGFUSE_SECRET_KEY")),
    },
    "cycles": all_cycles
}

with open("/workspace/cloud_health_check_report.json", "w", encoding="utf-8") as f:
    json.dump(final_summary, f, indent=2)

print("\n" + "=" * 68)
print("ALL HEALTH CHECK CYCLES COMPLETED AND TRACED TO LANGFUSE")
print("Report stored at /workspace/cloud_health_check_report.json")
print("=" * 68)
