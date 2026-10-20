/**
 * apply() 生命周期测试：加载注册服务、卸载还原、非法配置/缺失知识库响亮失败。
 *
 * 用真实 cordis Context 驱动 fiber（加载即生效、卸载即还原）。不启动 DSH ——
 * 这里只验证插件契约与生命周期，渲染需 DSH 运行时验证，本机未执行。
 */
import assert from 'node:assert/strict'
import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, it } from 'vitest'
import { Context } from '@deepseek-ai/cordis'
import * as prGenius from '../src/index.ts'
import { parseConfig, PrGeniusConfigError } from '../src/config.ts'
import { defaultKbRoot, resolveKbRoot } from '../src/kb.ts'
import type { PrGeniusService } from '../src/index.ts'

function asService(value: unknown): PrGeniusService {
  assert.ok(value !== undefined && value !== null, 'prGenius service should be registered')
  return value as PrGeniusService
}

describe('apply() lifecycle', () => {
  it('registers the prGenius service on load and restores on unload', async () => {
    const ctx = new Context()
    const fiber = ctx.plugin(prGenius, parseConfig({}))
    await fiber

    const service = asService(ctx.get('prGenius'))
    assert.equal(typeof service.describe, 'function')
    assert.equal(typeof service.callTool, 'function')
    assert.equal(typeof service.close, 'function')
    assert.equal(service.describe().name, 'pr-genius')
    assert.equal(service.describe().mcp.transport, 'stdio')
    assert.equal(service.describe().kbRoot, defaultKbRoot())

    await fiber.dispose()
    assert.equal(ctx.get('prGenius'), undefined, 'service must be gone after unload')
  })

  it('describe() reflects config overrides (maintainer mode, locale, risk filter, sidebar)', async () => {
    const ctx = new Context()
    const config = parseConfig({
      sidebar: { defaultView: 'panel' },
      maintainer: {
        enabled: true,
        actions: ['READY_FOR_REVIEW', 'HOLD_MAINTAINER_DECISION'],
        confidenceMin: 0.5,
        staleDays: 7,
      },
      locale: 'zh-CN',
      riskFilter: 'high_risk',
      mcp: { transport: 'http', url: 'http://127.0.0.1:9999/mcp' },
    })
    const fiber = ctx.plugin(prGenius, config)
    await fiber

    const info = asService(ctx.get('prGenius')).describe()
    assert.equal(info.sidebar.defaultView, 'panel')
    assert.equal(info.maintainer.enabled, true)
    assert.deepEqual(info.maintainer.actions, ['READY_FOR_REVIEW', 'HOLD_MAINTAINER_DECISION'])
    assert.equal(info.maintainer.confidenceMin, 0.5)
    assert.equal(info.maintainer.staleDays, 7)
    assert.equal(info.locale, 'zh-CN')
    assert.equal(info.riskFilter, 'high_risk')
    assert.equal(info.mcp.transport, 'http')
    assert.equal(info.mcp.endpoint, 'http://127.0.0.1:9999/mcp')

    await fiber.dispose()
    assert.equal(ctx.get('prGenius'), undefined)
  })

  it('fails load loudly when config is invalid (no half-mounted service)', async () => {
    const ctx = new Context()
    const fiber = ctx.plugin(prGenius, { locale: 'fr' } as never)
    await assert.rejects(() => Promise.resolve(fiber))
    assert.equal(ctx.get('prGenius'), undefined, 'invalid config must not leave a service registered')
  })

  it('fails load loudly when kbRoot has no knowledge base layout', async () => {
    const emptyRoot = mkdtempSync(join(tmpdir(), 'pr-genius-empty-kb-'))
    const ctx = new Context()
    const fiber = ctx.plugin(prGenius, parseConfig({ kbRoot: emptyRoot }))
    await assert.rejects(() => Promise.resolve(fiber), (error: unknown) => {
      assert.ok(error instanceof PrGeniusConfigError || error instanceof Error)
      assert.match(String(error), /kbRoot/)
      return true
    })
    assert.equal(ctx.get('prGenius'), undefined)
  })

  it('is idempotent across load/unload cycles', async () => {
    const ctx = new Context()
    for (let i = 0; i < 3; i++) {
      const fiber = ctx.plugin(prGenius, parseConfig({}))
      await fiber
      assert.ok(ctx.get('prGenius') !== undefined, `cycle ${i}: service registered`)
      await fiber.dispose()
      assert.equal(ctx.get('prGenius'), undefined, `cycle ${i}: service removed`)
    }
  })
})

