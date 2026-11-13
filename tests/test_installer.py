from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def test_local_installer_has_no_cloud_or_secret_prompt():
    script=(ROOT/'scripts/install_dsh.sh').read_text()
    assert 'BOX_TOKEN' not in script and 'box-plugin' not in script
    assert 'read -r' not in script and 'curl ' not in script
    assert '--ignore-scripts' in script
    assert 'documentsDirectory' in script  # works without desktop xdg-user-dir
    assert 'RASHI_CMD' in script and 'DSH_HOME' in script
    p=subprocess.run(['bash',str(ROOT/'scripts/install_dsh.sh'),'--help'],capture_output=True,text=True)
    assert p.returncode==0 and 'does not start DSH' in p.stdout


def test_installer_does_not_overwrite_existing_directory(tmp_path):
    if not shutil.which('node') or not shutil.which('npm'):
        import pytest;pytest.skip('Node/npm absent; local installer requires them')
    major,minor=map(int,subprocess.check_output(['node','-p','process.versions.node'],text=True).split('.')[:2])
    if (major,minor)<(22,18):
        import pytest;pytest.skip('Node 22.18+ needed')
    sentinel=tmp_path/'keep';sentinel.write_text('original')
    p=subprocess.run(['bash',str(ROOT/'scripts/install_dsh.sh'),str(tmp_path)],capture_output=True,text=True)
    assert p.returncode==1 and 'already exists' in p.stderr
    assert sentinel.read_text()=='original' and not (tmp_path/'venv').exists()


def test_plugin_builder_emits_real_plain_javascript(tmp_path):
    if not shutil.which('node'):
        import pytest;pytest.skip('Node absent')
    major,minor=map(int,subprocess.check_output(['node','-p','process.versions.node'],text=True).split('.')[:2])
    if (major,minor)<(22,18):
        import pytest;pytest.skip('Node 22.18+ needed')
    p=subprocess.run(['node',str(ROOT/'scripts/build_dsh_plugin.mjs'),str(tmp_path)],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    plugin=tmp_path/'rashi-plugin.mjs'
    assert "'./staged.mjs'" in plugin.read_text() and 'import type ' not in plugin.read_text()
    for file in (plugin,tmp_path/'staged.mjs'):
        assert subprocess.run(['node','--check',str(file)],capture_output=True).returncode==0
