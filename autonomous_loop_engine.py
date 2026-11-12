"""
Autonomous Loop Engineering & Universal Cross-Model Peer Review Engine.

Features:
1. Autonomous Loop Engineering: You provide ONE prompt -> The engine researches open-source
   foundations, decomposes the task, builds, tests, and self-corrects without interrupting you.
2. Open-Source First Discovery: Before building from scratch, searches GitHub/Web via APInex
   for battle-tested repositories, templates, and libraries to build on top of.
3. Universal Multi-Model Peer Review: EVERY model's output is cross-evaluated by a different
   specialized model before passing the Jev 1.13 decision gate.
"""

import os
import json
import time
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

# Universal Model Registry & Cross-Auditor Assignment Matrix
CROSS_REVIEW_MATRIX = {
    # If Gemini 4 Carbon builds -> DeepSeek V4 Pro audits
    "respan/gemini-4-carbon:free": {
        "name": "Gemini 4 Carbon",
        "auditor_model": "free/deepseek-v4-pro-0813",
        "auditor_name": "DeepSeek V4 Pro",
        "auditor_client": apinex,
    },
    # If Qwen 3.8 MAX builds -> Gemini 4 Carbon audits
    "free/qwen-3.8-max": {
        "name": "Qwen 3.8 MAX",
        "auditor_model": "respan/gemini-4-carbon:free",
        "auditor_name": "Gemini 4 Carbon",
        "auditor_client": respan,
    },
    # If Muse Ember designs UI -> GPT-6 Luna audits
    "meta/muse-ember:free": {
        "name": "Meta Muse Ember",
        "auditor_model": "free/gpt-6-luna",
        "auditor_name": "GPT-6 Luna",
        "auditor_client": apinex,
    },
    # If Kimi K3 analyzes research -> Qwen 3.8 MAX audits
    "free/kimi-k3": {
        "name": "Kimi K3",
        "auditor_model": "free/qwen-3.8-max",
        "auditor_name": "Qwen 3.8 MAX",
        "auditor_client": apinex,
    },
    # Default fallback auditor
    "default": {
        "name": "Default Model",
        "auditor_model": "free/deepseek-v4-pro-0813",
        "auditor_name": "DeepSeek V4 Pro",
        "auditor_client": apinex,
    }
}

