// Run without DSH dependencies: node --experimental-strip-types --test dsh/staged.test.ts
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, existsSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { resolve, join } from 'node:path'
import { stagedBuild } from './staged.ts'
const command=resolve('tests/fixtures/staged-child.py')
const workdir=()=>mkdtempSync(join(tmpdir(),'rashi-staged-test-'))
test('only exact host approval permits side effect', async () => {
  for (const allowed of [true,false]) {
    const wd=workdir()
    const result=JSON.parse(await stagedBuild(command,'normal',wd,async review=>{
      assert.ok(review.includes(wd));return allowed
    }))
    assert.equal(result.approved,allowed)
    assert.equal(existsSync(join(wd,'marker')),allowed)
  }
})
test('wrong review digest never reaches host approval', async () => {
  let called=false
  const wd=workdir()
  await assert.rejects(stagedBuild(command,'bad-hash',wd,async()=>{called=true;return true}),/invalid approval frame/)
  assert.equal(called,false);assert.equal(existsSync(join(wd,'marker')),false)
})
test('cancelled parent kills owned process group and settles',async()=>{
  const wd=workdir(),control=new AbortController()
  const promise=stagedBuild(command,'hang',wd,async()=>true,control.signal)
  for(let i=0;i<100&&!existsSync(join(wd,'pids'));i++) await new Promise(r=>setTimeout(r,10))
  assert.ok(existsSync(join(wd,'pids')))
  const pids=readFileSync(join(wd,'pids'),'utf8').split(' ').map(Number)
  control.abort()
  await assert.rejects(promise,/cancelled/)
  for(const pid of pids) {
    // Linux may retain a reaped-orphan zombie briefly; it is dead, not still executing.
    try { assert.equal(readFileSync(`/proc/${pid}/stat`,'utf8').split(' ')[2],'Z') }
    catch(e:any) { if(e.code!=='ENOENT') throw e }
  }
})
test('cancel during an unanswered host prompt also settles',async()=>{
  const wd=workdir(),control=new AbortController()
  const promise=stagedBuild(command,'normal',wd,async()=>{
    setTimeout(()=>control.abort(),20)
    return new Promise<boolean>(()=>{})
  },control.signal)
  await assert.rejects(promise,/cancelled/)
  assert.equal(existsSync(join(wd,'marker')),false)
})
