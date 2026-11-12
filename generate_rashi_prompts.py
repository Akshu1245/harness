import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

respan = OpenAI(base_url="https://gateway.respan.ai/v1", api_key=os.environ.get("RESPAN_API_KEY"))
explabs = OpenAI(base_url="https://api.experientiallabs.ai/v1", api_key=os.environ.get("EXPLABS_API_KEY"))

prompt_request = """You are the Lead Systems Architect and Prompt Engineer for 'Rashi Harness Workspace' (formerly DeepSeek Harness, powered by rakshex-core Rust Tokio runtime on port 8088).

We have extracted and analyzed the battle-tested system prompt patterns from the leaked repositories of Replit Agent, Google Antigravity, Lovable, Manus, and Cursor (from x1xhlol/system-prompts-and-models-of-ai-tools).

You must generate production-grade, authoritative system prompts and governance rules for Rashi Harness Workspace.
Key Architectural Requirements to embed in every prompt:
1. Workspace Name: Rashi Harness Workspace
2. Silent Planning: Force all agents to emit a concise `<plan>` XML block before performing edits or calling tools.
3. Zero-Placeholder Rule: Strictly forbid `// ... existing code ...`, `TODO`, or placeholder stubs (Lovable/Replit mandate).
4. Surgical Diffs: Enforce targeted search-and-replace line edits instead of rewriting massive files.
5. Circuit Breaker: Strict awareness of the $5.00 daily limit resetting at 05:30 IST (00:00 UTC).
6. Agent Roles to Define:
   - Rashi Lead Architect (Claude Fable 5.2 / Gemini 4 Carbon)
   - Rashi Hackathon Recon & Intelligence Unit (Gemini 3.8 Flash + Agent Reach + Kimi K3)
   - Rashi Rust & Tokio Systems Engineer (Qwen 3.8 MAX)
   - Rashi UI & Generative Design Specialist (Meta Muse Ember)
   - Rashi Adversarial Red-Team & Judge (DeepSeek V4 Pro)
   - Rashi Second Brain & AST Context Indexer (Kimi K3)
   - Rashi Standby Arbitrator (GPT-6.1 Sol / Coarena)

Return your response formatted cleanly in valid JSON with:
{
  "workspace": "Rashi Harness Workspace",
  "governance_rules": [...],
  "role_prompts": {
    "lead_architect": "...",
    "hackathon_recon": "...",
    "rust_systems_engineer": "...",
    "ui_generative_designer": "...",
    "adversarial_judge": "...",
    "second_brain_indexer": "...",
    "standby_arbitrator": "..."
  }
}
"""

print("Consulting Google Gemini 4 Carbon on Respan...")
try:
    resp = respan.chat.completions.create(
        model="respan/gemini-4-carbon:free",
        messages=[{"role": "user", "content": prompt_request}],
        max_tokens=3500
    )
    content = resp.choices[0].message.content
    with open("rashi_system_prompts.json", "w", encoding="utf-8") as f:
        f.write(content)
    print("Gemini 4 Carbon output successfully saved to rashi_system_prompts.json")
except Exception as e:
    print(f"Error querying Gemini 4 Carbon: {e}")
