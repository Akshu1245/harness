"""MCP server (gap B11): rashi's tools over stdio JSON-RPC (MCP protocol negotiation),
stdlib only - no mcp package, no dependencies, so any MCP-capable agent CLI (Claude Code,
Codex, DSH) can call the harness directly. Newline-delimited JSON-RPC 2.0 on stdin/stdout.

Exposed tools are the harness's real entry points: fleet (detect agent CLIs), research
(keyless OSS search), drift (spec vs code). ask/build need a provider key and say so clearly
when there is none - same honesty rule as the CLI, errors are tool errors, never crashes."""
import json
import sys

PROTOCOL = "2025-11-25"
PROTOCOLS = ("2024-11-05", "2025-03-26", "2025-06-18", PROTOCOL)
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
     "description": "Build with exact-plan review through client form elicitation; unsupported clients fail closed.",
     "inputSchema": {"type": "object", "properties": {"goal": {"type": "string"}, "dir": {"type": "string"}},
                     "required": ["goal", "dir"]}},
]


def call_tool(name, args, approve=None):
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
        if approve is None:
            return "Build requires exact-plan approval through a client supporting form elicitation.", True
        from .build import one_press
        result=one_press(str(args["goal"]),str(args["dir"]),make_llm(provider,model,key),approve)
        return json.dumps(result,indent=2), result["status"] != "DONE_VERIFIED"
    return f"unknown tool: {name}", True


def handle(msg, approve=None):
    """One JSON-RPC message -> response dict, or None for notifications."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
        return {"jsonrpc": "2.0", "id": None,
                "error": {"code": -32600, "message": "invalid request"}}
    mid = msg.get("id")
    method = msg.get("method")
    if method == "initialize":
        params=msg.get("params") or {}
        requested=params.get("protocolVersion") if isinstance(params,dict) else None
        negotiated=requested if requested in PROTOCOLS else PROTOCOL
        return {"jsonrpc": "2.0", "id": mid,
                "result": {"protocolVersion": negotiated, "capabilities": {"tools": {}},
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
            text, is_error = call_tool(params.get("name", ""), params.get("arguments") or {}, approve=approve)
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
    # A single bounded input reader lets approval expire without a forever-blocking readline.
    # This stdio server owns its input stream for its process lifetime.
    import queue
    import threading
    inbox=queue.Queue(maxsize=64)
    stopped=threading.Event()
    def pump():
        try:
            while not stopped.is_set():
                line=read.readline(262145)
                if not line:
                    break
                while not stopped.is_set():
                    try:inbox.put(line,timeout=0.1);break
                    except queue.Full:pass
        finally:
            while not stopped.is_set():
                try:inbox.put(None,timeout=0.1);break
                except queue.Full:pass
    threading.Thread(target=pump,daemon=True).start()
    input_closed=False
    def receive(timeout=None):
        nonlocal input_closed
        if input_closed:return None
        try:
            item=inbox.get(timeout=timeout)
            if item is None:input_closed=True
            return item
        except queue.Empty:return None
    elicitation=False
    request_id=0

    def ask_client(spec,findings):
        nonlocal request_id
        if not elicitation:
            return False
        from .approval_bridge import approval_text
        request_id+=1
        rid=f"rashi-approval-{request_id}"
        review=approval_text(spec,findings)
        if len(review)>100000:
            return False  # Never truncate approval scope silently.
        message={"jsonrpc":"2.0","id":rid,"method":"elicitation/create",
                 "params":{"message":"Approve this exact Rashi execution plan?\n"+review,
                           "requestedSchema":{"type":"object","properties":{
                               "approve":{"type":"boolean","description":"Approve this exact plan once"}},
                               "required":["approve"]}}}
        write.write(json.dumps(message)+"\n");write.flush()
        import time
        deadline=time.monotonic()+900
        while True:
            incoming=receive(max(0,deadline-time.monotonic()))
            if incoming is None or len(incoming)>262144:return False
            try:
                answer=json.loads(incoming)
            except ValueError:
                return False
            if not isinstance(answer,dict):return False
            if answer.get("id")==rid and "method" not in answer:
                result=answer.get("result") or {}
                return (isinstance(result,dict) and result.get("action")=="accept" and
                        isinstance(result.get("content"),dict) and result["content"].get("approve") is True)
            if answer.get("method")=="notifications/cancelled":return False
            if "method" in answer and answer.get("id") is not None:
                write.write(json.dumps({"jsonrpc":"2.0","id":answer["id"],
                                        "error":{"code":-32000,"message":"build awaiting approval"}})+"\n")
                write.flush()
        return False

    while True:
        line=receive()
        if line is None:break
        if len(line)>262144:
            stopped.set()
            break  # Oversized/unterminated frames are not recoverable on this stream.
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
        if isinstance(msg,dict) and msg.get("method")=="initialize":
            params=msg.get("params") or {}
            caps=params.get("capabilities",{}) if isinstance(params,dict) else {}
            capability=caps.get("elicitation",{}) if isinstance(caps,dict) else {}
            version=params.get("protocolVersion",PROTOCOL) if isinstance(params,dict) else PROTOCOL
            elicitation=(version in ("2025-06-18",PROTOCOL) and isinstance(caps,dict) and
                         "elicitation" in caps and isinstance(capability,dict) and
                         (not capability or "form" in capability))
        resp = handle(msg,approve=ask_client if elicitation else None)
        if resp is not None:
            write.write(json.dumps(resp) + "\n")
            write.flush()

    stopped.set()
