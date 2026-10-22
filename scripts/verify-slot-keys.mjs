#!/usr/bin/env node
/**
 * 拉上游 DSH slot-catalog，跑 slot 对齐验证（issue #97）。
 *
 * 用法：
 *   node scripts/verify-slot-keys.mjs            # gh api 拉上游 main 的 catalog
 *   node scripts/verify-slot-keys.mjs <file.ts>  # 用给定的 catalog 文件
 *   node scripts/verify-slot-keys.mjs --check     # 只报漂移、不写盘（发版门用）
 *
 * 做三件事：
 *   1. 取到权威 catalog（唯一真相源），列全部 key 与数量
 *   2. 与 test/fixtures/dsh-slot-catalog.ts 快照对比（新鲜度）
 *   3. 跑 test/slot-catalog.test.ts —— allowed 集合由该 catalog 的 bytes 解析而来，
 *      调 apply() 打印实际注入的 key 并逐个对照
 *
 * 绝不用替代品凑：取不到就退出并说明「权威 catalog 不可得」。
 */
import { execFileSync } from 'node:child_process'
import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createHash } from 'node:crypto'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(HERE, '..')
const FIXTURE = join(ROOT, 'test', 'fixtures', 'dsh-slot-catalog.ts')
const UPSTREAM_REPO = 'deepseek-ai/deepseek-harness'
const UPSTREAM_PATH = 'packages/extensions/cordis-client-runner/src/client/slot-catalog.ts'

function fail(msg) {
  console.error(`verify-slot-keys: ${msg}`)
  process.exit(2)
}

function fetchUpstream() {
  const out = execFileSync(
    'gh',
    ['api', `repos/${UPSTREAM_REPO}/contents/${UPSTREAM_PATH}`, '--jq', '.content'],
    { encoding: 'utf8' },
  ).trim()
  if (!out || out.startsWith('{"message"')) fail(`权威 catalog 不可得（gh api 失败）：${out.slice(0, 200)}`)
  return Buffer.from(out, 'base64').toString('utf8')
}

function parseKeys(text) {
  return [...text.matchAll(/^\s*key: '([^']+)'/gm)].map((m) => m[1])
}

// `--check`：只报漂移、不写盘。发版门用它 —— 会自我修复的门等于把漂移藏起来。
const CHECK_ONLY = process.argv.includes('--check')
const argPath = process.argv.slice(2).find((a) => a !== '--check')
let catalogText
let source
if (argPath) {
  if (!existsSync(argPath)) fail(`找不到 catalog 文件：${argPath}`)
  catalogText = readFileSync(argPath, 'utf8')
  source = argPath
} else {
  console.log(`fetching ${UPSTREAM_REPO}:${UPSTREAM_PATH} ...`)
  try {
    catalogText = fetchUpstream()
  } catch (err) {
    fail(
      `权威 catalog 不可得 —— 不做替代验证。\n` +
        `  原因：${String(err)}\n` +
        `  手工取法：gh api repos/${UPSTREAM_REPO}/contents/${UPSTREAM_PATH}`,
    )
  }
  source = `${UPSTREAM_REPO}:${UPSTREAM_PATH} (live)`
}

const keys = parseKeys(catalogText)
if (keys.length === 0) fail('catalog 里一个 key 都没解析出来 —— 文件形状不对，拒绝继续')
const sha = createHash('sha256').update(catalogText).digest('hex').slice(0, 16)

console.log(`\nsource : ${source}`)
console.log(`sha256 : ${sha}`)
console.log(`keys   : ${keys.length}`)
console.log('--- authoritative slot keys ---')
for (const k of keys) console.log(`  ${k}`)

