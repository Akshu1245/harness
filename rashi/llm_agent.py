"""Edit step backed by an OpenAI-compatible gateway. Free-tier only by design."""
import json, os, re, tempfile, time
from pathlib import Path
from openai import OpenAI

from .loop import emit

# Providers allowed for automatic use. Paid gateway (Coarena) is deliberately absent.
FREE_BASE_URLS = {
    "apinex": "https://api.apinex.bond/v1",
    "respan": "https://gateway.respan.ai/v1",
    "explabs": "https://api.experientiallabs.ai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "kenari": "https://kenari.id/v1",
}
# Providers that also sell paid models: only these model ids are allowed (free ones).
FREE_ONLY_MODELS = {"kenari": lambda m: m.endswith(":free") or m == "kenari-free"}
class SpendGate:
    """Daily call cap at the provider call path, persisted in one JSON file. Every allowed model is
    free by construction (FREE_BASE_URLS + FREE_ONLY_MODELS), so this guards free-tier rate limits
    and refuses to run up calls if a provider silently turns a model paid. Same semantics as the
    rakshex-core Rust breaker (per-day counter, reset at 00:00 UTC, deny over cap); the Rust
    prototype stays unconnected - this is the Python gate on the actual call path.
    shortcut: counts calls, not tokens/rupees (free APIs return no reliable cost field);
    upgrade: parse provider cost headers when one exists."""
    def __init__(self, path, per_day=50):
        self.path, self.per_day = Path(path), per_day

    def check(self, provider):
        day = time.strftime("%Y-%m-%d", time.gmtime())
        try:
            data = json.loads(self.path.read_text())
        except (OSError, ValueError):
            data = {}
        if data.get("day") != day:
            data = {"day": day, "calls": {}}
        n = data.get("calls", {}).get(provider, 0)
        if n >= self.per_day:
            raise RuntimeError(f"daily free-call cap reached for {provider} ({self.per_day}/day)")
        data.setdefault("calls", {})[provider] = n + 1
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent))  # atomic write: a crash mid-write
        with os.fdopen(fd, "w") as f:                         # must never corrupt the counter
            f.write(json.dumps(data))
        os.replace(tmp, self.path)


FILE_RE = re.compile(r"FILE:\s*(\S+)\s*\n```[a-zA-Z0-9]*\n(.*?)```", re.S)
SYSTEM = ("You are a careful engineer. Reply ONLY with files to write, each as:\n"
          "FILE: relative/path.py\n```python\n<full file content>\n```\n"
          "No explanations. Never edit test files. If checks failed, fix the cause.")


def parse_files(text):
    return [(m.group(1), m.group(2)) for m in FILE_RE.finditer(text or "")]


def safe_write(workdir, rel, content, protected=()):
    root = Path(workdir).resolve()
    target = (root / rel).resolve()
    if root not in target.parents and target != root:
        raise ValueError(f"path escapes workdir: {rel}")
    for p in protected:
        pp = (root / p).resolve()
        if target == pp or pp in target.parents:
            raise ValueError(f"protected path: {rel}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)


def make_agent(provider, model, api_key, protected=(), max_tokens=1500, client=None, calls_per_day=50):
    if provider not in FREE_BASE_URLS:
        raise ValueError(f"provider not allowed: {provider}")
    check = FREE_ONLY_MODELS.get(provider)
    if check and not check(model):
        raise ValueError(f"paid model refused on {provider}: {model}")
    client = client or OpenAI(base_url=FREE_BASE_URLS[provider], api_key=api_key, timeout=90)

    def agent(goal, feedback, workdir):
        SpendGate(Path(workdir) / ".spend.json", calls_per_day).check(provider)
        ctx = ""
        for fp in sorted(Path(workdir).glob("*.py")):
            if len(ctx) >= 24000:  # total cap: truncation mid-file produces broken edits
                break
            try:
                ctx += f"\n--- {fp.name} ---\n{fp.read_text(errors='replace')[:3000]}"
            except OSError:
                continue
        prompt = f"Goal: {goal}\nCurrent files:{ctx}\n"
        if feedback:
            prompt += f"\nFailing checks output:\n{feedback}\n"
        r = client.chat.completions.create(model=model, max_tokens=max_tokens,
            messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}])
        u = getattr(r, "usage", None)  # cost is data: every call's tokens land in events.jsonl
        if u is not None:
            emit(workdir, "llm_call", provider=provider, model=model,
                 prompt_tokens=getattr(u, "prompt_tokens", None),
                 completion_tokens=getattr(u, "completion_tokens", None))
        text = r.choices[0].message.content or ""
        files = parse_files(text)
        if not files:
            raise ValueError("model returned no parsable FILE blocks")
        for rel, content in files:
            safe_write(workdir, rel, content, protected)
    return agent
