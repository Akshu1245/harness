import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from rashi.security import smells


def test_clean_code_has_no_smells(tmp_path):
    (tmp_path / "ok.py").write_text("import subprocess\nsubprocess.run(['ls'])\n")
    assert smells(tmp_path) == []


def test_dangerous_shapes_are_found_with_locations(tmp_path):
    (tmp_path / "bad.py").write_text(
        "import os, pickle\n"
        "os.system(user_input)\n"
        "eval('2+2')\n"
        "subprocess.run(cmd, shell=True)\n"
        "pickle.loads(blob)\n"
        "api_key = 'sk-live-123456789'\n")
    found = smells(tmp_path)
    pats = {p for _, _, p in found}
    assert pats == {"os.system", "eval(", "shell=True", "pickle load", "hardcoded secret"}
    assert all(f == "bad.py" and isinstance(n, int) for f, n, _ in found)


def test_yaml_safe_load_is_not_flagged(tmp_path):
    (tmp_path / "y.py").write_text("yaml.load(s, Loader=yaml.SafeLoader)\n")
    assert smells(tmp_path) == []