describe('knowledge base layout', () => {
  it('defaultKbRoot points at the package root with the shipped knowledge base', () => {
    const layout = resolveKbRoot('')
    assert.equal(layout.root, defaultKbRoot())
    for (const dir of [layout.antiPatterns, layout.successPatterns, layout.profiles, layout.policies]) {
      assert.ok(dir.startsWith(layout.root), `${dir} should live under ${layout.root}`)
    }
  })

  it('resolves an explicit kbRoot and rejects one without the layout', () => {
    const fakeKb = mkdtempSync(join(tmpdir(), 'pr-genius-fake-kb-'))
    for (const sub of ['anti-patterns', 'success-patterns', 'profiles', join('docs', 'policies')]) {
      mkdirSync(join(fakeKb, sub), { recursive: true })
    }
    writeFileSync(join(fakeKb, 'anti-patterns', 'sample.yml'), 'key: sample\n')
    const layout = resolveKbRoot(fakeKb)
    assert.equal(layout.root, fakeKb)

    assert.throws(
      () => resolveKbRoot(mkdtempSync(join(tmpdir(), 'pr-genius-no-kb-'))),
      (error: unknown) => {
        assert.ok(error instanceof PrGeniusConfigError)
        assert.equal(error.field, 'kbRoot')
        return true
      },
    )
  })
})

/**
 * 空壳安装的告警与注册上报（issue #131）。
 *
 * #86/#90/#95/#97/#98/#100/#101/#117 —— 五周八次，每次都靠单测说"已修"、
 * 没人真跑过。warn 藏得住，logger.error 不该藏；describe() 里的结构化结果
 * 藏不住，宿主和测试都能读。
 */
