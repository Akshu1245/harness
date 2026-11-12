import sys, os, types, json, re, subprocess, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
os.environ.setdefault("RESPAN_API_KEY","x"); os.environ.setdefault("EXPLABS_API_KEY","x"); os.environ.setdefault("APINEX_API_KEY","x")
import autonomous_loop_engine as e
import rashi_fastpath_engine as f

class R:
    def __init__(s, code=200, body=None, bad=False): s.status_code=code; s._b=body; s._bad=bad
    def json(s):
        if s._bad: raise ValueError("html")
        return s._b

def test_gate_fails_closed_on_error_status():
    assert e.parse_gate(R(500, {"answers": {"is_acceptable": {"noul": 0.99}}})) == 0.0
def test_gate_fails_closed_on_missing_field():
    assert e.parse_gate(R(200, {})) == 0.0
def test_gate_fails_closed_on_non_json():
    assert e.parse_gate(R(200, bad=True)) == 0.0
def test_gate_rejects_out_of_range():
    assert e.parse_gate(R(200, {"answers": {"is_acceptable": {"noul": 7}}})) == 0.0
def test_gate_accepts_valid():
    assert e.parse_gate(R(200, {"answers": {"is_acceptable": {"noul": 0.8}}})) == 0.8
def test_refusal_and_empty_rejected():
    assert not e.is_usable_output("")
    assert not e.is_usable_output("No output generated.")
    assert not e.is_usable_output("I'm sorry, but I can't provide the information you're asking about. If you have other questions, happy to help.")
    assert e.is_usable_output("def add(a, b):\n    return a + b  # a real implementation with enough characters")
def test_fastpath_exact_only():
    assert f.FastPathOptimizer.intercept("healthcheck")["type"] == "quota_mock"
    assert f.FastPathOptimizer.intercept("explain network check in tcp") is None
def test_think_parser_flushes_unclosed():
    p = f.ThinkTagParser(); out = list(p.feed("a<think>unclosed")) + list(p.flush())
    assert ("thinking" in [c.type.value for c in out]) and "".join(c.content for c in out) == "aunclosed"
def test_no_secrets_in_tree():
    pats = re.compile(r"(xpl_[A-Za-z0-9]{10,}|coa_[A-Za-z0-9]{10,}|sk-apx[A-Za-z0-9]{6,}|sk-or-v1-[A-Za-z0-9]{10,}|sk-free-[A-Za-z0-9]{6,}|pk-lf-[A-Za-z0-9-]{10,}|sk-lf-[A-Za-z0-9-]{10,}|04EkULNO\.[A-Za-z0-9]+)")
    root = pathlib.Path(__file__).resolve().parents[1]; hits = []
    for p in root.rglob("*"):
        if p.is_file() and ".git" not in p.parts and p.suffix not in (".lock",) and p.stat().st_size < 2_000_000:
            if pats.search(p.read_text(errors="ignore")): hits.append(str(p.relative_to(root)))
    assert hits == [], hits

from rashi.netguard import url_is_public
def _fake(ip): return lambda h, p: [(2, 1, 6, "", (ip, 0))]
def test_ssrf_blocks_private_and_metadata():
    for ip in ("127.0.0.1", "10.0.0.5", "192.168.1.9", "169.254.169.254", "::1"):
        assert not url_is_public("http://x.example/", resolver=_fake(ip)), ip
def test_ssrf_blocks_bad_scheme():
    assert not url_is_public("file:///etc/passwd") and not url_is_public("ftp://a.com")
def test_ssrf_allows_public():
    assert url_is_public("https://example.com/", resolver=_fake("93.184.216.34"))
