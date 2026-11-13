"""The harness front door. Usage:
    python -m rashi fleet                 # detect agent CLIs, test readiness, print fixes
    python -m rashi ask "idea"            # intake: all clarifying questions in one batch
    python -m rashi build "build X" DIR   # one press: spec -> approve -> distribute -> verify
                                          #   --answers FILE folds intake answers into the goal
    python -m rashi bench                 # run the fixed benchmark tasks on a free model
    python -m rashi warroom DIR [port]    # live event stream UI for a run
    python -m rashi drift SPEC DIR        # EGM drift report: spec paths missing from the code
    python -m rashi council "question"    # debate + vote across your configured free gateways
    python -m rashi research "topic"      # find existing OSS for a topic (keyless, zero spend)
    python -m rashi mcp                   # serve rashi tools over MCP stdio (for agent CLIs)

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
from .intake import questions, with_answers
from .llm_agent import FREE_BASE_URLS, FREE_ONLY_MODELS, make_agent
from .loop import run_loop

KEY_ENV = {"kenari": "KENARI_API_KEY", "explabs": "EXPLABS_API_KEY", "apinex": "APINEX_API_KEY",
           "respan": "RESPAN_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
DEFAULT_MODEL = {"kenari": "glm-4-7-flash:free"}  # flash-class: proven in the loop, fits timeouts
# Council member per gateway. Non-Kenari defaults come from his 2026-11-12 council scripts and are
# UNVERIFIED until a live council run; override with RASHI_COUNCIL_MODEL_<PROVIDER>.
COUNCIL_MODELS = {"kenari": "glm-4-7-flash:free", "respan": "respan/gemini-4-carbon:free",
                  "explabs": "claude-fable-5.2:free", "apinex": "free/qwen-3.8-max"}


def council_members(env=os.environ, maker=None):
    """{member_name: llm} for every gateway with both a key and a free model. OpenRouter joins
    only when its model is named explicitly (its free set changes)."""
    maker = maker or make_llm
    members = {}
    for provider, var in KEY_ENV.items():
        key = env.get(var)
        model = env.get(f"RASHI_COUNCIL_MODEL_{provider.upper()}") or COUNCIL_MODELS.get(provider)
        if key and model:
            check = FREE_ONLY_MODELS.get(provider)
            # Council never opts into paid models, even if another command permits them.
            # Legacy gateway overrides must still use an explicitly free model marker.
            free = check(model) if check else (model.startswith("free/") or model.endswith(":free"))
            if not free:
                raise ValueError(f"council refuses non-free model for {provider}: {model}")
            members[f"{provider}/{model}"] = maker(provider, model, key)
    return members


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
    a = sub.add_parser("ask", help="intake: all clarifying questions for an idea, in one batch")
    a.add_argument("idea")
    b = sub.add_parser("build", help="one press: research, plan, distribute, verify")
    b.add_argument("goal")
    b.add_argument("dir")
    b.add_argument("--yes", action="store_true", help="approve the spec without prompting")
    b.add_argument("--answers", help="file with answers to the `rashi ask` intake batch")
    b.add_argument("--model", help="override the model; a paid model needs RASHI_ALLOW_PAID=1")
    b.add_argument("--research", action="store_true",
                   help="search for existing OSS first and feed findings into the brief")
    w = sub.add_parser("warroom", help="serve the event-stream UI for a run directory")
    w.add_argument("dir")
    w.add_argument("port", type=int, nargs="?", default=8765)
    paired = sub.add_parser("paired-bench", help="same-model bare vs visible-feedback repair; custom subset, extra calls disclosed")
    paired.add_argument("--data", required=True)
    paired.add_argument("--limit", type=int, default=3)
    paired.add_argument("--max-attempts", type=int, default=2)
    paired.add_argument("--control", action="store_true")
    paired.add_argument("--out", default="paired-result.json")
    pb = sub.add_parser("public-bench", help="isolated HumanEval subset evaluation; not an official leaderboard score")
    pb.add_argument("--data", required=True, help="local upstream HumanEval.jsonl.gz")
    pb.add_argument("--samples", help="local JSONL with task_id/completion, one per task")
    pb.add_argument("--limit", type=int, default=3)
    pb.add_argument("--out", default="public-bench-result.json")
    mode = pb.add_mutually_exclusive_group()
    mode.add_argument("--generate", action="store_true", help="generate with configured free default model")
    mode.add_argument("--self-test", action="store_true", help="reference/broken calibration, NOT a model score")
    sub.add_parser("mcp", help="serve rashi tools over MCP stdio (JSON-RPC, no dependencies)")
    r = sub.add_parser("research", help="find existing open-source projects for a topic (no key)")
    r.add_argument("topic")
    d = sub.add_parser("drift", help="compare a spec/design doc with the code tree; exit 1 on drift")
    d.add_argument("spec")
    d.add_argument("dir")
    c = sub.add_parser("council", help="debate + vote across configured free gateways; advisory")
    c.add_argument("question")
    c.add_argument("--out", default="council_result.json")
    bn = sub.add_parser("bench", help="fixed benchmark tasks on a free model; appends results JSONL")
    bn.add_argument("--tasks", default=str(Path(__file__).resolve().parent / "data" / "tasks.json"))
    bn.add_argument("--out", default="benchmarks/results.jsonl")
    bn.add_argument("--dir", default="/tmp/rashi-bench", help="parent dir for per-task workdirs")
    bn.add_argument("--max-iters", type=int, default=6)
    args = ap.parse_args(argv)

    if args.cmd == "paired-bench":
        from .paired_bench import main as paired_main
        return paired_main(args)
    if args.cmd == "public-bench":
        from .public_bench import main as public_main
        return public_main(args)
    if args.cmd == "fleet":
        print(report(detect_all()))
        return 0
    if args.cmd == "mcp":
        from .mcp_server import serve
        serve()
        return 0
    if args.cmd == "research":
        from .research import as_context, oss_alternatives
        print(as_context(oss_alternatives(args.topic)))
        return 0
    if args.cmd == "council":
        from .council import debate
        members = council_members()
        if len(members) < 2:
            print("council needs at least two configured gateways "
                  "(set KENARI_API_KEY / RESPAN_API_KEY / EXPLABS_API_KEY / APINEX_API_KEY ...)")
            return 2
        result = debate(members, args.question)
        Path(args.out).write_text(json.dumps(result, indent=2))
        print(f"members: {', '.join(members)}")
        print(f"winner: {result['winner']}" if result["winner"] else "no majority (see votes in the file)")
        if result["errors"]:
            print(f"errors/abstentions: {result['errors']}")
        print(f"full record: {args.out} (advisory - never auto-executed)")
        return 0
    if args.cmd == "drift":
        from .egm import drift_report
        r = drift_report(Path(args.spec).read_text(), args.dir)
        print(json.dumps(r, indent=2))
        return 1 if r["drifted"] else 0
    if args.cmd == "warroom":
        from .warroom import serve
        print(f"war room on http://127.0.0.1:{args.port}/  (events: {args.dir}/events.jsonl)")
        serve(args.dir, args.port).serve_forever()
        return 0
    # ask / build / bench
    found = find_llm()
    if not found:
        print("No free provider key in the environment. Set one of: "
              + ", ".join(KEY_ENV.values()), file=sys.stderr)
        return 2
    provider, model, key = found
    allow_paid = os.environ.get("RASHI_ALLOW_PAID") == "1"
    chosen = getattr(args, "model", None)
    if chosen and chosen != model:
        check = FREE_ONLY_MODELS.get(provider)
        if check and not check(chosen) and not allow_paid:
            print(f"paid model refused on {provider}: {chosen} "
                  "(set RASHI_ALLOW_PAID=1 to spend your own key's money)", file=sys.stderr)
            return 2
        model = chosen
    if args.cmd == "ask":
        print(questions(make_llm(provider, model, key), args.idea))
        print("\nAnswer in one message and build with: rashi build \"" + args.idea + "\" DIR "
              "--answers answers.txt\nOr paste the questions into your own AI and bring its answers back.")
        return 0
    if args.cmd == "bench":
        agent = make_agent(provider, model, key)
        tasks = benchmod.load_tasks(args.tasks)

        def runner(t):
            wd = Path(args.dir) / t["id"]
            wd.mkdir(parents=True, exist_ok=True)
            for rel, content in t.get("seed", {}).items():  # seeded files exist before the loop
                (wd / rel).write_text(content)
            # Multi-step SWE shape: steps run in order in ONE workdir, each graded by its
            # own checks, so step k builds on whatever step k-1 left behind.
            steps = t.get("steps") or [{"goal": t["goal"], "checks": t["checks"]}]
            total_iters, status = 0, "DONE_VERIFIED"
            for i, s in enumerate(steps):
                checks = [{"id": f"{t['id']}-s{i+1}-c{j+1}", "cmd": c} for j, c in enumerate(s["checks"])]
                status, log = run_loop({"goal": s["goal"], "workdir": str(wd), "checks": checks,
                                        "protected": t.get("protected", []),
                                        "max_iters": args.max_iters}, agent)
                total_iters += len(log)
                if status != "DONE_VERIFIED":
                    break  # a failed step ends the chain; later steps inherit broken code
            # PAIN_POINTS pain 24: exit codes verify behavior, not safety. A task marked
            # security_scan refuses DONE when the agent's output carries dangerous shapes.
            if status == "DONE_VERIFIED" and t.get("security_scan"):
                from .security import smells
                found = smells(wd)
                if found:
                    status = "FAILED_SECURITY_SMELLS"
            return {"status": status, "iterations": total_iters}

        summary = benchmod.run_bench(tasks, runner, args.out)
        print(json.dumps({"provider": provider, "model": model,
                          **{k: v for k, v in summary.items() if k != "rows"}}))
        return 0 if summary["done_verified"] == summary["n"] else 1
    llm = make_llm(provider, model, key)

    goal = args.goal
    if args.answers:
        goal = with_answers(goal, Path(args.answers).read_text())

    def approve(spec, findings):
        print(spec)
        if findings:
            print("Findings:", findings)
        return True if args.yes else input("Approve this spec? [y/N] ").strip().lower() == "y"
    research_fn = None
    if getattr(args, "research", False):  # R28: OSS alternatives feed the brief; failures stated
        from .research import as_context, oss_alternatives
        research_fn = lambda topic: as_context(oss_alternatives(topic))
    result = one_press(goal, args.dir, llm, approve, research=research_fn)
    print(result)
    return 0 if result["status"] == "DONE_VERIFIED" else 1


if __name__ == "__main__":
    sys.exit(main())
