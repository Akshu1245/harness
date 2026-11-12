import subprocess
import os

files_to_sync = [
    "model_orchestrator.py",
]

for fname in files_to_sync:
    local_path = os.path.join(r"d:\unreseted ai", fname)
    with open(local_path, "r", encoding="utf-8") as f:
        content = f.read()
    remote_path = f"/workspace/{fname}"
    print(f"Streaming {fname} to {remote_path} via stdin...")
    res = subprocess.run(
        ["npx.cmd", "@simular-ai/box", "exec", "--", "bash", "-c", f"cat > {remote_path}"],
        input=content,
        text=True,
        capture_output=True
    )
    if res.returncode == 0:
        print(f"Successfully synced {fname}!")
    else:
        print(f"Failed to sync {fname}:", res.stderr)
