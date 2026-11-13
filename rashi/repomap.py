"""Repo map (gap B3): a deterministic, compact map of a workdir - file tree plus Python symbols -
injected as project context so the elephant drafts specs against what actually exists.
Stdlib only, no LLM, no network. Output is capped; a huge repo yields a smaller honest map."""
import ast
from pathlib import Path

SKIP = ("__pycache__", ".git", ".rashi", ".spill", "node_modules", ".venv", "venv")


def py_symbols(path, max_names=12):
    """Top-level def/class names of one Python file; [] when unparsable."""
    try:
        tree = ast.parse(path.read_bytes())
    except (SyntaxError, ValueError, OSError):
        return []
    return [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))][:max_names]


def map_dir(workdir, max_files=200, max_out=4000):
    """One deterministic text block: sorted relative paths (+ sizes), with top-level symbols
    for Python files. Capped at max_files entries and max_out chars, and says when it truncated."""
    wd = Path(workdir)
    files = [fp for fp in sorted(wd.rglob("*"))
             if fp.is_file() and not any(part in SKIP for part in fp.parts)]
    truncated = len(files) > max_files
    lines = []
    for fp in files[:max_files]:
        rel = str(fp.relative_to(wd))
        line = f"{rel} ({fp.stat().st_size}B)"
        if rel.endswith(".py"):
            names = py_symbols(fp)
            if names:
                line += ": " + ", ".join(names)
        lines.append(line)
    if truncated:
        lines.append(f"[... {len(files) - max_files} more files]")
    out = "\n".join(lines)
    if len(out) > max_out:
        out = out[:max_out] + "\n[map truncated]"
    return out or "(empty directory)"
