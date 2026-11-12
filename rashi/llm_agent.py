"""Edit step backed by an OpenAI-compatible gateway. Free-tier only by design."""
import re
from pathlib import Path
from openai import OpenAI

# Providers allowed for automatic use. Paid gateway (Coarena) is deliberately absent.
FREE_BASE_URLS = {
    "apinex": "https://api.apinex.bond/v1",
    "respan": "https://gateway.respan.ai/v1",
    "explabs": "https://api.experientiallabs.ai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}
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


def make_agent(provider, model, api_key, protected=(), max_tokens=1500, client=None):
    if provider not in FREE_BASE_URLS:
        raise ValueError(f"provider not allowed: {provider}")
    client = client or OpenAI(base_url=FREE_BASE_URLS[provider], api_key=api_key, timeout=90)

    def agent(goal, feedback, workdir):
        ctx = ""
        for fp in sorted(Path(workdir).glob("*.py")):
            ctx += f"\n--- {fp.name} ---\n{fp.read_text()[:3000]}"
        prompt = f"Goal: {goal}\nCurrent files:{ctx}\n"
        if feedback:
            prompt += f"\nFailing checks output:\n{feedback}\n"
        r = client.chat.completions.create(model=model, max_tokens=max_tokens,
            messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}])
        text = r.choices[0].message.content or ""
        files = parse_files(text)
        if not files:
            raise ValueError("model returned no parsable FILE blocks")
        for rel, content in files:
            safe_write(workdir, rel, content, protected)
    return agent
