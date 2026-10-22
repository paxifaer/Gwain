# P9 Lifecycle Unified API Implementation — state

Phase: **P9 Phase 3b static ACCEPTED (D-024) — dynamic E2E deferred to Phase 3c; Phase 4 pending user kickoff** (2026-08-19)
HEAD: ArgoWatch `d2b3b9d` (unchanged ✓); robot-app-platform `f7512bd9` (branch `feat/p9-lifecycle-unified-frontend`,Phase 2a uncommitted changes); ArgoGateway `da0bb4f` (branch `feat/p9-lifecycle-unified-gateway`,0 code change)
sha256 sentry: `demo-app-lifecycle/src/runtime/reconcile.rs` = `74b92f34...72b822` (unchanged ✓)

## Current

- Phase 1 ACCEPTED by V1 (D-012) — 16/16 adversarial checks PASS
- Phase 2a ACCEPTED-pending-Phase-3-payload-fill (D-016) — frontend wiring byte-exact
- Phase 2b ACCEPTED (D-017) — ArgoGateway 0 code change,V2.1-V2.10 全 PASS
- Phase 2 (a+b) 闭环
- Phase 3 kickoff decisions ACCEPTED (D-018, D-019, D-020):
  - D-018 ESCALATE-2a-1: `service_id = "localization-robot-1-docker-exec"`
  - D-019 V2.7 advisory: option (c) document the gap
  - D-020 Phase 3a + 3b 串行 dispatch
- D-021 ESCALATE-3a-1 resolution: option (a) `echo '<pw>' | sudo -S` per documented pattern
- **Phase 3a ACCEPTED (D-022, 2026-08-19 11:32)** — deploy + verify 全 PASS:
  - 新 musl binary (sha256 `8814da20eac5ac30b2e4536e8af31ff8a3f1dec789f61f5ce378483c3025575b`) live on SP000065 PID 107688
  - 23 hits `lifecycle.execute` + 8 action strings 全在
  - `/etc/demo-app-backend/registry.yaml` sha256 `ae4a702b...0038` 0 overwrite
  - 0 ESCALATE,0 git push,0 AI attribution
  - 旧 binary 保留在 `/usr/bin/demo-app-backend.P8-W5.bak.20260819-113025` 可 rollback
  - `argo-gateway-server` (848) + `zenohd-global` (954) + `zenohd-local` (960) 全 unchanged
- **Phase 3b worker completed (D-024, 2026-08-19)** — UUID `f337693c-cd00-4460-bd19-63c5931b4cd9`, logs `/home/wangdang/work/ai-stack/logs/p9-frontend-demoapp/phase3b/`. Worker (~14 min, 79 turns) edited 3 wrappers in `demoRobotControl.ts` (Start/Stop/Restart) to add `service_id: "localization-robot-1-docker-exec"` payload; byte-exact signatures preserved; typecheck/biome PASS.
- **Phase 3b static ACCEPTED (D-024)** — sentries all intact: ArgoWatch `d2b3b9d` ✓ / ArgoGateway `da0bb4f` ✓ (0 tracked change) / robot-app-platform `f7512bd9` ✓ / reconcile.rs sha256 `74b92f34...72b822` ✓ / SP000065 binary + registry unchanged ✓. 31 insertions / 12 deletions cumulative (Phase 2a + 3b) in `demoRobotControl.ts`.
- **ESCALATE-3b-2 (dynamic E2E BLOCKED) → user decision option (d)**: demo app connect path `handleAddRobot` → `invokeTauri("robot_exec_task")` hard-depends on Tauri WebView, no browser fallback → Vite-in-Chrome can't trigger connect → robot card never renders → Start/Stop/Restart buttons never appear. NOT a P9 bug (P9 lifecycle button path is browser-compatible; only upstream connect is Tauri-only). Backend `lifecycle.execute` independently verified via lifecycle_cli (2026-08-18 logs: op=Restart/Start on localization-robot-1-docker-exec). User accepted static + deferred real-robot E2E to **Phase 3c** (Tauri-context runner, needs WebKitGTK automation infra).

