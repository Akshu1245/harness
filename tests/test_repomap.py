from rashi.repomap import map_dir


def test_map_lists_files_and_python_symbols(tmp_path):
    (tmp_path / "app.py").write_text("def main():\n    pass\n\nclass App:\n    pass\n")
    (tmp_path / "data.txt").write_text("hi")
    m = map_dir(str(tmp_path))
    assert "app.py" in m and "main, App" in m and "data.txt (2B)" in m


def test_map_skips_bookkeeping_and_is_deterministic(tmp_path):
    (tmp_path / ".rashi").mkdir()
    (tmp_path / ".rashi" / "x").write_text("stash")
    (tmp_path / "a.py").write_text("def f(): pass")
    assert ".rashi" not in map_dir(str(tmp_path))
    assert map_dir(str(tmp_path)) == map_dir(str(tmp_path))


def test_map_caps_and_says_so(tmp_path):
    for i in range(10):
        (tmp_path / f"f{i}.py").write_text("def g(): pass")
    m = map_dir(str(tmp_path), max_files=3)
    assert "7 more files" in m
    assert map_dir(str(tmp_path), max_out=20).endswith("[map truncated]")


def test_map_empty_and_unparsable(tmp_path):
    assert map_dir(str(tmp_path)) == "(empty directory)"
    (tmp_path / "bad.py").write_text("def (:\n")
    assert "bad.py" in map_dir(str(tmp_path))  # listed, symbols skipped
