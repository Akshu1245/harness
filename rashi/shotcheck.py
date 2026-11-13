"""Screenshot-as-check (PAIN_POINTS pass 4, pain 25: agents are blind to visual
correctness - the backend works while the UI hides the breakage).

For UI tasks, "the page renders" must be a check the loop can run, not the agent's
word. capture(url, out) drives headless Chrome when one is installed and returns the
PNG path; it raises an honest error when no browser exists, so a check that needs a
screenshot can never silently pass on a browser-less machine. The CLI form
(`python -m rashi.shotcheck URL out.png`) exits non-zero on any failure, which is
what makes it usable as a check command in a spec.
"""
import shutil
import subprocess
import sys
from pathlib import Path

BROWSERS = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")


def find_browser():
    return next((b for b in BROWSERS if shutil.which(b)), None)


def capture(url, out, width=1280, height=800, virtual_time_ms=6000):
    """Render url headlessly into out (PNG). Returns out; raises RuntimeError otherwise."""
    exe = find_browser()
    if not exe:
        raise RuntimeError("no headless browser installed (google-chrome/chromium): "
                           "a screenshot check cannot run here and must not pass")
    out = Path(out)
    p = subprocess.run([exe, "--headless", "--no-sandbox", "--disable-gpu",
                        f"--window-size={width},{height}", f"--screenshot={out}",
                        f"--virtual-time-budget={virtual_time_ms}", url],
                       capture_output=True, text=True, timeout=60)
    if p.returncode != 0 or not out.exists() or out.stat().st_size < 1000:
        raise RuntimeError(f"screenshot failed: {(p.stderr or p.stdout)[-200:]}")
    return out


def main(argv):
    try:
        capture(argv[1], argv[2])
    except (RuntimeError, subprocess.TimeoutExpired, IndexError) as ex:
        print(ex, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
