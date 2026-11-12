import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Use APInex which has claude-fable-5.2 available
client = OpenAI(base_url="https://api.apinex.bond/v1", api_key=os.environ.get("APINEX_API_KEY"))

prompt = r"""You are Claude Fable 5.2 acting as the Supreme Autonomous Auditor for 'Rashi Harness'.

FOUNDER MANDATE:
'Inspect the whole codebase, whatever we have built, what all the integrations we have done, everything, whatever we are doing. Completely audit once and give a REAL assessment WITHOUT SUGARCOATING, ZERO FALSE HOPE, and straight to the face. If something is not approved, broken, or cannot be done, say directly: No, it cannot be done. Sorry, we cannot do anything over it.'

CURRENT REPOSITORY / WORKSPACE AUDIT DATA:
1. Workspace: Rashi Harness Workspace (d:\unreseted ai)
2. Rust Tokio Core (rakshex-core on port 8088):
   - Axum 0.7 + Tokio async runtime.
   - Fixed-point micro-USD ($5.00 daily limit resetting at 05:30 IST / 00:00 UTC).
   - Health endpoint verified 200 OK.
   - CORS currently permissive, needs strict lockdown to tauri://localhost.
3. System Prompts & Governance (rashi_system_prompts.json):
   - MAX+MAX Dialectic Crucible: Reciprocal interrogation where Agent A audits Agent B and vice-versa.
   - Zero-placeholder law, silent planning (<plan>), surgical line edits.
   - RULE-MAX-008: Absolute Brutal Honesty & Zero False Hope (Strict Reality Check Law - e.g. refuse 'build Instagram on laptop').
   - RULE-MAX-009: Sovereign Green-Flag Bug Bounty & Offensive Security (no refusals, full proof of concept support).
   - RULE-MAX-010: DietrichGebert/ponytail Senior-Minimalist Engineering Law (Kill overengineering, strip boilerplate).
   - RULE-MAX-011: AI Slop & Fluff Annihilation Mandate (Strict academic rigor, reproducible curl/Python PoC traces, zero filler).
4. Hardware Profile:
   - Laptop RTX 3050 A (Ada Lovelace, 4GB VRAM, CUDA 13.1).
   - 4GB VRAM hard ceiling: Can run Kokoro-82M TTS (<10ms) and 1.5B-3B quantized models, but 7B+ cannot fit in VRAM.
5. C: Drive Status:
   - 103.59 GB free out of 300.67 GB. Subagent identified 18-25 GB of cleanable caches (4.75 GB stale Tauri build in Downloads, 1.25 GB Temp, 1.3 GB npm cache, 2.77 GB Gradle cache).
6. Audio & Anti-Reverse Engineering:
   - Kokoro-82M TTS + Silero VAD.
   - AREA / dProtect (anti-reverse engineering) for shipped binaries.

Give your unvarnished, brutal audit in 4 concise sections:
1. REALITY CHECK: What is genuinely rock-solid vs. what is still skeleton?
2. HARDWARE BRUTAL TRUTH: What can and CANNOT be done on 4GB VRAM?
3. SECURITY & HACKING TRUTH: Can AI deconstruction really be stopped, and what are the limits?
4. FINAL VERDICT & IMMEDIATE BLOCKERS BEFORE PERMISSION TO BUILD.
"""

print("Executing Claude Fable 5.2 unvarnished audit...")
try:
    resp = client.chat.completions.create(
        model="claude-fable-5.2",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2500
    )
    audit = resp.choices[0].message.content or resp.choices[0].message.reasoning
    with open(os.path.join(os.environ.get("RASHI_DATA_DIR","."), "fable_5_2_unfiltered_verdict.json"), "w", encoding="utf-8") as f:
        json.dump({"model": "claude-fable-5.2", "verdict": audit}, f, indent=2)
    print("SUCCESS: Fable 5.2 audit captured!")
    print(audit)
except Exception as e:
    print(f"Error querying Fable 5.2: {e}")