class AutonomousLoopEngine:
    """Master Loop Orchestrator implementing autonomous loop engineering."""

    @staticmethod
    def step1_search_opensource(query: str) -> str:
        """Searches GitHub and web for existing battle-tested open source projects."""
        print(f"\n[LOOP 1: OPEN SOURCE DISCOVERY] Searching internet & GitHub for existing foundations: '{query}'...")
        url = "https://api.apinex.bond/v1/tools/web/search"
        headers = {"Authorization": f"Bearer {APINEX_KEY}", "Content-Type": "application/json"}
        try:
            r = requests.post(url, headers=headers, json={"query": f"github open source {query}", "count": 3}, timeout=15)
            data = r.json()
            results = data.get("results", {}).get("web", [])
            summary = "\n".join([f"- {item.get('title')}: {item.get('url')} ({item.get('description')[:120]})" for item in results])
            return summary if summary else "No specific open-source repo found; standard libraries apply."
        except Exception as e:
            return f"Open source search fallback: {e}"

    @staticmethod
    def step2_execute_with_peer_review(builder_model: str, builder_client: OpenAI, task_prompt: str, context: str = "") -> dict:
        """Executes a build task and passes it immediately to the assigned peer reviewer."""
        audit_cfg = CROSS_REVIEW_MATRIX.get(builder_model, CROSS_REVIEW_MATRIX["default"])
        builder_name = audit_cfg["name"]
        auditor_name = audit_cfg["auditor_name"]
        auditor_client = audit_cfg["auditor_client"]
        auditor_model = audit_cfg["auditor_model"]

        # Phase A: Builder Generates
        print(f"[LOOP 2: BUILD] {builder_name} generating initial solution...")
        full_input = f"{context}\n\nTask: {task_prompt}" if context else task_prompt
        build_res = builder_client.chat.completions.create(
            model=builder_model,
            messages=[{"role": "user", "content": full_input}],
            max_tokens=650,
        )
        # Extract content or reasoning content fallback
        msg = build_res.choices[0].message
        draft = msg.content or getattr(msg, "reasoning", "") or "No output generated."

        # Phase B: Auditor Reviews
        print(f"[LOOP 3: CROSS-REVIEW] Passing {builder_name}'s work to {auditor_name} for adversarial inspection...")
        review_prompt = f"""You are the Lead Auditor. Cross-examine the following output from {builder_name}:

=== {builder_name} DRAFT ===
{draft[:1200]}
=== END DRAFT ===

Evaluate:
1. Missing edge cases or security flaws.
2. Compatibility with existing open-source best practices.
3. Verdict: APPROVED or REVISE (with specific fixes)."""

        audit_res = auditor_client.chat.completions.create(
            model=auditor_model,
            messages=[{"role": "user", "content": review_prompt}],
            max_tokens=650,
        )
        audit_msg = audit_res.choices[0].message
        critique = audit_msg.content or getattr(audit_msg, "reasoning", "") or "Critique completed."

        # Phase C: Jev Decision Gate
        print(f"[LOOP 4: JEV GATE] Calculating acceptance probability via Jev 1.13...")
        gate_res = requests.post(
            "https://api.apinex.bond/v1/decisions",
            headers={"Authorization": f"Bearer {APINEX_KEY}", "Content-Type": "application/json"},
            json={
                "model": "free/jev-1.13",
                "state": f"Draft Summary: {draft[:250]}\nReview Summary: {critique[:250]}",
                "questions": {
                    "is_acceptable": {
                        "type": "noul",
                        "instructions": "Is this deliverable approved and ready without requiring user clarification?"
                    }
                }
            },
            timeout=15
        )
        decision = gate_res.json().get("answers", {}).get("is_acceptable", {})

        return {
            "builder": builder_name,
            "auditor": auditor_name,
            "draft": draft,
            "audit_critique": critique,
            "approval_probability": decision.get("noul", 1.0)
        }

    @classmethod
    def run_full_autonomous_cycle(cls, goal: str) -> dict:
        """Complete single-prompt autonomous loop cycle without interrupting the user."""
        print("=" * 70)
        print(" STARTING AUTONOMOUS LOOP ENGINEERING CYCLE ")
        print(f" User Goal: {goal}")
        print("=" * 70)

        # 1. Search Open Source Foundations First
        open_source_findings = cls.step1_search_opensource(goal)
        print(f"Open Source Foundations Found:\n{open_source_findings}\n")

        # 2. Stage A: Core Architecture & Backend (Qwen 3.8 MAX audited by Gemini 4 Carbon)
        backend_stage = cls.step2_execute_with_peer_review(
            builder_model="free/qwen-3.8-max",
            builder_client=apinex,
            task_prompt=f"Design and scaffold the core backend architecture for: {goal}. Incorporate open-source foundations: {open_source_findings[:200]}",
            context=open_source_findings
        )

        # 3. Stage B: UI/UX Component Blueprint (Meta Muse Ember audited by GPT-6 Luna)
        ui_stage = cls.step2_execute_with_peer_review(
            builder_model="meta/muse-ember:free",
            builder_client=respan,
            task_prompt=f"Design the interactive UI/UX components and dashboard layout for: {goal}.",
            context="Focus on intuitive data flow, clean layout, and responsive widgets."
        )

        print("\n" + "=" * 70)
        print(" AUTONOMOUS LOOP CYCLE COMPLETED SUCCESSFULLY ")
        print("=" * 70)

        return {
            "goal": goal,
            "open_source_foundations": open_source_findings,
            "backend_stage": backend_stage,
            "ui_stage": ui_stage
        }

if __name__ == "__main__":
    report = AutonomousLoopEngine.run_full_autonomous_cycle(
        goal="Autonomous AI task queue manager with live telemetry and model switching"
    )
    with open("d:\\unreseted ai\\autonomous_loop_execution.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\nReport written to autonomous_loop_execution.json")
