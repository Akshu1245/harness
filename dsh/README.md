# Rashi inside DeepSeek Harness

DSH is the IDE shell; rashi runs inside it as one tool. Nothing from the DSH monorepo is
copied or embedded - this directory is a thin plugin plus its load overlay.

## Setup

1. Install rashi: `pip install .` from the harness repo root (puts `rashi` on PATH).
   Or set `RASHI_CMD` to the full command if it lives elsewhere.
2. Copy `rashi-plugin.ts` INTO your DeepSeek Harness checkout (e.g. `scratch-rashi/src/`).
   Loading it from outside the checkout fails: `@deepseek-ai/dsh-tools` only resolves
   inside the monorepo (verified by boot test 2026-11-13).
3. Edit `cordis.yml`: point `name:` at the copied plugin's absolute path inside the checkout.
4. From the checkout: `pnpm dsh web --patch /path/to/cordis.yml`
   (web needs `pnpm run build` first in a fresh checkout; `dsh headless` does not).
4. In the DSH chat: "Use the rashi tool, mode fleet" (detect agent CLIs),
   "rashi ask: <idea>" (intake questions), build through the Rashi CLI, which can show the generated spec for approval.

## What the tool exposes

| mode | what it runs |
|---|---|
| `fleet` | `rashi fleet` - detect Codex/Claude Code/OpenCode/Aider/Droid/Gemini CLIs + readiness |
| `ask` | `rashi ask "<idea>"` - one batch of clarifying intake questions |
| `build` | Disabled until the adapter can show and approve the generated spec |

`build` needs a free provider key in the environment (KENARI_API_KEY first). Output is
truncated at 16 KB (spill guard); the run's full events are in the workdir's `.rashi/`.

## Honest status

Boot-verified against DSH pinned at 39163dd (0.2.2-rc.3): headless boot composes and loads the
plugin (startup log `include:rashi`); the run itself stops at the LLM credential step without
a provider key. Web boot additionally needs `pnpm run build` in the checkout. Permission
modes (read-only / workspace-write / full-access) are DSH's own presets - rashi adds none.

Build approval is not inferred from a tool call. The adapter refuses builds rather than passing `--yes` silently. End-to-end DSH tool execution remains unverified.
