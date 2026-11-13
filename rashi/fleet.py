"""Detect installed agent CLIs and test whether each is ready (his 2026-11-13 voice note:
on install the harness finds which CLI agents exist - Codex, Claude Code, OpenCode, Aider,
Factory and friends - tests them, and says how to fix any that are not ready).

Detection only: probes are read-only (--version) and nothing here signs in, sends prompts,
or touches accounts. `runner` is injectable so tests use fakes; no network, no spend.
"""
import shutil
import subprocess

# cmd -> (display name, version args, fix hint when missing or failing)
KNOWN = {
    "codex": ("OpenAI Codex CLI", ["--version"], "npm i -g @openai/codex && codex login"),
    "claude": ("Claude Code", ["--version"], "install Claude Code, then run `claude` once to sign in"),
    "opencode": ("OpenCode", ["--version"], "npm i -g opencode-ai"),
    "aider": ("Aider", ["--version"], "pip install aider-chat"),
    "droid": ("Factory Droid", ["--version"], "install from factory.ai, then `droid` to sign in"),
    "gemini": ("Gemini CLI", ["--version"], "npm i -g @google/gemini-cli"),
}


def probe(cmd, runner=subprocess.run, timeout=10):
    """One CLI: installed? does `<cmd> --version` exit 0? Never raises."""
    name, version_args, fix = KNOWN.get(cmd, (cmd, ["--version"], f"install {cmd}"))
    exe = shutil.which(cmd)
    if not exe:
        return {"cmd": cmd, "name": name, "installed": False, "ready": False, "fix": fix}
    try:
        p = runner([exe, *version_args], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as ex:
        return {"cmd": cmd, "name": name, "installed": True, "ready": False,
                "fix": f"`{cmd} --version` failed ({type(ex).__name__}); reinstall or check PATH", "path": exe}
    out = (p.stdout or "").strip() or (p.stderr or "").strip()
    version = out.splitlines()[0][:80] if out else ""
    ok = p.returncode == 0
    return {"cmd": cmd, "name": name, "installed": True, "ready": ok, "version": version,
            "path": exe, **({} if ok else {"fix": f"`{cmd} --version` exited {p.returncode}; reinstall or check its auth"})}


def detect_all(runner=subprocess.run):
    return {cmd: probe(cmd, runner=runner) for cmd in KNOWN}


def report(results):
    """Human-readable readiness list, ready CLIs first."""
    lines = []
    for cmd, r in sorted(results.items(), key=lambda kv: not kv[1]["ready"]):
        if r["ready"]:
            lines.append(f"READY  {r['name']} ({cmd}) {r.get('version', '')}".rstrip())
        elif r["installed"]:
            lines.append(f"BROKEN {r['name']} ({cmd}): {r['fix']}")
        else:
            lines.append(f"ABSENT {r['name']} ({cmd}): {r['fix']}")
    return "\n".join(lines)
