# Caller-owned acceptance contract

The model-only planning path can invent weak checks, omit requirements or split dependent tasks
into unrelated directories. A passing model-generated check is not proof of the user's whole goal.
The morning live failures demonstrated that distinction.

For a goal with explicit existing acceptance tests, use the new opt-in single-workdir mode:

```json
{
  "checks": [{"id": "semantic", "cmd": "python verify_summary.py"}],
  "protected": ["verify_summary.py"]
}
```

Save that JSON as a local file and run:

```bash
rashi build "the full original goal" /path/to/workdir --acceptance /path/to/contract.json
```

Put the independent acceptance script in the workdir first. The model does not author or rewrite
this contract. Review shows the original goal, exact workdir/checks, protected content digest,
selected coding agent, iteration bound and contract hash. A proposed spec is advisory; it cannot
remove these checks. There is no model task split: one selected agent works in the same directory.
The original goal is carried into the agent prompt, not replaced by the model's shortened task.

The contract is copied before review; later mutation of the caller's object does not alter it.
Missing/symlinked protected fixtures fail before planning. A fixture changed during approval
invalidates execution, and the loop rejects protected-file changes during work. Failed mandatory
checks cannot become DONE_VERIFIED because another model says they passed. Planning errors return
FAILED_PLANNING without invoking an agent. Review denial invokes no agent.

Limits:
- This protects only the checks the caller supplied. Poor checks remain poor evidence.
- Protected files are cooperative hash guards, not race-proof isolation from hostile processes.
- Coding CLIs retain host privileges and may use a separately paid service. The mode grants no
  spending authority and is not a sandbox. No hidden user credentials are supplied.
- This mode is available in the Python library and `build --acceptance`. DSH/MCP cannot yet select
  a caller-owned contract through their tool inputs. Their default independent-task mode is unchanged.
- The CLI selects the first ready agent by sorted name and displays it before approval. Multiple
  agents do not make this mode parallel. A real coding CLI installation is still needed.

Verification: offline tests cover omitted/rewritten model criteria, exact original goal, one-directory
execution, review denial, changed/missing protected fixtures, failed acceptance and agent tampering.
The first real free-model trial of this new mode failed in planning on a provider timeout after a
complete spec and an empty length-limited reviewer response. No coding agent ran. It is not live
goal-completion evidence. Historical zero-lift benchmark results have not been changed.