// 与快照对比
if (existsSync(FIXTURE)) {
  const snap = readFileSync(FIXTURE, 'utf8')
  const snapSha = createHash('sha256').update(snap).digest('hex').slice(0, 16)
  if (snapSha === sha) {
    console.log(`\nsnapshot: up to date (${snapSha})`)
  } else {
    const snapKeys = parseKeys(snap)
    const added = keys.filter((k) => !snapKeys.includes(k))
    const removed = snapKeys.filter((k) => !keys.includes(k))
    console.log(`\nsnapshot: STALE (snapshot ${snapSha} vs live ${sha})`)
    console.log(`  keys only in live   (${added.length}): ${added.join(', ') || '-'}`)
    console.log(`  keys only in snapshot(${removed.length}): ${removed.join(', ') || '-'}`)
    if (CHECK_ONLY) {
      fail(
        `fixture is stale (snapshot ${snapSha} vs live ${sha}) — ` +
          `${added.length} key(s) only in live, ${removed.length} only in snapshot. ` +
          `Run without --check to refresh.`,
      )
    }
    if (!argPath) {
      writeFileSync(FIXTURE, catalogText)
      console.log('  snapshot refreshed from upstream.')
    }
  }
} else if (!argPath && !CHECK_ONLY) {
  writeFileSync(FIXTURE, catalogText)
  console.log(`\nsnapshot written to ${FIXTURE}`)
} else if (CHECK_ONLY && !existsSync(FIXTURE)) {
  fail('fixture is missing and --check will not write it')
}

// ── regenerate src/ui/slot-catalog.ts from the same parse (issue #139) ────────
// 两份产物（fixture 与 src 的 CONFIRMED_SLOT_KEYS）曾经分开生成，于是 src 落后了
// 8 个 key 而没人发现（92 vs 100）。现在它们出自同一次 parse：keys 数为 N，两边
// 就都是 N，`CATALOG_PROVENANCE.keyCount` 也写 N —— 数字再对不上就没有来源了。
const SRC = join(ROOT, 'src', 'ui', 'slot-catalog.ts')
function regenerateSource(keys, shaHex, srcText) {
  // 用索引定位而不是正则：声明行里的 `readonly string[]` 含 `[]`，当正则用会
  // 被当成字符类（第一版就是这么没匹配上的）。
  const head = 'export const CONFIRMED_SLOT_KEYS: readonly string[] = ['
  const at = srcText.indexOf(head)
  if (at < 0) return { ok: false, why: 'CONFIRMED_SLOT_KEYS declaration not found' }
  const close = srcText.indexOf('\n]', at)
  if (close < 0) return { ok: false, why: 'CONFIRMED_SLOT_KEYS block is not closed' }
  const sorted = [...keys].sort()
  const body = sorted.map((k) => `  '${k}',`).join('\n')
  let out = srcText.slice(0, at) + head + '\n' + body + srcText.slice(close)
  const now = new Date().toISOString().slice(0, 10)
  out = out
    .replace(/blobSha: '[^']*'/, `blobSha: '${shaHex}'`)
    .replace(/keyCount: \d+/, `keyCount: ${keys.length}`)
    .replace(/fetchedAt: '[^']*'/, `fetchedAt: '${now}'`)
  return { ok: true, text: out, count: keys.length }
}

if (existsSync(SRC)) {
  const srcText = readFileSync(SRC, 'utf8')
  const regen = regenerateSource(keys, sha, srcText)
  if (!regen.ok) fail(`无法重新生成 src/ui/slot-catalog.ts：${regen.why}`)
  const before = (srcText.match(/^  '[^']+',$/gm) || []).length
  if (regen.text !== srcText) {
    if (CHECK_ONLY) {
      const keyDiff =
        before === regen.count
          ? `both have ${before} keys, so the drift is in the provenance block (keyCount / blobSha / fetchedAt)`
          : `${before} key(s) in the snapshot vs ${regen.count} parsed`
      fail(`src/ui/slot-catalog.ts is out of step with the authority — ${keyDiff}. Run without --check to regenerate.`)
    }
    if (!argPath) {
      writeFileSync(SRC, regen.text)
      console.log(`\nsrc/ui/slot-catalog.ts: regenerated ${before} -> ${regen.count} keys (keyCount=${regen.count})`)
    } else {
      console.log(`\nsrc/ui/slot-catalog.ts: would regenerate ${before} -> ${regen.count} keys (dry run, --file mode)`)
    }
  } else {
    console.log(`\nsrc/ui/slot-catalog.ts: already in step (${regen.count} keys)`)
  }
}

console.log('\n--- running non-circular alignment test (apply() vs parsed authority) ---')
const vitestBin = join(ROOT, 'node_modules', '.bin', 'vitest')
const testFile = join(ROOT, 'test', 'slot-catalog.test.ts')
try {
  execFileSync(vitestBin, ['run', testFile, '--reporter=verbose'], {
    cwd: ROOT,
    stdio: 'inherit',
  })
} catch {
  fail('alignment test FAILED')
}
console.log('\nverify-slot-keys: OK — every injected key exists in the authority.')
