import subprocess
import base64

with open(r"d:\unreseted ai\.env", "r", encoding="utf-8") as f:
    env_content = f.read()

b64 = base64.b64encode(env_content.encode("utf-8")).decode("utf-8")
bash_cmd = f"echo '{b64}' | base64 -d > /workspace/.env"

print("Syncing .env to cloud box...")
proc = subprocess.run(["npx.cmd", "@simular-ai/box", "exec", "--", "bash", "-c", bash_cmd], capture_output=True, text=True)
print("Return code:", proc.returncode)
if proc.stdout:
    print("Stdout:", proc.stdout)
if proc.stderr:
    print("Stderr:", proc.stderr)

# Verify
proc_verify = subprocess.run(["npx.cmd", "@simular-ai/box", "exec", "--", "cat", "/workspace/.env"], capture_output=True, text=True)
print("=== VERIFIED /workspace/.env INSIDE CLOUD BOX ===")
print(proc_verify.stdout)
