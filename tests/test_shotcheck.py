import sys, pathlib, shutil
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from rashi import shotcheck

browser = pytest.mark.skipif(not shotcheck.find_browser(), reason="no headless browser here")


@browser
def test_capture_renders_a_page_to_a_real_png(tmp_path):
    (tmp_path / "ui.html").write_text("<h1 style='font-size:80px'>HELLO</h1>")
    out = shotcheck.capture(f"file://{tmp_path}/ui.html", tmp_path / "shot.png")
    data = pathlib.Path(out).read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) > 1000  # a real render, not an error page


@browser
def test_cli_exits_nonzero_on_a_missing_page(tmp_path):
    assert shotcheck.main(["x", "file:///nonexistent-page-zzz", str(tmp_path / "x.png")]) == 1


def test_no_browser_is_an_honest_failure_not_a_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(shotcheck, "find_browser", lambda: None)
    with pytest.raises(RuntimeError, match="no headless browser"):
        shotcheck.capture("file:///x", tmp_path / "x.png")
