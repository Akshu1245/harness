// Emit plain ESM inside the installed DSH host so imports resolve without a source checkout.
import { stripTypeScriptTypes } from 'node:module'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { resolve, dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
const source=resolve(dirname(fileURLToPath(import.meta.url)),'../dsh')
const target=process.argv[2]
if(!target) throw new Error('pass an output directory')
mkdirSync(target,{recursive:true})
for(const name of ['rashi-plugin','staged']) {
  const input=readFileSync(join(source,`${name}.ts`),'utf8')
  const output=stripTypeScriptTypes(input).replace("'./staged.ts'","'./staged.mjs'")
  writeFileSync(join(target,`${name}.mjs`),output)
}
