import json

transcript_path = r"C:\Users\aksha\.gemini\antigravity\brain\f5c270c6-4d58-4062-8293-f128bf3958e6\.system_generated\logs\transcript_full.jsonl"

with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
    for idx, line in enumerate(f):
        try:
            item = json.loads(line)
            c = item.get("content", "")
            if not isinstance(c, str):
                continue
            c_low = c.lower()
            if "cloud" in c_low and ("user:" in c_low or item.get("source") == "USER_EXPLICIT" or item.get("type") == "USER_INPUT"):
                for line_part in c.split("\n"):
                    if "user:" in line_part.lower() and "cloud" in line_part.lower():
                        print(f"Step {item.get('step_index', idx)}: {line_part}")
        except Exception:
            pass