## Next

- **Phase 3c (DEFERRED)** — Tauri-context runner real-robot E2E click test on SP000065 (needs WebKitGTK automation infra); user explicitly deferred 2026-08-19, backend already verified via lifecycle_cli — not on critical path
- **Phase 4 (pending user kickoff)** — deprecate 旧 7 topic (D-008): ArgoGateway returns `MIGRATED` RPC error + 2-week grace before hard unsubscribe

## Decisions (详见 decisions.md)

- D-001..D-008 8 design open questions resolved
- D-009..D-012 Phase 1 + V1 verifier ACCEPT
- D-013..D-015 Phase 2 启动 + Scheme A + 前端 write-set
- D-016 Phase 2a worker ACCEPTED-pending-Phase-3-payload-fill
- D-017 Phase 2b ArgoGateway verifier ACCEPT
- D-018 ESCALATE-2a-1 resolution: `service_id = "localization-robot-1-docker-exec"`
- D-019 V2.7 advisory resolution: option (c) document the gap
- D-020 Phase 3a + 3b 串行 dispatch
- D-021 ESCALATE-3a-1 resolution: option (a) `echo '<pw>' | sudo -S`
- **D-022 Phase 3a ACCEPT — deploy + verify 全 PASS**
- **D-023 Phase 3b worker dispatched** (2026-08-19 11:39) — PID 2236202, UUID `f337693c-cd00-4460-bd19-63c5931b4cd9`, logs `/home/wangdang/work/ai-stack/logs/p9-frontend-demoapp/phase3b/`, hard 30-min cap
- **D-024 Phase 3b static ACCEPTED + dynamic E2E deferred to Phase 3c** (2026-08-19) — 3 wrappers payload-filled, byte-exact signatures, sentries intact (ArgoWatch/ArgoGateway/robot-app-platform HEADs + reconcile.rs sha256 + SP000065 binary/registry unchanged); ESCALATE-3b-2 (Tauri WebView dep blocks browser E2E) → user option (d) accept static + defer real-robot E2E to Phase 3c

## Blocked (read-only — Phase 3b worker must respect)

- `code/ArgoWatch/**` — Phase 1 byte-exact 锁定(Phase 3b 不动后端)
- `code/ArgoGateway/**` — Phase 2b 验证已闭,Phase 3b 不动
- `/etc/demo-app-backend/registry.yaml` on SP000065 — 不改 registry(sha256 必须保持 `ae4a702b...0038`)
- `packages/gateway-client/src/lib/demoRobotControl.ts` `runLifecycleExecute` 函数签名(byte-exact 保留,Phase 3b 只加 payload 内容)
- `runChatCommand` 函数体(`demoRobotControl.ts:239-258`)— byte-exact 保留
- UI 按钮(`RobotCardSettingsDialog.tsx` 4 个按钮 onClick)— 0 改动
- SP000065 robot host 其他文件 — 不动
- SP000065 zenohd (954/960) + argo-gateway-server (848) + demo-app-backend (107688) — 0 touch

## Watch-out

- Phase 3b 真机 E2E:前端 dev server 启动后 browser MCP click 3 按钮(Start/Stop/Restart),verify SP000065 backend journalctl + `/var/log/robot/demo-app-backend/demo-app-backend.log` 收到 `lifecycle.execute` + docker exec probe `echo PA3_OK && id && hostname` 输出
- 50053 (TLS) listening on SP000065 — demo app connect 用 50053 mTLS per [[project_sp000065_tls_client_bug.md]];50051 (plaintext) 不确定是否开放,worker 需 verify port 可达性
- V2.7 known gap:zenoh hop drops `request_id` — Phase 3 E2E 用 Chat 层 correlation_id 即可(D-019)
- pre-existing baseline test failures(group_restart_e2e 3, oneshot_e2e 5)在后端 — 不影响 lifecycle.execute 通路
- UI 测试必须 browser MCP click(per [[feedback_ui_test_browser_click.md]])
- SP000065 上 `argo-gateway-server` (pid 848)运行中 — Phase 3b 不动 ArgoGateway
