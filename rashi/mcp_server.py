"""MCP server (gap B11): rashi's tools over stdio JSON-RPC (MCP protocol 2024-11-05),
stdlib only - no mcp package, no dependencies, so any MCP-capable agent CLI (Claude Code,
Codex, DSH) can call the harness directly. Newline-delimited JSON-RPC 2.0 on stdin/stdout.

Exposed tools are the harness's real entry points: fleet (detect agent CLIs), research
(keyless OSS search), drift (spec vs code). ask/build need a provider key and say so clearly
when there is none - same honesty rule as the CLI, errors are tool errors, never crashes."""
import json
import sys

PROTOCOL = "2024-11-05"
SERVER = {"name": "rashi", "version": "0.1.0"}

TOOLS = [
    {"name": "rashi_fleet",
     "description": "Detect installed agent CLIs (Codex, Claude Code, OpenCode, Aider, Droid, Gemini) and test readiness.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "rashi_research",
     "description": "Find the most-starred existing open-source projects for a topic (keyless GitHub search).",
     "inputSchema": {"type": "object", "properties": {"topic": {"type": "string"}}, "required": ["topic"]}},
    {"name": "rashi_drift",
     "description": "Drift report: paths a spec/design doc names that are missing from the code tree.",
     "inputSchema": {"type": "object", "properties": {"spec": {"type": "string"}, "dir": {"type": "string"}},
                     "required": ["spec", "dir"]}},
    {"name": "rashi_ask",
     "description": "Intake: one batch of clarifying questions for an idea (needs a free provider key).",
     "inputSchema": {"type": "object", "properties": {"idea": {"type": "string"}}, "required": ["idea"]}},
    {"name": "rashi_build",
     "description": "One press: brainstorm, spec, approve (--yes), distribute to ready CLI agents, verify by exit codes (needs a free provider key).",
     "inputSchema": {"type": "object", "properties": {"goal": {"type": "string"}, "dir": {"type": "string"}},
                     "required": ["goal", "dir"]}},
]


def call_tool(name, args):
    """Returns (text, is_error)."""
    if name == "rashi_fleet":
        from .fleet import detect_all, report
        return report(detect_all()), False
    if name == "rashi_research":
        from .research import as_context, oss_alternatives
        return as_context(oss_alternatives(str(args.get("topic", "")))), False
    if name == "rashi_drift":
        from pathlib import Path
        from .egm import drift_report
        try:
            spec_text = Path(str(args["spec"])).read_text()
        except OSError as ex:
            return f"cannot read spec: {ex}", True
        return json.dumps(drift_report(spec_text, str(args["dir"])), indent=2), False
    if name in ("rashi_ask", "rashi_build"):
        from .__main__ import find_llm, make_llm
        found = find_llm()
        if not found:
            return ("no free provider key configured (set KENARI_API_KEY or another free gateway key); "
                    "refusing to guess"), True
        provider, model, key = found
        if name == "rashi_ask":
            from .intake import questions
            return questions(make_llm(provider, model, key), str(args.get("idea", ""))), False
        from .build import one_press
        result = one_press(str(args["goal"]), str(args["dir"]), make_llm(provider, model, key),
                           lambda spec, findings: True)
        return json.dumps(result, indent=2, default=str), result["status"] != "DONE_VERIFIED"
    return f"unknown tool: {name}", True


def handle(msg):
    """One JSON-RPC message -> response dict, or None for notifications."""
    mid = msg.get("id")
    method = msg.get("method")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": mid,
                "result": {"protocolVersion": PROTOCOL, "capabilities": {"tools": {}},
                           "serverInfo": SERVER}}
    if method in ("notifications/initialized", "notifications/cancelled"):
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params") or {}
        try:
            text, is_error = call_tool(params.get("name", ""), params.get("arguments") or {})
        except Exception as ex:  # a tool failure is a tool error, never a server crash
            text, is_error = f"{type(ex).__name__}: {str(ex)[:200]}", True
        return {"jsonrpc": "2.0", "id": mid,
                "result": {"content": [{"type": "text", "text": text}], "isError": is_error}}
    if mid is not None:
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": -32601, "message": f"method not found: {method}"}}
    return None


def serve(read=None, write=None):
    """Line-delimited JSON-RPC on stdin/stdout until EOF."""
    read = read or sys.stdin
    write = write or sys.stdout
    for line in read:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            write.write(json.dumps({"jsonrpc": "2.0", "id": None,
                                    "error": {"code": -32700, "message": "parse error"}}) + "\n")
            write.flush()
            continue
        resp = handle(msg)
        if resp is not None:
            write.write(json.dumps(resp) + "\n")
            write.flush()
