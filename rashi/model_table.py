"""Generate a markdown table of Kenari's free chat models from a live /v1/models response.

Probe-generated, never hand-maintained: rerun with a fresh /v1/models JSON when the table matters.
shortcut: Kenari only, it is the one provider whose /models exposes pricing.free and endpoints;
upgrade: fold in other providers when their /models exposes the same fields.
"""
import json


def free_chat_models(models_json):
    return [
        {
            "id": m["id"],
            "tools": bool(m.get("tool_call")),
            "reasoning": bool(m.get("reasoning")),
            "context": m.get("context_length", 0),
        }
        for m in models_json.get("data", [])
        if m.get("pricing", {}).get("free") and "chat" in m.get("endpoints", [])
    ]


def to_markdown(models, source_desc):
    lines = [f"<!-- probe-generated from {source_desc}; do not hand-edit -->",
             "| model | tool calling | reasoning | context |", "|---|---|---|---|"]
    for m in sorted(models, key=lambda m: -m["context"]):
        lines.append(f"| {m['id']} | {'yes' if m['tools'] else 'no'} | "
                     f"{'yes' if m['reasoning'] else 'no'} | {m['context']:,} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import sys
    data = json.loads(open(sys.argv[1]).read())
    print(to_markdown(free_chat_models(data), sys.argv[1]), end="")
