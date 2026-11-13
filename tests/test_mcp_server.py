import io
import json

from rashi import mcp_server


def roundtrip(msgs):
    inp = io.StringIO("\n".join(json.dumps(m) for m in msgs) + "\n")
    out = io.StringIO()
    mcp_server.serve(read=inp, write=out)
    return [json.loads(l) for l in out.getvalue().splitlines()]


def test_initialize_and_tools_list():
    r = roundtrip([{"jsonrpc": "2.0", "id": 1, "method": "initialize"},
                   {"jsonrpc": "2.0", "method": "notifications/initialized"},
                   {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}])
    assert r[0]["result"]["protocolVersion"] == "2024-11-05"
    assert len(r) == 2  # notifications get no response
    names = [t["name"] for t in r[1]["result"]["tools"]]
    assert names == ["rashi_fleet", "rashi_research", "rashi_drift", "rashi_ask", "rashi_build"]


def test_call_drift_tool(tmp_path):
    (tmp_path / "spec.md").write_text("- `gone.py`")
    r = roundtrip([{"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                    "params": {"name": "rashi_drift",
                               "arguments": {"spec": str(tmp_path / "spec.md"), "dir": str(tmp_path)}}}])
    body = json.loads(r[0]["result"]["content"][0]["text"])
    assert body["missing_paths"] == ["gone.py"] and r[0]["result"]["isError"] is False


def test_tool_error_is_tool_error_not_crash():
    r = roundtrip([{"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                    "params": {"name": "rashi_drift", "arguments": {"spec": "/no/such", "dir": "."}}},
                   {"jsonrpc": "2.0", "id": 4, "method": "bogus/method"}])
    assert r[0]["result"]["isError"] is True and "cannot read spec" in r[0]["result"]["content"][0]["text"]
    assert r[1]["error"]["code"] == -32601


def test_ask_without_key_is_an_honest_error(monkeypatch):
    monkeypatch.delenv("KENARI_API_KEY", raising=False)
    for v in ("EXPLABS_API_KEY", "APINEX_API_KEY", "RESPAN_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(v, raising=False)
    text, is_error = mcp_server.call_tool("rashi_ask", {"idea": "x"})
    assert is_error and "no free provider key" in text
