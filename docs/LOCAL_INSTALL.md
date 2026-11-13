# Local developer installer

This installer gives you the pinned DeepSeek Harness browser UI with the Rashi tool already
wired. It is not a branded Rashi EXE or APK release. DSH keeps its own branding and license notices.

Requirements: Linux/macOS shell, Python 3.10+, Node 22.18+ and npm, internet for package downloads.
Only Linux has been exercised here. Windows/WSL and macOS installation have not been tested.

From a clone of this repo:

```bash
bash scripts/install_dsh.sh
# Optional: pass a new absolute install path instead.
# bash scripts/install_dsh.sh "$HOME/rashi-test-install"
```

The default directory is `$HOME/.local/share/rashi-harness`. Existing directories are refused,
not overwritten. On a failed install, keep the printed error and choose a fresh path on retry.
To remove an install, stop its running DSH process first and remove only the directory you chose.
The installer does not change global packages or a prior DSH profile. Its Python environment,
DSH npm packages, compiled plugin and separate profile are all inside that directory.

After installation, run the printed `start-rashi.sh` path. This opens a local browser UI.
Use `--no-open` if you want to open the private startup URL yourself. Never share that URL.
A default project folder is created inside the install directory, avoiding the desktop Documents
lookup that failed in a clean headless Linux environment. The launcher sets `RASHI_CMD` and
an isolated `DSH_HOME`; it does not change the user's global DSH config.

The installer does not:
- create a cloud computer, add a cloud plugin, request a cloud token, or start a model call;
- include anyone's model keys, automate payment, or install coding-agent CLIs;
- ship a portable single-file app, branded desktop binary, phone app or production backend.

DSH's own first-use UI asks for a model login or API key. Those are still the user's to configure.
Rashi planning uses the configured free-provider key in the launcher's environment. Coding agents
must separately be installed and authorized. A free planning model does not make an external
coding-agent subscription free. Approval and agent-isolation caveats: [DSH adapter](../dsh/README.md).

Verification on 2026-11-14: clean install on Linux with a new Python environment and 673 pinned-root
npm dependencies succeeded; the compiled installed plugin ran `fleet`; composed config included Rashi;
the real browser UI loaded and created its default workspace. Visual inspection confirmed the UI
and first-use credential prompt. No model call was made. This is install/boot proof, not a goal-completion test.
