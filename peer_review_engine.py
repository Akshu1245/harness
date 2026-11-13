"""
Peer-Review and Cross-Model Verification Engine.
Runs a 2-stage cycle:
Stage 1 (Builder): Primary specialized model creates the artifact/code/design.
Stage 2 (Peer Reviewer): A rival frontier model inspects the output for flaws, edge cases, and improvements.
Stage 3 (Jev Gate): Jev 1.13 evaluates if the work meets the acceptance threshold.
"""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI
import requests

load_dotenv()

respan = OpenAI(base_url="https://gateway.respan.ai/v1", api_key=os.environ.get("RESPAN_API_KEY")) if os.environ.get("RESPAN_API_KEY") else None
explabs = OpenAI(base_url="https://api.experientiallabs.ai/v1", api_key=os.environ.get("EXPLABS_API_KEY")) if os.environ.get("EXPLABS_API_KEY") else None
apinex = OpenAI(base_url="https://api.apinex.bond/v1", api_key=os.environ.get("APINEX_API_KEY")) if os.environ.get("APINEX_API_KEY") else None

# Define Peer-Review Pairs (Builder <-> Reviewer)
PEER_REVIEW_PAIRS = {
    # If Gemini Carbon designs, Claude Fable 5.2 audits
    "reasoning_architecture": {
        "builder": {"name": "Gemini 4 Carbon", "client": respan, "model": "respan/gemini-4-carbon:free"},
        "reviewer": {"name": "Claude Fable 5.2", "client": explabs, "model": "claude-fable-5.2:free"}
    },
    # If Qwen 3.8 builds backend code, DeepSeek V4 Pro audits
    "backend_code": {
        "builder": {"name": "Qwen 3.8 MAX", "client": apinex, "model": "free/qwen-3.8-max"},
        "reviewer": {"name": "DeepSeek V4 Pro", "client": apinex, "model": "free/deepseek-v4-pro-0813"}
    },
    # If Muse Ember designs UI, GPT-6 Luna audits UX/clarity
    "ui_ux": {
        "builder": {"name": "Meta Muse Ember", "client": respan, "model": "meta/muse-ember:free"},
        "reviewer": {"name": "GPT-6 Luna", "client": apinex, "model": "free/gpt-6-luna"}
    }
}

def execute_cross_evaluation(domain: str, task_prompt: str) -> dict:
    pair = PEER_REVIEW_PAIRS.get(domain)
    if not pair:
        raise ValueError(f"Unknown domain {domain}. Options: {list(PEER_REVIEW_PAIRS.keys())}")

    builder = pair["builder"]
    reviewer = pair["reviewer"]

    print(f"\n[Stage 1: BUILD] Delegating task to {builder['name']}...")
    build_resp = builder["client"].chat.completions.create(
        model=builder["model"],
        messages=[
            {"role": "system", "content": "You are the primary builder. Produce a production-grade, technically rigorous solution."},
            {"role": "user", "content": task_prompt}
        ],
        max_tokens=600,
    )
    initial_output = build_resp.choices[0].message.content.strip()

    print(f"[Stage 2: PEER REVIEW] Passing output to {reviewer['name']} for cross-examination...")
    review_prompt = f"""You are the Lead Quality & Security Inspector.
Analyze the following work created by {builder['name']}:

=== BUILDER OUTPUT ===
{initial_output}
=== END BUILDER OUTPUT ===

Original Task: {task_prompt}

Perform a rigorous cross-model inspection:
1. Identify any hidden edge cases, bugs, or architectural weaknesses.
2. Verify correctness and completeness.
3. State whether this is APPROVED or NEEDS REVISION, with concrete improvements."""

    review_resp = reviewer["client"].chat.completions.create(
        model=reviewer["model"],
        messages=[
            {"role": "system", "content": "You are a critical, adversarial auditor. Do not rubber-stamp. Find all flaws."},
            {"role": "user", "content": review_prompt}
        ],
        max_tokens=600,
    )
    review_output = review_resp.choices[0].message.content.strip()

    print(f"[Stage 3: JEV ACCEPTANCE GATE] Calculating probabilistic approval...")
    url = "https://api.apinex.bond/v1/decisions"
    headers = {"Authorization": f"Bearer {os.environ.get('APINEX_API_KEY')}", "Content-Type": "application/json"}
    payload = {
        "model": "free/jev-1.13",
        "state": f"Builder Output:\n{initial_output[:300]}\n\nPeer Review Output:\n{review_output[:300]}",
        "questions": {
            "is_approved": {
                "type": "noul",
                "instructions": "Based on the peer review critique, is this deliverable safe and approved for production?"
            },
            "quality_grade": {
                "type": "score",
                "instructions": "Grade the overall quality of this deliverable.",
                "criteria": ["unacceptable", "needs_work", "acceptable", "exceptional"]
            }
        }
    }
    jev_res = requests.post(url, headers=headers, json=payload, timeout=20)
    decision = jev_res.json().get("answers", {})

    return {
        "builder": builder["name"],
        "reviewer": reviewer["name"],
        "initial_output": initial_output,
        "peer_review": review_output,
        "jev_decision": decision
    }

if __name__ == "__main__":
    print("Testing Cross-Model Evaluation Loop (Gemini 4 Carbon <-> Claude Fable 5.2)...")
    res = execute_cross_evaluation(
        domain="reasoning_architecture",
        task_prompt="Propose a zero-downtime database migration strategy for high-volume message queues."
    )
    print("\n--- COMPLETE PEER-REVIEW CYCLE RESULT ---")
    print(f"Builder ({res['builder']}):\n{res['initial_output'][:200]}...\n")
    print(f"Reviewer ({res['reviewer']}):\n{res['peer_review'][:200]}...\n")
    print(f"Jev Gate Decision: {json.dumps(res['jev_decision'], indent=2)}")
