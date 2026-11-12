import json
import re

transcript_path = r"C:\Users\aksha\.gemini\antigravity\brain\f5c270c6-4d58-4062-8293-f128bf3958e6\.system_generated\logs\transcript.jsonl"

targets = [
    "colab", "google colab", "modal", "runpod", "vast", "aws", "gcp", 
    "google cloud", "azure", "paperspace", "replit", "gitpod", "lightning",
    "oracle", "render", "railway", "fly.io", "huggingface", "vps", "server"
]

with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
    for idx, line in enumerate(f):
        try:
            item = json.loads(line)
            c = item.get("content", "")
            if not isinstance(c, str):
                continue
            c_low = c.lower()
            for t in targets:
                if t in c_low and ("user:" in c_low or item.get("source") == "USER_EXPLICIT" or item.get("type") == "USER_INPUT"):
                    print(f"Match [{t}] at step {item.get('step_index', idx)}:")
                    # print user lines
                    for subline in c.split("\n"):
                        if "user:" in subline.lower() or t in subline.lower():
                            print("  ", subline[:140])
                    break
        except Exception as e:
            pass
