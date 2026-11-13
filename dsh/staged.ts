// Trusted adapter bridge. No model-facing approval argument; the native approval service decides.
import { spawn } from 'node:child_process'
import { createHash } from 'node:crypto'
import { createInterface } from 'node:readline'

export async function stagedBuild(command: string, goal: string, workdir: string,
  decide: (review: string) => Promise<boolean>, signal?: AbortSignal): Promise<string> {
  if (signal?.aborted) throw new Error('cancelled')
  const child = spawn(command, ['staged-build', goal, workdir], {
    env: process.env, stdio: ['pipe', 'pipe', 'pipe'], detached: process.platform !== 'win32',
  })
  let stderr = '', result: unknown, failure: Error | undefined
  const stop = () => {
    if (!child.pid) return
    try { process.platform === 'win32' ? child.kill('SIGKILL') : process.kill(-child.pid, 'SIGKILL') } catch {}
  }
  const abort = () => { failure = new Error('cancelled'); stop() }
  signal?.addEventListener('abort', abort, { once: true })
  const timer = setTimeout(() => { failure = new Error('build timeout'); stop() }, 900_000)
  child.stderr.on('data', chunk => { stderr = (stderr + chunk).slice(-4000) })
  // Attach completion handlers immediately so a rejected/early exit cannot be missed.
  const closed = new Promise<number | null>((resolve, reject) => {
    child.on('close', resolve); child.on('error', reject)
  })
  child.stdin.on('error', () => { stop() })
  let pendingBytes = 0
  child.stdout.on('data', chunk => {
    const text = chunk.toString()
    const last = text.lastIndexOf('\n')
    pendingBytes = last < 0 ? pendingBytes + chunk.length : Buffer.byteLength(text.slice(last + 1))
    if (pendingBytes > 262144 || chunk.length > 1048576) {
      failure = new Error('oversized build frame'); stop()
    }
  })
  const lines = createInterface({ input: child.stdout })
  let asked = false
  try {
    for await (const line of lines) {
      if (line.length > 262144) throw new Error('oversized build frame')
      const frame = JSON.parse(line)
      if (frame.type === 'approval_request') {
        if (asked || typeof frame.review !== 'string' || frame.review.length > 100000 ||
            typeof frame.sha256 !== 'string' ||
            createHash('sha256').update(frame.review).digest('hex') !== frame.sha256) throw new Error('invalid approval frame')
        asked = true
        const allowed = await Promise.race([decide(frame.review),
          closed.then(() => { throw failure || new Error('build exited while awaiting approval') })])
        if (signal?.aborted) throw new Error('cancelled')
        child.stdin.write(JSON.stringify({ decision: allowed ? 'approve' : 'reject', sha256: frame.sha256 }) + '\n')
        child.stdin.end()
      } else if (frame.type === 'result') result = frame.result
      else throw new Error('unexpected build frame')
    }
    const code = await closed
    if (failure) throw failure
    if (code !== 0 || result === undefined) throw new Error(`staged build exited ${code}: ${stderr}`)
    return JSON.stringify(result)
  } catch (error) {
    stop()
    await closed.catch(() => {})
    throw error
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', abort)
    lines.close()
  }
}
