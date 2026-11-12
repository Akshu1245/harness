import os
import json

with open(os.path.join(os.environ.get("RASHI_DATA_DIR","."), "rashi_system_prompts.json"), "r", encoding="utf-8") as f:
    prompts = json.load(f)

# Update RULE-MAX-011 with Peter Yang's no-ai-slop guidelines
for rule in prompts["governance_rules"]:
    if rule["id"] == "RULE-MAX-011":
        rule["rule"] = (
            "AI Slop Annihilation Mandate (Incorporating petergyang/no-ai-slop): "
            "Absolute prohibition of AI filler, robotic prose, and intellectual throat-clearing. "
            "1. BANNED VOCABULARY: 'delve', 'testament', 'tapestry', 'foster', 'crucial', 'transformative', 'beacon', 'unwavering', 'plethora', 'in conclusion'. "
            "2. BANNED PATTERNS: Never open with 'In today's fast-paced digital world', never repeat the prompt back to the user, and never use filler summaries. "
            "3. RIGOROUS EXECUTION: Deliver dense, high-signal, punchy communication. In research papers, use formal LaTeX math and reproducible benchmarks. In bug reports, provide concrete curl/Python PoC traces with zero speculative hallucinations."
        )

# Add RULE-MAX-012 for the 50 Component Libraries & Accelerator Index
prompts["governance_rules"].append({
    "id": "RULE-MAX-012",
    "name": "Standard Accelerator & 50-Component Design Ecosystem",
    "rule": "Whenever an agent is tasked with building or designing a frontend UI or full-stack application, it MUST cross-reference d:\\unreseted ai\\rashi_accelerators.json. It must leverage the 50 free curated component libraries (Aceternity UI, 21st.dev, Magic UI, Shadcn/ui, DaisyUI, Tremor, React Bits, Flowbite, etc.) and the 9 specialized repos (RuView for telemetry, OfficeCLI for docs, ian-xiaohei for illustrations, free-claude-code for gateway fallbacks) rather than generating unstyled or generic HTML/CSS."
})

# Enhance Hackathon Recon prompt with the Accelerator Index
prompts["role_prompts"]["hackathon_recon"] += """\n\n### ACCELERATOR INDEX ACCESS
You are the primary indexer of `d:\\unreseted ai\\rashi_accelerators.json`.
When the user requests an app:
1. Search the 50 Component Libraries (Aceternity, Magic UI, Tremor, 21st.dev, Daisy UI, etc.) to pick the exact matching UI kit.
2. Select the optimal architecture from the Nov 11 toolkits (e.g., RuView for dashboards, OfficeCLI for doc engines, free-claude-code for model fallbacks).
3. Deliver the exact import commands and copy-paste component snippets directly to the UI Designer."""

# Enhance UI Designer prompt with the Component Ecosystem
prompts["role_prompts"]["ui_generative_designer"] += """\n\n### 50 COMPONENT LIBRARIES ECOSYSTEM
You have instant design access to the 50 verified UI libraries in `d:\\unreseted ai\\rashi_accelerators.json`:
- For Dashboards/Analytics: Tremor, Tail Grids, Flowbite.
- For High-Craft Visuals/3D: Aceternity UI, Magic UI, React Bits, Eldora UI.
- For Rock-Solid Primitives: Shadcn/ui, Headless UI, Jolly UI, DaisyUI.
Never build dull, unstyled components. Always craft production-grade, aesthetically stunning interfaces using these ecosystems."""

with open(os.path.join(os.environ.get("RASHI_DATA_DIR","."), "rashi_system_prompts.json"), "w", encoding="utf-8") as f:
    json.dump(prompts, f, indent=2)

print("Successfully updated rashi_system_prompts.json with petergyang/no-ai-slop rules and 50 component libraries!")
