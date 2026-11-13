"""The harness front door. Usage:
    python -m rashi fleet                 # detect agent CLIs, test readiness, print fixes
    python -m rashi build "build X" DIR   # one press: spec -> approve -> distribute -> verify
    python -m rashi bench                 # run the fixed benchmark tasks on a free model
    python -m rashi warroom DIR [port]    # live event stream UI for a run

`build`/`bench` need one free provider key in the environment (KENARI_API_KEY first,
then the other free gateways); the coding in `build` is done by the CLI agents fleet
found ready. No key, no guesswork: they exit with a clear message.
"""
import argparse
import json
import os
import sys
from pathlib import Path

from . import bench as benchmod
from .build import one_press
from .fleet import detect_all, report
from .llm_agent import FREE_BASE_URLS, FREE_ONLY_MODELS, make_agent
from .loop import run_loop

KEY_ENV = {"kenari": "KENARI_API_KEY", "explabs": "EXPLABS_API_KEY", "apinex": "APINEX_API_KEY",
           "respan": "RESPAN_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
DEFAULT_MODEL = {"kenari": "glm-4-7-flash:free"}  # flash-class: proven in the loop, fits timeouts


def find_llm(env=os.environ):
    """(provider, model, key) for the first configured free gateway, else None."""
    for provider, var in KEY_ENV.items():
        key = env.get(var)
        if not key:
            continue
        check = FREE_ONLY_MODELS.get(provider)
        model = DEFAULT_MODEL.get(provider)
        if model is None or (check and not check(model)):
            continue
        return provider, model, key
    return None


def make_llm(provider, model, key):
    from openai import OpenAI
    client = OpenAI(base_url=FREE_BASE_URLS[provider], api_key=key, timeout=90)

    def llm(system, user):
        r = client.chat.completions.create(model=model, max_tokens=2000, messages=[
            {"role": "system", "content": system}, {"role": "user", "content": user}])
        return r.choices[0].message.content or ""
    return llm


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rashi", description="RaksHex harness front door")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fleet", help="detect and readiness-test installed agent CLIs")
    b = sub.add_parser("build", help="one press: research, plan, distribute, verify")
    b.add_argument("goal")
    b.add_argument("dir")
    b.add_argument("--yes", action="store_true", help="approve the spec without prompting")
    w = sub.add_parser("warroom", help="serve the event-stream UI for a run directory")
    w.add_argument("dir")
    w.add_argument("port", type=int, nargs="?", default=8765)
    bn = sub.add_parser("bench", help="fixed benchmark tasks on a free model; appends results JSONL")
    bn.add_argument("--tasks", default=str(Path(__file__).resolve().parent.parent / "benchmarks" / "tasks.json"))
    bn.add_argument("--out", default="benchmarks/results.jsonl")
    bn.add_argument("--dir", default="/tmp/rashi-bench", help="parent dir for per-task workdirs")
    bn.add_argument("--max-iters", type=int, default=6)
    args = ap.parse_args(argv)

    if args.cmd == "fleet":
        print(report(detect_all()))
        return 0
    if args.cmd == "warroom":
        from .warroom import serve
        print(f"war room on http://127.0.0.1:{args.port}/  (events: {args.dir}/events.jsonl)")
        serve(args.dir, args.port).serve_forever()
        return 0
    # build / bench
    found = find_llm()
    if not found:
        print("No free provider key in the environment. Set one of: "
              + ", ".join(KEY_ENV.values()), file=sys.stderr)
        return 2
    provider, model, key = found
    if args.cmd == "bench":
        agent = make_agent(provider, model, key)
        tasks = benchmod.load_tasks(args.tasks)

        def runner(t):
            wd = Path(args.dir) / t["id"]
            wd.mkdir(parents=True, exist_ok=True)
            for rel, content in t.get("seed", {}).items():  # seeded files exist before the loop
                (wd / rel).write_text(content)
            checks = [{"id": f"{t['id']}-c{i+1}", "cmd": c} for i, c in enumerate(t["checks"])]
            status, log = run_loop({"goal": t["goal"], "workdir": str(wd), "checks": checks,
                                    "protected": t.get("protected", []),
                                    "max_iters": args.max_iters}, agent)
            return {"status": status, "iterations": len(log)}

        summary = benchmod.run_bench(tasks, runner, args.out)
        print(json.dumps({"provider": provider, "model": model,
                          **{k: v for k, v in summary.items() if k != "rows"}}))
        return 0 if summary["done_verified"] == summary["n"] else 1
    llm = make_llm(provider, model, key)

    def approve(spec, findings):
        print(spec)
        if findings:
            print("Findings:", findings)
        return True if args.yes else input("Approve this spec? [y/N] ").strip().lower() == "y"
    result = one_press(args.goal, args.dir, llm, approve)
    print(result)
    return 0 if result["status"] == "DONE_VERIFIED" else 1


if __name__ == "__main__":
    sys.exit(main())