describe('surface registration report (#131)', () => {
  /**
   * 记录 apply() 真正打出来的日志。
   *
   * 必须挂 `ctx.logger` —— resolveLogger 先试它，取不到才落到 console；
   * 真实 cordis Context 有自己的 logger，只截 console 会漏掉全部输出
   * （第一版测试就是这么误报"没有 error"的）。
   */
  function captureLogs(ctx: Context) {
    const errors: unknown[][] = []
    const warns: unknown[][] = []
    const infos: unknown[][] = []
    const rec = {
      info: (...a: unknown[]) => {
        infos.push(a)
      },
      warn: (...a: unknown[]) => {
        warns.push(a)
      },
      error: (...a: unknown[]) => {
        errors.push(a)
      },
    }
    ;(ctx as unknown as { logger: (n: string) => unknown }).logger = () => rec
    return {
      errors,
      warns,
      infos,
      restore() {
        delete (ctx as unknown as { logger?: unknown }).logger
      },
    }
  }

  /** 一个 slots 宿主：`accept` 决定每个 key 是否被认下。 */
  function hostSlots(accept: boolean) {
    const injected: string[] = []
    return {
      injected,
      inject(slot: string, factory: () => unknown) {
        if (!accept) throw new Error(`slot ${slot} is not in this host's catalog`)
        injected.push(slot)
        factory()
        return () => {
          /* dispose */
        }
      },
      register(_def: unknown, _component: unknown) {
        return () => {
          /* dispose */
        }
      },
    }
  }

  /** 假的 slash 命令服务 —— 只需要被调用后返回一个带 action 的对象。 */
  function hostCommand() {
    return (_name: string) => ({
      action(fn: () => unknown) {
        return fn
      },
      option: undefined,
    })
  }

  /**
   * 把假宿主挂到 ctx.get(...) 上 —— optionalService 就走这个口，
   * 属性兜底只在宿主没有 get() 时才用，真实 cordis Context 一定有。
   *
   * 两个服务都给：slots 决定 UI 面的成败，command 决定 slash 面 —— 分开给，
   * 报告里才分得清"slot 面全灭"和"命令面是好的"。
   */
  function withHost(
    ctx: Context,
    slots: ReturnType<typeof hostSlots>,
    command: ReturnType<typeof hostCommand> | null = hostCommand(),
  ): Context {
    const original = ctx.get.bind(ctx)
    ;(ctx as unknown as { get: (n: string) => unknown }).get = (n: string) => {
      if (n === 'slots') return slots
      if (n === 'command') return command ?? undefined
      return original(n)
    }
    return ctx
  }

  it('logs an ERROR when the host accepts none of the UI surfaces', async () => {
    const ctx = withHost(new Context(), hostSlots(false))

    const logs = captureLogs(ctx)
    try {
      const fiber = ctx.plugin(prGenius, parseConfig({}))
      await fiber
      const report = asService(ctx.get('prGenius')).describe().surfaces
      assert.ok(report, 'describe().surfaces must be populated after apply()')
      assert.equal(report.slotsAvailable, true, 'the fake host must have been detected')
      assert.equal(report.registered.filter((r) => r.id !== 'pr-genius').length, 0)
      assert.equal(report.failed.length >= 4, true, `expected >=4 failed, got ${report.failed.length}`)

      const flat = logs.errors.map((a) => a.map(String).join(' ')).join('\n')
      assert.ok(
        /NO SURFACES REGISTERED/i.test(flat),
        `expected a logger.error about total registration failure, got: ${flat || '(no error logged)'}`,
      )
      await fiber.dispose()
    } finally {
      logs.restore()
    }
  })

  it('does not log an error when every surface registers', async () => {
    const ctx = withHost(new Context(), hostSlots(true))

    const logs = captureLogs(ctx)
    try {
      const fiber = ctx.plugin(prGenius, parseConfig({}))
      await fiber
      const report = asService(ctx.get('prGenius')).describe().surfaces
      assert.ok(report)
      assert.equal(report.slotsAvailable, true)
      assert.equal(
        report.registered.filter((r) => r.id !== 'pr-genius').length,
        4,
        'all four UI surfaces should register on a permissive host',
      )
      assert.equal(report.failed.filter((r) => r.id !== 'pr-genius').length, 0)

      const flat = logs.errors.map((a) => a.map(String).join(' ')).join('\n')
      assert.ok(
        !/NO SURFACES REGISTERED/i.test(flat),
        `no total-failure error expected, got: ${flat}`,
      )
      await fiber.dispose()
    } finally {
      logs.restore()
    }
  })

  it('describe().surfaces names the seats that were accepted and the candidates that were not', async () => {
    const ctx = withHost(new Context(), hostSlots(false))
    const logs = captureLogs(ctx)
    try {
      const fiber = ctx.plugin(prGenius, parseConfig({}))
      await fiber
      const report = asService(ctx.get('prGenius')).describe().surfaces
      assert.ok(report)
      assert.equal(report.expected, 5, '4 UI surfaces + the slash command')

      const panel = report.failed.find((f) => f.id === 'pr-genius.advisor-panel')
      assert.ok(panel, 'the panel surface should be listed as failed')
      assert.ok(
        panel.candidates && panel.candidates.length > 0,
        `the panel carries two candidate slots; got ${JSON.stringify(panel.candidates)}`,
      )
      assert.ok(
        panel.candidates!.includes('details') && panel.candidates!.includes('sidebar.right.pane.tab'),
        `both candidate keys must be reported so a host can say which catalog it ships; got ${panel.candidates}`,
      )

      const cmd = report.registered.find((r) => r.id === 'pr-genius')
      assert.ok(cmd, 'the slash command is registered separately and must appear in the report')
      await fiber.dispose()
    } finally {
      logs.restore()
    }
  })
})
