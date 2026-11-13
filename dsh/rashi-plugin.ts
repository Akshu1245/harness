// Rashi harness as a DeepSeek Harness tool (his direction: DSH is the IDE shell, rashi runs
// inside it). Light wiring only: one tool that shells out to the `rashi` CLI - no DSH code
// copied, no DSH monorepo embedded. Load with:
//   pnpm dsh web --patch /path/to/harness/dsh/cordis.yml
// Requires `rashi` on PATH (pip install . from the harness repo) or RASHI_CMD set.
import type { Context } from '@deepseek-ai/cordis'
import { defineTool } from '@deepseek-ai/dsh-tools'
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'

const execFileAsync = promisify(execFile)

export const name = 'rashi'
export const inject = ['tools']

const RASHI_CMD = process.env.RASHI_CMD || 'rashi'
const MAX_OUTPUT = 16 * 1024 // spill guard: long run output is truncated, never streamed raw

export function apply(ctx: Context) {
  ctx.tools.register(defineTool({
    name: 'rashi',
    description:
      'Run the Rashi harness. mode=fleet: detect installed agent CLIs and their readiness. ' +
      'mode=ask: one batch of clarifying intake questions for an idea (goal required). ' +
      'mode=build: one press - research, plan, distribute to ready CLI agents, verify by exit codes ' +
      '(goal and workdir required; needs a free provider key such as KENARI_API_KEY in the environment).',
    parameters: {
      mode: { type: 'string', required: true, description: 'fleet | ask | build' },
      goal: { type: 'string', description: 'Idea or goal text (ask and build)' },
      workdir: { type: 'string', description: 'Absolute directory the build runs in (build only)' },
    },
    output: {
      schema: { type: 'string' },
      render: (_args, value) => [{ type: 'text', text: value }],
    },
    timeoutMs: 900_000, // builds run long; cooperative deadline, enforced by DSH timeout policy
    async execute(args) {
      const mode = String(args.mode)
      let argv: string[]
      if (mode === 'fleet') {
        argv = ['fleet']
      } else if (mode === 'ask') {
        if (!args.goal) throw new Error('rashi ask needs goal')
        argv = ['ask', String(args.goal)]
      } else if (mode === 'build') {
        if (!args.goal || !args.workdir) throw new Error('rashi build needs goal and workdir')
        argv = ['build', String(args.goal), String(args.workdir), '--yes']
      } else {
        throw new Error(`unknown rashi mode: ${mode} (use fleet | ask | build)`)
      }
      try {
        const { stdout, stderr } = await execFileAsync(RASHI_CMD, argv, {
          maxBuffer: 8 * 1024 * 1024,
          env: process.env,
        })
        const out = (stdout + (stderr ? `\n[stderr]\n${stderr}` : '')).trim()
        return out.length > MAX_OUTPUT
          ? out.slice(0, MAX_OUTPUT) + `\n[truncated at ${MAX_OUTPUT} chars]`
          : out || '(rashi produced no output)'
      } catch (err: any) {
        const detail = err && err.code === 'ENOENT'
          ? `rashi CLI not found (RASHI_CMD=${RASHI_CMD}); install with: pip install . from the harness repo`
          : `rashi exited ${err?.code ?? 'error'}: ${String(err?.stderr || err?.message || err)}`
        throw new Error(detail)
      }
    },
  }))
}
