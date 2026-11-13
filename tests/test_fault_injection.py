"""Fault-injection sweep: adversarial inputs must never crash the guards, and denial is default."""
import pathlib
import random
import string
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest

from rashi import bounty
from rashi.llm_agent import parse_files, safe_write
from rashi.netguard import url_is_public


def _rand(rng, n):
    return "".join(rng.choice(string.printable) for _ in range(n))


def test_scope_never_crashes_and_denies_garbage():
    rng = random.Random(20261113)
    s = bounty.Scope({"program": "p", "policy_url": "https://x/p", "date": "2026-11-13",
                      "in_scope": ["*.ex.com", "ex.org"], "out_of_scope": []})
    for _ in range(500):
        url = _rand(rng, rng.randint(0, 60))
        try:
            ok, _ = s.allows(url)
        except Exception as ex:
            raise AssertionError(f"allows() crashed on {url!r}: {ex}")
        assert ok is False or url.lower().startswith(("http://", "https://"))


def test_netguard_never_crashes_and_denies_garbage():
    rng = random.Random(7)
    crash_resolver = lambda h, p: (_ for _ in ()).throw(OSError("no dns"))
    for _ in range(500):
        url = _rand(rng, rng.randint(0, 60))
        assert url_is_public(url, resolver=crash_resolver) is False


def test_parse_files_never_crashes():
    rng = random.Random(11)
    for _ in range(300):
        parse_files(_rand(rng, rng.randint(0, 200)))  # must not raise


def test_safe_write_refuses_symlink_escape(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    (work / "link").symlink_to(outside)
    with pytest.raises(ValueError):
        safe_write(work, "link/evil.txt", "x")
    assert not (outside / "evil.txt").exists()


def test_scope_record_with_empty_in_scope_is_rejected():
    # fail closed at load: an empty in_scope reads as a malformed record, not "deny quietly"
    with pytest.raises(ValueError):
        bounty.Scope({"program": "p", "policy_url": "https://x/p", "date": "2026-11-13",
                      "in_scope": []})
