"""The DSH wiring stays honest: plugin + overlay + README present, no DSH code embedded."""
from pathlib import Path

DSH = Path(__file__).resolve().parent.parent / "dsh"


def test_wiring_files_exist():
    assert (DSH / "rashi-plugin.ts").is_file()
    assert (DSH / "cordis.yml").is_file()
    assert (DSH / "README.md").is_file()


def test_plugin_registers_one_tool_shelling_to_cli():
    src = (DSH / "rashi-plugin.ts").read_text()
    assert "defineTool" in src and "ctx.tools.register" in src
    assert "execFile" in src and "shell: true" not in src and "exec(" not in src  # argv array, never a shell
    assert "RASHI_CMD" in src
    # every rashi front-door mode the plugin claims is a real CLI subcommand:
    import re
    main = (Path(__file__).resolve().parent.parent / "rashi" / "__main__.py").read_text()
    for mode in re.findall(r"mode === '(\w+)'", src):
        assert f'"{mode}"' in main or f'add_parser("{mode}"' in main


def test_overlay_has_no_secrets():
    yml = (DSH / "cordis.yml").read_text()
    assert "sk-" not in yml and "kn-" not in yml


def test_dsh_build_cannot_silently_approve_spec():
    src = (DSH / 'rashi-plugin.ts').read_text()
    assert "'--yes'" not in src
    assert 'review handshake' in src
    assert 'timeout: 120_000' in src
