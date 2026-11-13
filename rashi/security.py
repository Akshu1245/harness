"""Security-smell scan for agent-written code (PAIN_POINTS pass 4, pain 24:
"perfectly compiling code that happens to leave your database wide open").

Exit-code checks verify behavior, not safety. smells(path) walks a tree and returns
plain findings [(file, line, pattern)] for code shapes that are usually wrong in
agent output: dynamic eval/exec, shell string execution, unsafe deserialization,
and hardcoded credentials. Stdlib only, no network, no judgment calls: every finding
is a literal pattern a human can confirm in one glance. A spec's checks can refuse
DONE when smells() is non-empty.
"""
import re
from pathlib import Path

PATTERNS = [
    ("eval(", re.compile(r"\beval\s*\(")),
    ("exec(", re.compile(r"\bexec\s*\(")),
    ("os.system", re.compile(r"\bos\.system\s*\(")),
    ("shell=True", re.compile(r"\bshell\s*=\s*True")),
    ("pickle load", re.compile(r"\bpickle\.loads?\s*\(")),
    ("yaml unsafe load", re.compile(r"\byaml\.load\s*\((?![^)]*Loader)")),  # load() without a Loader
    ("hardcoded secret", re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{8,}")),
]


def smells(path):
    """[(relative file, line number, pattern name)] for Python source under path."""
    root = Path(path)
    files = [root] if root.is_file() else sorted(root.rglob("*.py"))
    out = []
    for fp in files:
        if "__pycache__" in fp.parts or ".git" in fp.parts:
            continue
        for n, line in enumerate(fp.read_text(errors="replace").splitlines(), 1):
            for name, pat in PATTERNS:
                if pat.search(line):
                    out.append((str(fp.relative_to(root)) if root.is_dir() else fp.name, n, name))
    return out
