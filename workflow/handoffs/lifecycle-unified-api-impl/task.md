# P9 — Lifecycle Unified API Implementation

- **Phase**: P9 Phase 1 (backend-only additive)
- **Risk**: High (S3 spans sessions + S4 design wiring must survive — Gawain workflow.md High-Risk Reasoning Gate)
- **Predecessor**: P8 closed D-132 (V5 ACCEPT, lifecycle robot takeover done)
- **Design doc**: `code/Gawain/workflow/handoffs/lifecycle-unified-api-design/DESIGN.md` (792 lines, 49 KB, kimi-k3 worker)
- **User instruction (verbatim)**:
  1. 严格按照 `code/Gawain/workflow/bootstrap.md` 的工作方式
  2. 我们现在先对后端接口改造
  3. `code/frontend/robot-app-platform` 这个前端接口放在下一届阶段
  4. 所有测试不要 mock 必须端到端

## Task

在 `code/ArgoWatch` 的 `demo-app-backend` + `demo-app-lifecycle` crate 内,**additive** 引入统一 lifecycle API:

- 新 action `lifecycle.execute` + 新 zenoh topic `lifecycle/execute/submit`
- `payload.op` (`ListGroups` / `ListState` / `GetState` / `Start` / `Stop` / `Restart` / `GroupStart` / `GroupStop` / `GroupRestart` + `CustomOp` escape hatch) 分发到现有 7 个 handler —— **复用,不重写**
- 旧 7 个 topic + 旧 7 个 action 全部保留(dual-track,additive),不得破坏任何 byte-exact 行为
- reconcile.rs 的 sha256 sentry `74b92f34...72b822` 必须保持不变
- HEAD `d2b3b9d` 必须保持不变(本期纯设计/实现,0 git push,0 AI attribution)
- 必须遵循 Gawain Integration Traceability Contract(8 verifier checks,FAIL/ERROR/STATE taxonomy,first-failure 原则,correlation_id 跨 6 transport 传递,run_id 经 `GAWAIN_RUN_ID` env)

## Out of scope (must NOT touch)

- `code/frontend/robot-app-platform/*` —— 下一届阶段
- ArgoGateway proto(`code/ArgoGateway/proto/*`) —— 下一届阶段(本期只在 ArgoWatch 内做后端 envelope + dispatch)
- `demo-app-lifecycle/src/reconcile.rs` —— sha256 sentry 锁定
- 旧 7 topic 订阅 / 旧 7 handler 函数体 / 旧 7 action 常量
- 任何 robot host 文件 / SP000065 上的运行进程(本期不 deploy,只在本机 build + 单元/集成自检;真机 E2E 在 Phase 3)

## Acceptance — Phase 1 (本期 worker 必须达成)

- A1. `cargo build -p demo-app-backend -p demo-app-lifecycle` 0 warning 0 error
- A2. `cargo test  -p demo-app-backend -p demo-app-lifecycle` 0 fail(若新增统一 API 单测,必须真连接 zenoh + 真 lifecycle registry,不得 mock —— 见约束 4)
- A3. `git -C code/ArgoWatch status --short` 仅显示本期新增/修改的文件,无意外 diff
- A4. `git -C code/ArgoWatch log --oneline -1` 仍是 `d2b3b9d`(未 commit,未 push)
- A5. `sha256sum code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/src/reconcile.rs` 仍是 `74b92f34...72b822`(sentry 保持)
- A6. 旧 7 action 常量(`lifecycle.list_groups` 等)与旧 7 topic 订阅在 `demo-app-backend/src/handlers.rs` + `main.rs` 全部保留 byte-exact
- A7. 新 `lifecycle.execute` 路径的所有 FAIL/ERROR/STATE 日志满足 8 verifier checks(由 V1 verifier 在 Phase 1 完成后用 evidence.md 对抗性审计)
- A8. 0 git push / 0 AI attribution / 0 mock test / 0 跨 write-set 修改

## Acceptance — Phase 3 (后续阶段,真机 E2E verifier,本期不执行)

- B1. SP000065 (192.168.100.100) 上 deploy Phase 1 产物(.deb 或 cargo install)
- B2. 7/7 ops 通过新 `lifecycle.execute` 通路在 SP000065 真机执行 PASS(无 mock)
- B3. `INVALID_INTENT` 与 `MISSING_FEATURE` 错误字节级与旧路径一致
- B4. `correlation_id` 从 frontend → ArgoGateway → zenoh → demo-app-backend → provider 全链路传递
- B5. `run_id` 经 env `GAWAIN_RUN_ID` 注入,所有 FAIL/ERROR 事件可重建 first-failure

## References

- `code/Gawain/workflow/bootstrap.md` — worker classification rules + hard constraints
- `code/Gawain/workflow/workflow.md` — Plan/Dispatch/Judge + High-Risk Reasoning Gate
- `code/Gawain/workflow/worker-preamble.md` — verbatim preamble for every worker
- `code/Gawain/workflow/agentflow/observability/README.md` — 8 verifier checks
- `code/Gawain/workflow/agentflow/observability/events.md` — FAIL/ERROR/STATE taxonomy
- `code/Gawain/workflow/agentflow/observability/evidence.md` — verifier adversarial checklist
- `code/Gawain/workflow/handoffs/lifecycle-unified-api-design/DESIGN.md` — design doc (8 open questions resolved, see decisions.md D-001..D-008)
- `code/Gawain/workflow/handoffs/demo-app-backend-lifecycle-integration/state.md` — P8 closure D-132

## Worker UUID

- Phase 1 implementation worker: `550803f9-0ff7-441f-a1fc-92bdc4195a8a`
- Model: `t9s/kimi-k3`
- Logs: `/home/wangdang/work/ai-stack/logs/p9-lifecycle-impl-phase1/`
- Hard cap: 30 min (`timeout -k 5 1800s`)
