# Rashi inside DeepSeek Harness

DSH is the IDE shell; rashi runs inside it as one tool. Nothing from the DSH monorepo is
copied or embedded - this directory is a thin plugin plus its load overlay.

## Setup

1. Install rashi: `pip install .` from the harness repo root (puts `rashi` on PATH).
   Or set `RASHI_CMD` to the full command if it lives elsewhere.
2. Copy `rashi-plugin.ts` AND `staged.ts` INTO your DeepSeek Harness checkout (e.g. `scratch-rashi/src/`).
   Loading it from outside the checkout fails: `@deepseek-ai/dsh-tools` only resolves
   inside the monorepo (verified by boot test 2026-11-13).
3. Edit `cordis.yml`: point `name:` at the copied plugin's absolute path inside the checkout.
4. From the checkout: `pnpm dsh web --patch /path/to/cordis.yml`
   (web needs `pnpm run build` first in a fresh checkout; `dsh headless` does not).
5. In the DSH chat: "Use the rashi tool, mode fleet" (detect agent CLIs),
   "rashi ask: <idea>" (intake questions), build through the native exact-plan approval prompt (goal and absolute workdir required).

## What the tool exposes

| mode | what it runs |
|---|---|
| `fleet` | `rashi fleet` - detect Codex/Claude Code/OpenCode/Aider/Droid/Gemini CLIs + readiness |
| `ask` | `rashi ask "<idea>"` - one batch of clarifying intake questions |
| `build` | `rashi staged-build` with exact plan/check review via the native approval service |

`build` needs a free provider key in the environment (KENARI_API_KEY first). Fleet/ask output is
truncated at 16 KB (spill guard); the run's full events are in the workdir's `.rashi/`.

## Honest status

Boot-verified against DSH pinned at 39163dd (0.2.2-rc.3): headless boot composes and loads the
plugin (startup log `include:rashi`); the run itself stops at the LLM credential step without
a provider key. Web boot additionally needs `pnpm run build` in the checkout. Permission
modes (read-only / workspace-write / full-access) are DSH's own presets - rashi adds none.

Build approval is not inferred from a tool call or an argument such as `approved=true`.
The split tasks, workdir, checks, agent command templates, iteration bound and isolation warning
are frozen before review. The adapter verifies the review digest, asks `ctx.approval.request`,
and continues only on `allowed-once`. Rejection, cancellation, unavailable approval and policy
`never` do not permit execution. It does not silently pass `--yes`.

The staged child has a 15-minute timeout; cancellation kills its owned process group on POSIX.
This is cooperative process cleanup, not containment against an agent that deliberately escapes.
Never run untrusted task code on a machine carrying private credentials. The bridge passes the
host environment to the child. CLI agent permissions and any service usage still require the
owner's separate authority; clicking plan approval does not make a paid endpoint free.

Verified: the actual pinned DSH `defineTool` runtime invokes the plugin and completes an approved
local deterministic build; a rejected build makes no agent edit. The approval service in that test
was a controlled answerer, not a real human UI. Four standalone Node tests cover bound approval,
wrong digest, cancellation of child + grandchild, and cancellation during an unanswered prompt:
`node --experimental-strip-types --test dsh/staged.test.ts` (Node 22+).
A real-model DSH UI-to-build run remains unverified.
