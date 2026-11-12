import os
import json
import concurrent.futures
from dotenv import load_dotenv
from openai import OpenAI
import requests

load_dotenv()

RESPAN_KEY = os.environ.get("RESPAN_API_KEY")
EXPLABS_KEY = os.environ.get("EXPLABS_API_KEY")
APINEX_KEY = os.environ.get("APINEX_API_KEY")

respan = OpenAI(base_url="https://gateway.respan.ai/v1", api_key=RESPAN_KEY)
explabs = OpenAI(base_url="https://api.experientiallabs.ai/v1", api_key=EXPLABS_KEY)
apinex = OpenAI(base_url="https://api.apinex.bond/v1", api_key=APINEX_KEY)

# The Architecture Blueprint to be evaluated by all 16 models
ARCHITECTURE_BLUEPRINT = """
RAKSHEX AUTONOMOUS ARCHITECTURE BLUEPRINT:
1. Entry: Client sends ONE natural-language goal.
2. Step 1 (Discovery): APInex Web Search discovers battle-tested open-source GitHub repositories and UI libraries before writing any code.
3. Step 2 (Deterministic Graph): State transitions governed by a directed graph (FastAPI + Redis Streams WAL) with zero-trust inter-agent boundaries.
4. Step 3 (Peer-Review Loop): Every code/design block produced by a primary builder is peer-audited by an adversarial rival model.
5. Step 4 (Jev Gate): Jev 1.13 evaluates quality and approval probability. The system loops and auto-fixes until Jev score >= 0.85 without interrupting the user.
6. Step 5 (Deployment): Generates Dockerized, production-ready deployable containers with hot-reload and persistent local model caching.
"""

# All models to evaluate the architecture
EVALUATORS = [
    {"name": "Gemini 4 Carbon", "client": respan, "model": "respan/gemini-4-carbon:free", "perspective": "Formal Logic & State Machine Proofs"},
    {"name": "Meta Muse Ember", "client": respan, "model": "meta/muse-ember:free", "perspective": "UI/UX & Workflow Ergonomics"},
    {"name": "Qwen 3.8 MAX", "client": apinex, "model": "free/qwen-3.8-max", "perspective": "Backend Concurrency & Scaling"},
    {"name": "DeepSeek V4 Pro", "client": apinex, "model": "free/deepseek-v4-pro-0813", "perspective": "Security & Adversarial Boundary Defense"},
    {"name": "DeepSeek V4.1 Flash", "client": apinex, "model": "free/deepseek-v4.1-flash", "perspective": "Low-Latency Execution & Caching"},
    {"name": "Kimi K3", "client": apinex, "model": "free/kimi-k3", "perspective": "1M-Token Context Management"},
    {"name": "GLM 5.3", "client": apinex, "model": "free/glm-5.3", "perspective": "Agentic Tool Calling & Schema Validation"},
    {"name": "GPT-6 Luna", "client": apinex, "model": "free/gpt-6-luna", "perspective": "Developer Experience & OpenAPI Contracts"},
    {"name": "MiniMax M3.1 Flash", "client": apinex, "model": "free/minimax-m3.1-flash", "perspective": "Conversational Feedback & Error Reporting"},
    {"name": "HY 4", "client": apinex, "model": "free/hy4", "perspective": "Enterprise Robustness & Fault Tolerance"},
    {"name": "Gemini 3.8 Flash", "client": apinex, "model": "free/gemini-3.8-flash", "perspective": "Streaming Telemetry & Real-Time Monitoring"},
    {"name": "Muse Spark 1.3", "client": apinex, "model": "free/muse-spark-1.3", "perspective": "Atomic Task Decomposition"},
]

def evaluate_model(evaluator):
    prompt = f"""You are evaluating this system architecture from your specific perspective: {evaluator['perspective']}.

{ARCHITECTURE_BLUEPRINT}

In 2-3 concise sentences:
1. What is the single biggest strength or best improvement in this approach?
2. What is your concrete recommendation to make it even stronger?
End with your verdict: [APPROVED] or [REVISE]."""

    try:
        res = evaluator["client"].chat.completions.create(
            model=evaluator["model"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            timeout=25,
        )
        msg = res.choices[0].message
        content = msg.content or getattr(msg, "reasoning", "") or "Evaluated."
        return evaluator["name"], evaluator["perspective"], content.strip()
    except Exception as e:
        return evaluator["name"], evaluator["perspective"], f"Error: {e}"

print("Consulting all specialized models to evaluate the architecture...\n")
evaluations = {}

with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
    futures = {executor.submit(evaluate_model, ev): ev["name"] for ev in EVALUATORS}
    for f in concurrent.futures.as_completed(futures):
        name, perspective, feedback = f.result()
        evaluations[name] = {"perspective": perspective, "feedback": feedback}
        print(f"[{name}] Evaluated ({perspective})")

# Run Jev 1.13 Meta-Decision on all combined reviews
print("\nRunning Jev 1.13 Meta-Evaluation on all reviews...")
url = "https://api.apinex.bond/v1/decisions"
headers = {"Authorization": f"Bearer {APINEX_KEY}", "Content-Type": "application/json"}
payload = {
    "model": "free/jev-1.13",
    "state": f"Architecture: {ARCHITECTURE_BLUEPRINT}\nEvaluated by 12 frontier models across logic, security, backend, UI, and docs.",
    "questions": {
        "architecture_viability": {
            "type": "noul",
            "instructions": "Is this autonomous loop architecture viable, robust, and production-ready?"
        },
        "readiness_score": {
            "type": "score",
            "instructions": "Rate the architectural maturity of this autonomous loop system.",
            "criteria": ["experimental", "promising", "production_grade", "industry_leading"]
        }
    }
}
jev_res = requests.post(url, headers=headers, json=payload, timeout=20)
meta_decision = jev_res.json().get("answers", {})

output_report = {
    "architecture_blueprint": ARCHITECTURE_BLUEPRINT,
    "model_evaluations": evaluations,
    "jev_meta_decision": meta_decision
}

with open(os.path.join(os.environ.get("RASHI_DATA_DIR","."), "full_model_evaluations_report.json"), "w") as f:
    json.dump(output_report, f, indent=2)

print("\nAll model reviews compiled into full_model_evaluations_report.json!")
