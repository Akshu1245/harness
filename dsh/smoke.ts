// Optional adapter smoke check. Copy beside the plugin inside a DSH checkout, adjust
// the relative import if needed, then run with its tsx loader and RASHI_CMD set.
// Uses the real defineTool through the plugin, but a capture registry, not a live DSH session.
import { apply } from './rashi-plugin.ts'
let tool: any
apply({ tools: { register(value: any) { tool = value } } } as any)
const result = await tool.execute({ mode: 'fleet' })
console.log(JSON.stringify(result))
