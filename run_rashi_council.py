import os, json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

respan = OpenAI(base_url="https://gateway.respan.ai/v1", api_key=os.environ.get("RESPAN_API_KEY"))
explabs = OpenAI(base_url="https://api.experientiallabs.ai/v1", api_key=os.environ.get("EXPLABS_API_KEY"))
apinex = OpenAI(base_url="https://api.apinex.bond/v1", api_key=os.environ.get("APINEX_API_KEY"))

query = """You are participating in the supreme Council of Models for 'Rashi Harness Workspace'.
The founder's core directive:
"A user who has never coded and knows nothing about AI models should be able to type or speak: 'I want to build an app like X'. Rashi Harness must autonomously:
1. Deconstruct the idea into high-leverage architectural steps.
2. Scout the live web/GitHub for existing open-source accelerators, templates, and free APIs (using Agent Reach & Kimi K3).
3. Coordinate the 16-model mesh to generate the complete frontend (Muse Ember), backend (Rust Tokio/Qwen 3.8 MAX), and verify it with zero placeholders (DeepSeek V4 Pro).
4. Package everything into a 1-click standalone portable Windows application (Rashi Harness.exe) with zero external dependencies."

Give your concrete audit, ideas, and actionable verdict:
1. What is the single biggest architectural enhancement to make this zero-friction for non-technical users?
2. What are the fatal pitfalls to guard against in autonomous code synthesis?
3. What is your final verdict and sign-off on the Rashi Harness execution plan?
"""

council = {}

print("1. Polling Gemini 4 Carbon (Respan)...")
try:
    r = respan.chat.completions.create(
        model="respan/gemini-4-carbon:free",
        messages=[{"role": "user", "content": query}],
        max_tokens=1500
    )
    council["Gemini 4 Carbon"] = r.choices[0].message.content
except Exception as e:
    council["Gemini 4 Carbon"] = f"Error: {e}"

print("2. Polling Claude Fable 5.2 (Experiential Labs)...")
try:
    r = explabs.chat.completions.create(
        model="claude-fable-5.2:free",
        messages=[{"role": "user", "content": query}],
        max_tokens=1500
    )
    council["Claude Fable 5.2"] = r.choices[0].message.content or r.choices[0].message.reasoning
except Exception as e:
    council["Claude Fable 5.2"] = f"Error: {e}"

print("3. Polling Qwen 3.8 MAX (APInex)...")
try:
    r = apinex.chat.completions.create(
        model="free/qwen-3.8-max",
        messages=[{"role": "user", "content": query}],
        max_tokens=1000
    )
    council["Qwen 3.8 MAX"] = r.choices[0].message.content
except Exception as e:
    council["Qwen 3.8 MAX"] = f"Error: {e}"

print("4. Polling DeepSeek V4 Pro (APInex)...")
try:
    r = apinex.chat.completions.create(
        model="free/deepseek-v4-pro-0813",
        messages=[{"role": "user", "content": query}],
        max_tokens=1000
    )
    council["DeepSeek V4 Pro"] = r.choices[0].message.content
except Exception as e:
    council["DeepSeek V4 Pro"] = f"Error: {e}"

with open("rashi_harness_council_verdict.json", "w", encoding="utf-8") as f:
    json.dump(council, f, indent=2)

print("Council complete! Results saved to rashi_harness_council_verdict.json")
