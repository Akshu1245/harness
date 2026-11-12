"""
Adversarial Model Debate & Empirical Proof Engine.

Rules:
1. Builder creates the solution.
2. Adversary attacks: MUST find concrete flaws, failure modes, race conditions, or unverified claims.
3. Builder Defense: Builder cannot manipulate or handwave; it MUST provide empirical evidence,
   code proofs, math, or citations to defend its work.
4. Jev 1.13 Judge: Unbiased referee evaluates the debate transcript and awards victory based
   solely on proof and correctness.
"""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI
import requests

load_dotenv()

respan = OpenAI(base_url="https://gateway.respan.ai/v1", api_key=os.environ.get("RESPAN_API_KEY"))
explabs = OpenAI(base_url="https://api.experientiallabs.ai/v1", api_key=os.environ.get("EXPLABS_API_KEY"))
apinex = OpenAI(base_url="https://api.apinex.bond/v1", api_key=os.environ.get("APINEX_API_KEY"))

def run_adversarial_trial(topic: str, builder_cfg: dict, adversary_cfg: dict) -> dict:
    print(f"\n{'='*70}")
    print(f" ADVERSARIAL TRIAL: {builder_cfg['name']} (Builder) vs {adversary_cfg['name']} (Challenger)")
    print(f" Topic: {topic}")
    print(f"{'='*70}\n")

    # Round 1: Builder proposes architecture/solution
    print(f"[ROUND 1] {builder_cfg['name']} builds initial proposal...")
    p1 = f"Propose a production-grade, highly resilient design for: {topic}. Be specific, include architecture details and proof of correctness."
    r1 = builder_cfg["client"].chat.completions.create(
        model=builder_cfg["model"],
        messages=[{"role": "user", "content": p1}],
        max_tokens=500
    )
    msg1 = r1.choices[0].message
    proposal = msg1.content or getattr(msg1, "reasoning", "") or "No proposal generated."

    # Round 2: Adversary attacks
    print(f"[ROUND 2] {adversary_cfg['name']} launches adversarial attack on {builder_cfg['name']}'s proposal...")
    p2 = f"""You are the strict Adversarial Auditor. Attack the following proposal by {builder_cfg['name']}:

=== PROPOSAL ===
{proposal}
=== END PROPOSAL ===

Rules for your attack:
1. Spot any edge-case failure modes, scaling bottlenecks, security vulnerabilities, or hand-waving assumptions.
2. Demand concrete empirical proof, mathematical bounds, or code verification.
3. Challenge the builder directly: explain exactly why this is not yet production-ready."""
    
    r2 = adversary_cfg["client"].chat.completions.create(
        model=adversary_cfg["model"],
        messages=[{"role": "user", "content": p2}],
        max_tokens=500
    )
    msg2 = r2.choices[0].message
    critique = msg2.content or getattr(msg2, "reasoning", "") or "No critique generated."

    # Round 3: Builder defends with proof
    print(f"[ROUND 3] {builder_cfg['name']} must defend its work with proof against the critique...")
    p3 = f"""The Adversary ({adversary_cfg['name']}) attacked your proposal with the following critique:

=== ADVERSARY CRITIQUE ===
{critique}
=== END CRITIQUE ===

Defend your design. You CANNOT use vague words or manipulate the auditor.
You MUST provide:
1. Direct technical refutation of their critique.
2. Concrete proof (code safeguards, mathematical guarantees, or failover mechanisms).
3. The revised production guarantee why this must be approved."""

    r3 = builder_cfg["client"].chat.completions.create(
        model=builder_cfg["model"],
        messages=[
            {"role": "assistant", "content": proposal},
            {"role": "user", "content": p3}
        ],
        max_tokens=600
    )
    msg3 = r3.choices[0].message
    defense = msg3.content or getattr(msg3, "reasoning", "") or "No defense generated."

    # Round 4: Jev 1.13 Independent Mathematical Judgment
    print(f"[ROUND 4] Jev 1.13 evaluating the debate and empirical proofs...")
    url = "https://api.apinex.bond/v1/decisions"
    headers = {"Authorization": f"Bearer {os.environ.get('APINEX_API_KEY')}", "Content-Type": "application/json"}
    payload = {
        "model": "free/jev-1.13",
        "state": f"Builder ({builder_cfg['name']}) Proposal:\n{proposal[:250]}\n\nAdversary Attack:\n{critique[:250]}\n\nBuilder Defense:\n{defense[:250]}",
        "questions": {
            "defense_proven": {
                "type": "noul",
                "instructions": "Did the builder empirically prove its architecture against the adversary attack without handwaving?"
            },
            "debate_winner": {
                "type": "choice",
                "instructions": "Who won the technical debate based strictly on factual evidence?",
                "criteria": {
                    "builder_verified": "Builder successfully proved correctness with robust safeguards",
                    "adversary_valid": "Adversary successfully exposed critical unaddressed flaws"
                }
            }
        }
    }
    j_res = requests.post(url, headers=headers, json=payload, timeout=20)
    verdict = j_res.json().get("answers", {})

    return {
        "topic": topic,
        "builder": builder_cfg["name"],
        "adversary": adversary_cfg["name"],
        "proposal": proposal,
        "critique": critique,
        "defense": defense,
        "verdict": verdict
    }

if __name__ == "__main__":
    trial_result = run_adversarial_trial(
        topic="High-throughput distributed task queue with zero message loss during worker crashes",
        builder_cfg={"name": "Qwen 3.8 MAX", "client": apinex, "model": "free/qwen-3.8-max"},
        adversary_cfg={"name": "DeepSeek V4 Pro", "client": apinex, "model": "free/deepseek-v4-pro-0813"}
    )
    with open(os.path.join(os.environ.get("RASHI_DATA_DIR","."), "adversarial_trial_report.json"), "w") as f:
        json.dump(trial_result, f, indent=2)
    print("\nAdversarial Trial Completed and Logged to adversarial_trial_report.json!")
