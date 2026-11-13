"""Sandboxed check execution (gap B1). bwrap profile follows the DSH sandbox-local pattern
(read-only /, tmpfs /tmp, writable workdir, unshared PID/net, die-with-parent) reimplemented
in minimal Python - no DSH code. Linux + bubblewrap only.

Off by default. Enable per run with spec["sandbox"]=True or RASHI_SANDBOX=1. If bwrap is
missing, the run stops before checks or agents execute. A requested sandbox never falls
back to unsandboxed execution. Verified live 2026-11-13 (bubblewrap 0.6.1): workdir writable,
/etc read-only, network unreachable."""
import os
import shutil


def available(which=shutil.which):
    return which("bwrap") is not None


def wrap_argv(workdir, net=False):
    """bwrap argv prefix for running a command with only `workdir` writable.
    net=False unshares the network namespace (checks should not phone home)."""
    args = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--unshare-pid",
            "--proc", "/proc", "--die-with-parent", "--tmpfs", "/tmp",
            "--bind", os.path.abspath(workdir), os.path.abspath(workdir)]
    if not net:
        args.append("--unshare-net")
    return args


def requested(spec, env=os.environ):
    return bool(spec.get("sandbox")) or env.get("RASHI_SANDBOX") == "1"
