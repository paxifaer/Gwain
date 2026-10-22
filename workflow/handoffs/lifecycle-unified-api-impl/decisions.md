# P9 Lifecycle Unified API Implementation — decisions

所有决策均来自 design worker 的 DESIGN.md §10 Open Questions + 用户 2 轮 AskUserQuestion 答复 + 用户 4 条硬约束。

## D-001 — Proto 文件位置:新建 `lifecycle.proto`(Q1)

- **选择**:在 ArgoGateway `gateway.v1` 包下新建 `lifecycle.proto`,独立文件,按业务域拆分
- **理由**:便于后续按业务域(lifecycle / status / logs / ...)拆 proto;不污染 `robot_control.proto`
- **本期影响**:0(本期不碰 ArgoGateway proto,下届阶段做)
- **何时启用**:Phase 2(backend .deb 上 SP000065 之后,ArgoGateway proto 改造届)

## D-002 — `schema_version` 字段:占位不启用(Q2)

- **选择**:proto 中保留 `schema_version` 字段编号,但 v1 不强制校验
- **理由**:proto3 字段编号一旦占用即永久保留;占位为未来版本协商留位
- **本期影响**:0(本期不写 proto)

## D-003 — `client_caps` 字段:占位不启用(Q3)

- **选择**:proto 中保留 `client_caps` 字段编号,v1 不强制 client 传
- **理由**:为未来 client capability 声明(feature flag / 版本协商)留位
- **本期影响**:0

## D-004 — Stream vs Unary:Unary RPC(Q4)

- **选择**:`LifecycleExecute` 是 unary 请求-响应,fire-and-forget + get_state 轮询
- **理由**:当前后端 7 handler 已是 fire-and-forget;引入 stream 增加复杂度且打破现有 envelope 模型
- **本期影响**:0(本期不写 proto)

## D-005 — 扩展范围:本期只统一 lifecycle(Q5)

- **选择**:`robot.status` / `robot.operational` / `logs.collect` 等其它 action namespace **本期不统一**
- **理由**:控制本期爆炸半径;lifecycle 先把模式跑通,再扩
- **本期影响**:正本清源 — Phase 1 worker 只动 lifecycle 相关 handler / topic / action

## D-006 — `x-*` escape hatch lint:buf lint plugin(Q6)

- **选择**:用 buf lint plugin 强制 `CustomOp` 走 `x-*` 前缀,而非 pre-commit hook
- **理由**:buf 已是 proto 生态标准;pre-commit 易绕过
- **本期影响**:0(本期不写 proto)

## D-007 — §5.4 Completed 相位语义:保留现状(Q7)

- **选择**:`Stop` from `Completed` **不开放**(矩阵:Stop 不允许 Completed)
- **理由**:P4/V3-C1 已开放 `Restart` from `Completed`;`Stop` 开放语义不清(Completed 已是终态,Stop 是动作 — 不应混淆)
- **本期影响**:0(Phase 1 worker 不得改 §5.4 矩阵)

## D-008 — 旧 topic 退订阅:`MIGRATED` error + 2 周 grace(Q8)

- **选择**:Phase 4 硬删旧 7 topic 前,ArgoGateway 先对旧 topic 订阅者返回 `MIGRATED` RPC error(含新 topic 指引),保留 2 周观察期再硬退订阅
- **理由**:短期 404 对调用方不友好;显式 `MIGRATED` 让 client 能升级 + 2 周 grace 兜底
- **本期影响**:0(本期是 Phase 1 additive,旧 topic 全部保留)

## D-009 — P9 启动(8 决策全采纳 + 4 硬约束)

- **触发**:用户 2026-08-18 拍板"先决策 8 个 open question" → 全采纳推荐 → 加 4 条硬约束(bootstrap.md / 后端先改 / 前端下届 / 0 mock 全 E2E)
- **风险等级**:High(S3 spans sessions + S4 design wiring must survive)
- **触发动作**:建 task-state layout(task.md / state.md / decisions.md / evaluation.md / sync/)
- **时间**:2026-08-19

## D-010 — Phase 1 = backend-only additive(用户硬约束 #2 + #3)

- **选择**:Phase 1 worker write-set 限定在 `code/ArgoWatch/demo_app_service/crates/demo-app-backend/**` + `code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/**`(不含 reconcile.rs)
- **必做**:
  - `demo-app-lifecycle/src/handlers.rs` 新增 `ACTION_LIFECYCLE_EXECUTE = "lifecycle.execute"` 常量
  - 新增 `handle_lifecycle_execute(req: &Envelope) -> Envelope` 函数,解析 `payload.op` 后 dispatch 到现有 7 个 handler(复用,不重写)
  - `demo-app-backend/src/handlers.rs` `dispatch_action` 新增 `lifecycle.execute` match arm
  - `demo-app-backend/src/main.rs`(或对应订阅注册点)新增 `lifecycle/execute/submit` topic 订阅
  - 新增/扩展 FAIL/ERROR/STATE 日志满足 8 verifier checks
- **禁做**:
  - 0 改 reconcile.rs
  - 0 改 robot-app-platform 任何文件
  - 0 改 ArgoGateway 任何文件
  - 0 改 proto(本期 envelope 仍是 JSON,不引入 protobuf)
  - 0 mock test
  - 0 git push,0 AI attribution
  - 0 改旧 7 action 常量 / 旧 7 topic 订阅 / 旧 7 handler 函数体
- **时间**:2026-08-19 起,30-min hard cap per worker session

## D-011 — Phase 1 worker ACCEPTED-pending-V1(2026-08-19 09:54)

- **触发**:Phase 1 worker 退出,5 个 Edit 全 additive,build PASS,sentries 全 intact
- **审计结论**(orchestrator 验证):
  - 5 Edit 调用:Edit #1-#2 在 `demo-app-lifecycle/src/handlers.rs`(新增常量 + helper + handle_lifecycle_execute 函数,appended at end),Edit #3-#5 在 `demo-app-backend/src/handlers.rs`(imports + outer match + inner dispatch,各 +1 行/臂)
  - 严格 additive:worker 0 deletion,git diff 中 322 deletions 全部 pre-existing(早于 worker 启动,worker 通过 `git stash -u` + `git stash pop` 验证 baseline 不变)
  - HEAD `d2b3b9d` ✓ unchanged;reconcile.rs sha256 `74b92f34...72b822` ✓ unchanged
  - 独立 `cargo build -p demo-app-backend -p demo-app-lifecycle` PASS 1.32s 0 warning 0 error
  - 0 git push,0 AI attribution,0 mock test,0 frontend touch,0 ArgoGateway touch,0 reconcile.rs touch
- **2 ESCALATEs**:
  - ESCALATE-1 GroupStart/GroupStop → `UNKNOWN_OP`(worker 选 option (a) 保守路径,不扩 60-80 行新 handler;defer 到 Phase 2 §5.4 matrix sign-off)
  - ESCALATE-2 0 new e2e test for `lifecycle.execute`(dev box 缺 SP000065 systemd + zenoh bus 基建;defer 到 Phase 3 SP000065 E2E per Acceptance B1-B5)
- **状态**:ACCEPTED-pending-V1 — Phase 1 self-audit PASS,但 V1 verifier 对抗审计未跑;V1 PASS 才进 Phase 2
- **后续动作**:dispatch V1 verifier(adversarial mandate via evidence.md 8 checks)

## D-012 — V1 verifier ACCEPT(2026-08-19 09:58)

- **触发**:V1 verifier 退出,16 项对抗检查全 PASS,0 counterexample,0 新 ESCALATE
- **verifier runtime**:2.5 min(09:56:06 → 09:58:36),远低于 30-min cap
- **verifier 结论**:
  - Write-set additive(5 Edit 全 additive,Edit #3 use-block 重写但保留 7 原始 imports byte-exact + 加 2 新)
  - Build/clippy PASS(worker 新代码 0 warning;pre-existing clippy warning 在 handlers.rs:358 不归 worker)
  - E5.1-E5.8 全 PASS(log presence/correlation/identity/failure semantics/retry/cause/first-failure/scope)
  - topic.rs 0 change + `extract_action_from_topic` 真的把 `lifecycle/execute/submit` 解析成 `lifecycle.execute`(cargo test 6 passed)
  - main.rs wildcard `**` 真覆盖 `lifecycle/execute/submit`(3 segments deep,同旧 7 topic)
  - reconcile.rs sha256 sentry intact;0 git push;0 AI attribution;HEAD `d2b3b9d`
  - 0 frontend touch / 0 ArgoGateway touch(pre-existing baseline 验证)
  - 0 mock test(ESCALATE-2 推理 strong + minor note:可考虑纯 dispatch logic 单测,非 contract 违规)
- **verifier 自己的 open judgment calls**:
  - use-block 重写算 additive(语义保留 byte-exact)
  - git stash cycle 非 git op(bootstrap.md 只禁 push + AI attribution)
  - ESCALATE-2 conservative reading 可接受
- **后续动作**:Phase 1 ACCEPTED,Phase 2(ArgoGateway proto + 前端 wiring)按用户硬约束 #3 留给下届阶段;Phase 3 SP000065 E2E + Phase 4 deprecate 旧 7 topic 也排后续

## D-013 — Phase 2 启动(2026-08-19)—— 前端 demoapp + ArgoGateway 验证

- **触发**:用户 2026-08-19 "可以开始前端的开发...先对demoapp进行开发...argogatewayserver这边也新建一分支"
- **范围**:
  - Phase 2a — robot-app-platform demoapp 前端 wiring(本期重点)
  - Phase 2b — ArgoGateway 验证(read-only,确认 Chat RPC → zenoh 转发路径处理 `lifecycle.execute` 正确)
- **分支**:
  - robot-app-platform: `feat/p9-lifecycle-unified-frontend`(from `feat/argo-tls-discovery` HEAD `f7512bd9`)
  - ArgoGateway: `feat/p9-lifecycle-unified-gateway`(from `feat/argo-tls` HEAD `da0bb4f`)
- **0 push**:本地分支,0 git push,0 AI attribution

## D-014 — Phase 2 走 Scheme A(Chat RPC 隧道,0 proto 改动)

- **选择**:Scheme A — 前端继续用现有 `Chat(ChatRequest)` RPC 隧道,只是把 `action` 从 `restart_service` / `start_service` / `stop_service` 改成 `lifecycle.execute` + `payload.op`
- **理由**:
  - ArgoGateway `argo-gateway-chat/src/lib.rs:224-225` 通用规则 `if resolved.contains("/watch/") && resolved.ends_with("/submit")` 已经处理任何 `watch/<x>/submit` topic,包括 `lifecycle/execute/submit`
  - 前端 `runChatCommand`(`demoRobotControl.ts:239`)已做 `action.replace(/\./g, "/")` —— `lifecycle.execute` 自动变成 `lifecycle/execute/submit`,0 改动 runChatCommand
  - 0 proto 改动 = 0 ArgoGateway 服务器代码改动 = 短期最高 ROI
- **不做**:Scheme B(新建 typed `LifecycleExecute` RPC + 新 `lifecycle.proto`)—— 中期方案,Phase 4 之后做

## D-015 — Phase 2a 前端 write-set 边界

- **必做**:
  - `packages/gateway-client/src/lib/demoRobotControl.ts` 加 `runLifecycleExecute(session, op, payload?)` 函数 + 重构 `restartDemoRobot` / `startDemoRobot` / `stopDemoRobot` 内部走 `lifecycle.execute` + op
  - 可选:加新 op wrapper(`listGroupsDemoRobot` / `listStateDemoRobot` / `getStateDemoRobot` / `groupRestartDemoRobot`)
  - `apps/demo/src/hooks/useDemoRobotControl.ts` 可选暴露新 op(若加新 wrapper)
- **禁做**:
  - 0 改 UI 按钮(`RobotCardSettingsDialog.tsx` 4 个按钮 onClick 仍调 `handleStartDemo / handleStopDemo / handleRestartDemo`,handler 内部自动走新路径)
  - 0 改 ArgoGateway 任何文件(Phase 2b 只读验证)
  - 0 改 demo-app-backend / demo-app-lifecycle(Phase 1 已 done)
  - 0 改 reconcile.rs / 旧 7 action 常量 / 旧 7 handler(backend byte-exact 锁定)
  - 0 mock test(E2E 真机测试留 Phase 3 SP000065)
  - 0 git push,0 AI attribution
- **acceptance**:
  - `pnpm typecheck`(或 `tsc --noEmit`)0 error
  - `pnpm lint` 0 warning(若 lint script 存在)
  - 旧 3 个 export 函数签名 byte-exact 保留(`restartDemoRobot(session)` / `startDemoRobot(session)` / `stopDemoRobot(session)`)
  - 新 `runLifecycleExecute` 函数签名清晰,op 类型为联合字面量(`"Start" | "Stop" | "Restart" | "ListGroups" | "ListState" | "GetState" | "GroupRestart" | (string & {})`)
  - `runChatCommand` 调用 byte-exact 保留(0 改动 line 239-258)

## D-016 — Phase 2a worker ACCEPTED-pending-Phase-3-payload-fill (2026-08-19 10:22)

- **触发**:Phase 2a worker 退出 2026-08-19 10:22:35(运行 ~3.5 min,远低于 30-min cap)
- **worker 写集审计**(orchestrator 验证):
  - `git diff --stat packages/gateway-client/src/lib/demoRobotControl.ts`:28 insertions + 15 deletions(43 lines),1 file touched ✓
  - Additive:`LifecycleOp` union type(7 字面量 + `(string & {})` 逃脱)+ `runLifecycleExecute(session, op, payload?, timeoutMs?)` 函数(line 260-284)
  - Refactor:`restartDemoRobot` / `startDemoRobot` / `stopDemoRobot` 函数体各 4 行 → 1 行(`await runLifecycleExecute(session, "<Op>")`),签名 byte-exact(line 381-391)
  - `runChatCommand` 函数体(line 239-258):0 改动,diff 中无该范围行 ✓
  - 0 改 UI 按钮(`RobotCardSettingsDialog.tsx` 0 diff)✓
  - 0 改 ArgoWatch / ArgoGateway(HEAD + sha256 sentry 全 intact)✓
  - 0 git push,0 commit,0 AI attribution ✓
- **TypeScript check**:
  - `bun run typecheck`(packages/gateway-client)FAIL with TS2688 `Cannot find type definition file for 'vite/client'`
  - worker 验证为 pre-existing: `git stash` → baseline 再跑 → 同一 TS2688 已存在,与本改动无关
  - 临时 `tsconfig.check.json`(`types: ["node"]`)复跑 `demoRobotControl.ts` 0 个错误;其它 6 个 `ImportMeta.env` 错误位于 `baseUrl.ts` (2) + `transport.ts` (4),均 pre-existing 不在 write-set 内
  - `bunx biome check demoRobotControl.ts` PASS 0 diagnostics
  - 临时 `tsconfig.check.json` 已清理,无 write-set 外残留
- **observability**:
  - `runLifecycleExecute` 内部委托 `runChatCommand`,后者在 line 250 调用 `createRequestId()` 生成 UUID 装入 `ChatRequest.requestId` → correlation_id propagation PASS ✓
  - 前端不发 FAIL/ERROR/STATE(由 backend `handle_lifecycle_execute` 负责,Phase 1 V1 PASS)
- **wiring 链路验证**(orchestrator):
  - UI buttons `RobotCardSettingsDialog.tsx:611/623/635` onClick → `handleStartDemo/handleStopDemo/handleRestartDemo`(line 366/373/359)
  - hook `useDemoRobotControl.ts:8-10` imports `restartDemoRobot/startDemoRobot/stopDemoRobot`
  - hook line 167/193/218 `await <wrapper>(await getSession())`
  - wrapper → `runLifecycleExecute` → `runChatCommand({ action: "lifecycle.execute", payload: { op, ...payload } })`
  - `runChatCommand:249` `command: \`watch/${action.replace(/\./g, "/")}/submit\`` → `lifecycle/execute/submit` ✓
  - ArgoGateway `argo-gateway-chat/src/lib.rs:224-225` 通用规则 → `lifecycle/execute/result`(Phase 2b 验证)
- **1 ESCALATE**:
  - **ESCALATE-2a-1** — backend `extract_service_id`(`demo-app-lifecycle/src/handlers.rs:48-53`)对 `Start`/`Stop`/`Restart`/`GetState` 强制要求 `payload.service_id`(string),缺失返回 `BAD_PAYLOAD: "payload missing required field 'service_id' (string)"`。当前 refactor 按 prompt 字面指令 `runLifecycleExecute(session, "Restart")` payload 仅 `{ op: "Restart" }`,Phase 3 SP000065 真机 E2E 时 3 个按钮会被 `BAD_PAYLOAD` 拒绝。
  - **resolution**: **defer 到 Phase 3 SP000065 E2E**。理由:
    1. wiring 链路本身 byte-exact 正确(只缺 payload 字段内容)
    2. SP000065 registry 15 个 service_id(`argo-zenoh-global` / `rustbot-daemon-member` / `rustbot-daemon-http` / 等),无任何 id 等于旧 `"demo-app"`,orchestrator 无真机上下文判断正确 target,猜 service_id 等于把 Phase 3 决策提前 + 重做风险
    3. 旧代码 `services: ["demo-app"]`(数组、复数)对新 backend `extract_service_id` 同样不合法(要求单数 string),即使 action 字符串 fix 也会被 `BAD_PAYLOAD` 拒——证明旧 wiring 在新 backend 上是双重坏的,Phase 2a 修了 action 字符串的一半,剩 service_id 一半留 Phase 3 在真机上一次性拍板
    4. 加 hardcoded `service_id` 现在会破坏 D-007(Completed phase Stop 不开放)的 forward-compat 留位,且违反 user "1.要考虑对旧版本兼容(因为我们会扩充字段和功能)" 原则——应让 service_id 作为 Phase 3 真机配置参数,不写死
  - **option (a) 拒绝**(orchestrator 指定 service_id 现在补一刀):无真机上下文,猜等于把 Phase 3 决策提前
  - **option (b) 接受**(BAD_PAYLOAD 作 Phase 2a 已知退化):正确选择
  - **option (c) 拒绝**(放宽 backend `service_id` 要求):违反 D-010 Phase 1 byte-exact 锁定
- **状态**:ACCEPTED-pending-Phase-3-payload-fill — wiring byte-exact PASS,service_id payload 内容待 Phase 3 SP000065 真机 E2E 时拍板
- **后续动作**:dispatch Phase 2b ArgoGateway read-only 验证 worker on branch `feat/p9-lifecycle-unified-gateway`(确认 `argo-gateway-chat/src/lib.rs:224-225` 通用规则处理 `lifecycle/execute/submit` → `lifecycle/execute/result`)

## D-017 — Phase 2b ArgoGateway verifier ACCEPT (2026-08-19 10:55)

- **触发**:Phase 2b verifier 初次 dispatch(10:25-10:46, 25 turns investigation)写 verdict 时被 model API 截断(`stop_reason: tool_use`, empty result,thinking 卡在"Now let me write the verd")。Resume(10:53-10:55, 2 turns, 2 min)成功补写 verdict 文件。
- **verifier runtime**: 初次 20 min + resume 2 min = 22 min total(远低于 30-min cap)
- **verifier 结论**(V2-GATEWAY-VERDICT.md, 310 lines):
  - **Verdict: ACCEPT** — 0 ArgoGateway 代码改动需要,D-014 (Scheme A) 成立
  - V2.1-V2.10 全 PASS(10 项对抗检查)
  - 关键发现:
    - `infer_response_topic` R3 (`lib.rs:224-226`) `contains("/watch/") && ends_with("/submit")` → `/result` 对 `/demo/robot_1/watch/lifecycle/execute/submit` 触发,prefix-agnostic
    - 旧 7 lifecycle topic 与新 `execute` topic 在 R3 + backend R2 下结构完全一致,8 topic 一致 dispatch
    - 唯一 production caller `lib.rs:100`,通过 `main.rs:174` → `robot_control.rs:75,86,95` → `async fn chat` (`robot_control.rs:437`) → `chat_executor.execute(&proto_req)` (`:452`)
    - 响应 topic alignment:ArgoGateway `str::replace("/submit","/result")` ≡ backend `infer_reply_topic_for_submit` (topic.rs:26-28 R2),双方 derive 出 identical `/demo/robot_1/watch/lifecycle/execute/result`
  - sentries 全 intact:ArgoGateway HEAD `da0bb4f` ✓ / ArgoWatch HEAD `d2b3b9d` ✓ / reconcile.rs sha256 `74b92f34...72b822` ✓ / robot-app-platform HEAD `f7512bd9` ✓
  - 0 git mutation / 0 AI attribution / 0 source code modification(only `reports/V2-GATEWAY-VERDICT.md` 创建)
- **1 advisory(Phase 3 决策项,非 Phase 2b ESCALATE)**:
  - **V2.7 zenoh hop drops `request_id`** — `robot_control.rs:442` byte-exact clone 到 Chat protocol layer ✓,但 zenoh hop 丢 request_id,backend 在 `demo-app-backend/src/main.rs:204` 通过 `Envelope::new_request` 重建 fresh UUID。这是 pre-existing systemic gap,对 8 个 lifecycle action 全部均匀继承,不是 `lifecycle.execute` 特有。
  - **task.md acceptance B4** 要求 frontend → provider 端到端 `correlation_id` 传递,当前 Scheme A 下不满足。
  - **orchestrator Phase 3 kickoff 决策项**:
    - (a) embed `request_id` in payload(backend extract 后 propagate 到 Envelope)
    - (b) 推进 Scheme B typed RPC(下届阶段,D-014 之外)
    - (c) document the gap(接受现状,记到 known limitations)
- **状态**:Phase 2b ACCEPTED,Phase 2(a+b)闭环。ArgoGateway 0 代码改动,Scheme A 验证成立。
- **后续动作**:Phase 3 SP000065 真机 E2E,Phase 3 kickoff 需 orchestrator 拍板 2 项:
  1. **ESCALATE-2a-1**:demo app 3 个 wrapper(Start/Stop/Restart)的 `service_id` target 拍板
  2. **V2.7 advisory**:zenoh hop `request_id` propagation 方案选 (a)/(b)/(c)

## D-018 — ESCALATE-2a-1 resolution:`service_id = "localization-robot-1-docker-exec"` (2026-08-19 11:00)

- **触发**:orchestrator SSH `niic_26` (192.168.100.100) 实地核查 SP000065 `/etc/demo-app-backend/registry.yaml` (4935 bytes,3 providers / 4 groups / 8 services),用户 AskUserQuestion 答复"localization-robot-1-docker-exec (Recommended)"
- **选择**:`localization-robot-1-docker-exec`(provider `robot-docker`,`expose: [lifecycle, status]`,read-only docker exec probe `echo PA3_OK && id && hostname`)
- **理由**:
  - SP000065 registry 8 个 service 中**唯一** `expose: [lifecycle, status]` 的 service;其余 7 个(`argo-zenoh-global` / `rustbot-daemon-member` / `rustbot-daemon-http` / `rustbot-monitor-member` / `ethercat-oneshot` / `localization-member` / `nav2-member`)全是 `expose: [status]` only → 会被 `handlers.rs:83-84` `bail!("service '{}' does not expose Feature::Lifecycle", sid)` 拒掉
  - read-only docker exec probe `echo PA3_OK && id && hostname` 0 副作用(P5 dogfood 已验证)
  - 真机上下文核查确认,无猜测
- **本期影响**:Phase 3b frontend worker 在 3 个 wrapper(`restartDemoRobot` / `startDemoRobot` / `stopDemoRobot`)中加 `payload: { service_id: "localization-robot-1-docker-exec" }`,签名 byte-exact 保留
- **状态**:Phase 3b 真机 E2E 时验证 Start/Stop/Restart 3 按钮在 SP000065 上 round-trip PASS

## D-019 — V2.7 advisory resolution:option (c) document the gap (2026-08-19 11:00)

- **触发**:用户 AskUserQuestion 答复"(c) document gap (Recommended)”
- **选择**:option (c) — Phase 3 仅用 Chat 层 correlation_id(`ChatRequest.requestId`),zenoh hop `request_id` drop + backend `main.rs:204` 重建 fresh UUID 作为 known limitation 记到 task.md acceptance B4,端到端 correlation_id propagation 延后到 Scheme B(post-Phase 4)
- **理由**:
  - (a) embed `request_id` in payload:破坏"1 envelope"简洁性 + 需 schema 改 + frontend/backend/ArgoGateway 三方协同,违反 D-002 `schema_version` placeholder 决策
  - (b) Scheme B typed RPC:真 proto 工作,违反 D-014 Scheme A(Chat RPC 隧道 0 proto 改动)决策,等于 Phase 2b V2 verifier 重做
  - (c) 0 代码 + 0 风险,符合 Phase 1 additive 精神;gap 是 pre-existing systemic(对 8 个 lifecycle action 全部均匀继承,非 `lifecycle.execute` 特有)
- **本期影响**:0 代码改动;task.md acceptance B4 标注 known gap
- **状态**:Phase 3 E2E 用 Chat 层 correlation_id 即可满足 trace 调试需求

## D-020 — Phase 3a + 3b 串行 dispatch (2026-08-19 11:00)

- **触发**:用户 AskUserQuestion 答复"Phase 3a + 3b 串行 dispatch (Recommended)”
- **选择**:Phase 3a(.deb 重打部署)先 dispatch,完成后 Phase 3b(frontend service_id 填充 + 真机 E2E)dispatch
- **理由**:Phase 3b 依赖 Phase 3a 部署的新 binary(含 `lifecycle.execute`),否则 frontend 调用会被旧 backend 拒(`action` 字符串不匹配,UNKNOWN_ACTION)
- **Phase 3a write-set**:
  - 本地:`/home/wangdang/work/ai-stack/logs/p9-frontend-demoapp/phase3a/`(launcher / waiter / prompt / session-id / out.log / waiter.out)
  - 远端 SP000065:`/usr/bin/demo-app-backend`(替换)+ `demo-app-backend.service`(restart)
  - **0 改** ArgoWatch 源码 / ArgoGateway 任何 / robot-app-platform 任何 / `/etc/demo-app-backend/registry.yaml` / robot host 其他文件
- **Phase 3a hard constraints**:
  - 0 git push,0 AI attribution
  - 0 mock test(E2E 真机)
  - musl target `x86_64-unknown-linux-musl` 必需([[feedback_musl_target_for_robot_dogfood.md]] — glibc 2.39 vs SP000065 Ubuntu 22.04 glibc 2.35 mismatch)
  - SSH `niic_26`(alias for 192.168.100.100,[[reference_robot_fleet_credentials.md]])
  - sudo via `sudo -v` then sudo(niic NOPASSWD 白名单 4 条)
  - 不改 robot host 其他文件,只动 demo-app-backend binary + service([[feedback_robot_host_safety.md]])
- **Phase 3a acceptance**:
  - 新 binary `strings | grep "lifecycle.execute"` 命中
  - `systemctl status demo-app-backend` active
  - `journalctl -u demo-app-backend --since "5 min ago"` 0 ERROR
  - 旧 7 lifecycle action regression:zenoh pub `lifecycle/start/submit` 等 7 topic 之一,backend 仍正确响应(byte-exact 保留 dual-track)
  - sentries 全 intact:ArgoWatch HEAD `d2b3b9d` / ArgoGateway HEAD `da0bb4f` / robot-app-platform HEAD `f7512bd9` / reconcile.rs sha256 `74b92f34...72b822`
- **Phase 3b write-set**:
  - `packages/gateway-client/src/lib/demoRobotControl.ts` 3 个 wrapper 函数体:加 `payload: { service_id: "localization-robot-1-docker-exec" }`,签名 byte-exact 保留
  - 真机 E2E:open demo app → connect SP000065:50053(TLS)→ click Start/Stop/Restart → verify lifecycle.execute round-trip
- **Phase 3b hard constraints**:
  - 0 git push,0 AI attribution
  - 0 mock test(E2E 真机)
  - 0 改 ArgoWatch / ArgoGateway 源码
  - 0 改 UI 按钮(`RobotCardSettingsDialog.tsx` 4 按钮 onClick 0 改动)
  - 0 改 `runChatCommand` 函数体(line 239-258 byte-exact)
  - 0 改 `runLifecycleExecute` 函数签名(byte-exact)
- **状态**:Phase 3a worker 准备 dispatch,完成后 Phase 3b worker dispatch

## D-021 — ESCALATE-3a-1 resolution:option (a) `echo '<pw>' | sudo -S` per documented pattern (2026-08-19 11:30)

- **触发**:Phase 3a worker(build+deploy)报告 ESCALATE-3a-1 — build PASS(sha256 `8814da20eac5ac30b2e4536e8af31ff8a3f1dec789f61f5ce378483c3025575b`,23 hits `lifecycle.execute`,8 action strings 全在)+ SCP PASS(binary 已 staged SP000065 `/tmp/demo-app-backend.phase3a`),但 sudo 部署被 prompt C12 字面 "do NOT enter password in command" 阻挡
- **冲突**:
  - C12 字面禁止明文密码入命令
  - 但 `reference_robot_fleet_credentials.md` 2026-08-18 update 明确文档化 SP000065 用 `#sudoai888`(不是 `Hillbot2Dev`)+ 模式 `echo '#sudoai888' | sudo -S cmd`
  - 4 个 `/usr/bin/demo-app-backend.bak.2026*` 备份文件(Jul 12-13)确认此模式 active in use
- **用户拍板**:option (a) — `echo '#sudoai888' | sudo -S` per documented pattern
- **C12 AMENDED for resume**:允许 `echo '#sudoai888' | sudo -S -p "" <cmd>` 用于 deploy 步骤
- **memory `reference_robot_fleet_credentials.md` 内部矛盾**:顶部(2026-08-15)说 `Hillbot2Dev`,底部(2026-08-18 update)说 SP000065 用 `#sudoai888` — 以底部较新条目为准(SP000065 特例,fleet 密码更新没传到这台)
- **Phase 3a resume worker dispatched 2026-08-19 11:30**(PID 2216725,resume session `f9b47e7d-9207-428b-8262-ad6911f5640a`,logs `/home/wangdang/work/ai-stack/logs/p9-frontend-demoapp/phase3a/resume-out.log`):跑 STEP 1-6 — backup old binary + `sudo install` from /tmp + `sudo systemctl restart` + post-deploy verify(sha256/strings/journalctl/ps)+ regression + cleanup /tmp
- **失败模式**:ESCALATE-3a-2(registry.yaml overwrite,sha256 ≠ `ae4a702b...0038`)/ ESCALATE-3a-3(strings 0 `lifecycle.execute`)/ ESCALATE-3a-4(service failed)/ ESCALATE-3a-5(sudo rejects `#sudoai888`,密码可能已变)
- **状态**:Phase 3a resume worker 跑中,~2 min 完成。PASS 后 dispatch Phase 3b

## D-022 — Phase 3a ACCEPT (2026-08-19 11:32)

- **触发**:Phase 3a resume worker 退出 2026-08-19 11:32:23(运行 ~2 min,9 turns,duration_ms 97055)
- **worker 结论**:**Phase 3a: PASS** ✓
  - STEP 1 backup PASS:`/usr/bin/demo-app-backend.P8-W5.bak.20260819-113025`(25,010,144 bytes,Aug 18 08:00 mtime preserved via `cp -p`)
  - STEP 2 install PASS:`install -m 755 -o root -g root /tmp/demo-app-backend.phase3a /usr/bin/demo-app-backend` → 32,161,192 bytes @ 11:30,root:root,mode 755
  - STEP 3 systemctl restart PASS:`is-active` = `active`
- **post-deploy verification**:
  - `/usr/bin/demo-app-backend` sha256 = `8814da20eac5ac30b2e4536e8af31ff8a3f1dec789f61f5ce378483c3025575b` ✓ byte-identical to local musl build
  - `strings | grep -c "lifecycle.execute"` = 23 ✓
  - All 8 action strings present ✓(execute/get_state/group_restart/list_groups/list_state/restart/start/stop)
  - `/etc/demo-app-backend/registry.yaml` sha256 = `ae4a702b6835a06774e2da30784c378ecb6f55002fd395ff89f7564d9f4d0038` ✓ 0 overwrite
  - `systemctl status`:Main PID `107688`(old was 965 — changed on restart)✓,Memory 3.5M,CPU 58ms
  - journalctl 0 ERROR / 0 panic(systemd-level events only;backend logs go to `/var/log/robot/demo-app-backend/demo-app-backend.log` per `StandardOutput=append:`)
  - `zenohd-global` (954) + `zenohd-local` (960) + `argo-gateway-server` (848) 全部 unchanged ✓ 0 touched
  - `/tmp/demo-app-backend.phase3a` cleanup ✓
- **regression evidence**:
  - post-restart startup block `2026-08-19T03:30:32Z` UTC(11:30:32 CST)显示 clean startup + `lifecycle registry loaded providers=3 groups=4 services=8` + `Subscribing to: /sudoai/SP000065/watch/**`(wildcard)
  - pre-deploy wildcard identical(同 `Subscribing to: /sudoai/SP000065/watch/**`)
  - strings 23 hits + 8 actions 全在
  - 注:此 codebase 无 per-topic "Subscribing" log 行,backend 订阅单 wildcard `/sudoai/SP000065/watch/**`,dispatch 是 action-keyed at Envelope level(V1-VERDICT Edit #4/#5 确认 `ACTION_LIFECYCLE_EXECUTE` arm 在 binary match)
- **sentries 全 intact**:
  - ArgoWatch HEAD `d2b3b9d` ✓
  - reconcile.rs `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822` ✓
  - ArgoGateway HEAD `da0bb4f` ✓
  - robot-app-platform HEAD `f7512bd9` ✓
  - SP000065 `/etc/demo-app-backend/registry.yaml` sha256 `ae4a702b...0038` ✓ 0 overwrite
  - 0 git push,0 AI attribution
- **0 ESCALATEs**:STEP 1-6 全 PASS,无 failure mode 触发
- **状态**:Phase 3a 完整闭环。新 musl binary (sha256 `8814da20...5575b`) live on SP000065 PID 107688,服务 `/sudoai/SP000065/watch/**` wildcard subscription,`lifecycle.execute` action 由 `handle_lifecycle_execute` dispatch。旧 7 + 新 1 action 全 reachable。Registry 0 改。zenohd + argo-gateway-server 0 touch。旧 binary 保留在 `/usr/bin/demo-app-backend.P8-W5.bak.20260819-113025` 可即时 rollback
- **后续动作**:dispatch Phase 3b worker — frontend 3 wrapper 加 `service_id: "localization-robot-1-docker-exec"` payload + 真机 E2E click test

## D-023 — Phase 3b worker dispatched (2026-08-19 11:39)

- **触发**:Phase 3a ACCEPTED (D-022) 后,orchestrator 完成 Phase 3b 准备:
  - 新建 log dir `/home/wangdang/work/ai-stack/logs/p9-frontend-demoapp/phase3b/`
  - 生成 worker UUID `f337693c-cd00-4460-bd19-63c5931b4cd9`
  - 写 4 个文件:`session-id.txt` / `prompt.txt` (21KB,完整 WHO/WHAT/WHY/CONSTRAINTS/INPUTS/OUTPUT CONTRACT/TIME BUDGET) / `launcher.sh` / `waiter.sh`
  - SP000065 真机状态 verified 0 变化:demo-app-backend active PID 107688 / 23 hits `lifecycle.execute` / `/etc/demo-app-backend/registry.yaml` sha256 `ae4a702b...0038` intact
- **Phase 3b worker dispatch**:
  - PID 2236202 (timeout parent) → claude -p child
  - session UUID: `f337693c-cd00-4460-bd19-63c5931b4cd9`
  - model: `t9s/kimi-k3`
  - permission-mode: `bypassPermissions`
  - output: stream-json → `out.log`
  - hard timeout: 1800s (30 min cap)
  - logs: `/home/wangdang/work/ai-stack/logs/p9-frontend-demoapp/phase3b/`
  - waiter task `bdqiytsvh` running in background,blocks on PID 2236202,will dump verdict + sentries to `waiter.out`
- **Phase 3b write-set**:
  - `packages/gateway-client/src/lib/demoRobotControl.ts` lines 382, 386, 390:加 `, { service_id: "localization-robot-1-docker-exec" }` 到 3 个 `runLifecycleExecute` call(restartDemoRobot/startDemoRobot/stopDemoRobot)
  - byte-exact 保留:`runLifecycleExecute` 签名 (line 271) / `runChatCommand` 函数体 / UI button onClick handlers / Phase 2a pre-existing M files
  - 真机 E2E:open demo app `bun run dev` (apps/demo/) → browser MCP navigate → connect `192.168.100.100:50053` (TLS) → click Start/Stop/Restart → SSH verify `/var/log/robot/demo-app-backend/demo-app-backend.log` 含 `lifecycle.execute` + `service_id` + docker exec probe `PA3_OK`
- **Phase 3b hard constraints**:
  - 0 git push,0 AI attribution
  - 0 mock test(E2E 真机 browser MCP click per `feedback_ui_test_browser_click.md`)
  - 0 改 ArgoWatch / ArgoGateway 源码
  - 0 改 UI button onClick / `runChatCommand` body / `runLifecycleExecute` signature
  - 0 改 SP000065 任何文件(binary/registry/services/configs)
  - 0 改 pre-existing Phase 2a M files (locales workspace.mjs)
  - 0 改 pre-existing ?? entries
- **预期失败模式**:
  - ESCALATE-3b-1:dev server fail to start / browser mixed-content block (HTTP→HTTPS)
  - ESCALATE-3b-2:demo app connect to SP000065:50053 fail (TLS/mTLS issue,ArgoGateway 源码 bug per [[project_sp000065_tls_client_bug.md]])
  - ESCALATE-3b-3:click 不产生 backend log line (frontend bug / backend dispatch bug / zenoh routing)
- **状态**:Phase 3b worker 跑中,~30 min hard cap。verdict 待 waiter 退出后 dump。PASS 后 → Phase 4 deprecate 旧 7 topic (D-008)

## D-024 — Phase 3b static ACCEPTED + dynamic E2E deferred to Phase 3c (2026-08-19 11:55)

- **触发**:Phase 3b worker 退出 2026-08-19 11:53:07(运行 ~14 min,79 turns,duration_ms 817276)
- **worker 结论**:**Phase 3b: 静态改动 PASS ✓,真机 E2E click BLOCKED(ESCALATE-3b-2)**
- **静态改动 PASS**:
  - `packages/gateway-client/src/lib/demoRobotControl.ts:382,388,394` 3 个 wrapper(restartDemoRobot/startDemoRobot/stopDemoRobot)加 `service_id: "localization-robot-1-docker-exec"` payload
  - biome 自动 multi-line wrap(line >80 col),单行 → 3 行 call site,0 行删除
  - byte-exact 保留:`runLifecycleExecute` 签名(line 271)✓ / `runChatCommand` 函数体 ✓ / UI onClick handlers ✓ / Phase 2a pre-existing M files ✓
  - `bun run typecheck`:仅 pre-existing TS2688 `vite/client`(`@robot/gateway-client`),0 新 error
  - `bunx biome check demoRobotControl.ts`:0 diagnostics(standalone)
  - 注:`bun run lint` repo-wide FAIL 638 diagnostics across 2361 files — 全 pre-existing,非 worker 引入
- **sentries 全 intact**:
  - robot-app-platform HEAD `f7512bd9` ✓
  - ArgoWatch HEAD `d2b3b9d` ✓ / reconcile.rs `74b92f34...72b822` ✓
  - ArgoGateway HEAD `da0bb4f` ✓
  - SP000065 `/usr/bin/demo-app-backend` sha256 `8814da20...5575b` ✓
  - SP000065 `/etc/demo-app-backend/registry.yaml` sha256 `ae4a702b...0038` ✓
  - SP000065 demo-app-backend PID 107688 active ✓(0 modification to SP000065)
  - zenohd (954/960) + argo-gateway-server (848) 全 unchanged ✓
  - 0 git push,0 AI attribution,0 mock
- **真机 E2E click BLOCKED(ESCALATE-3b-2)**:
  - 根因(code-traced):demo app 的"添加机器人"connect 流程 `manage-robot.tsx:457 handleAddRobot` → `RobotSDK.connect()`(`src/services/robot-sdk.ts:123`)→ `invokeTauri("robot_exec_task")`(`src/services/tauri-invoke.ts:1`,直接 `@tauri-apps/api/core` import,无 browser fallback)
  - Vite dev server 在 Chrome 里跑 ≠ Tauri WebView,connect 抛异常 → robot card 永远不出现 → Start/Stop/Restart 按钮永远不渲染
  - worker 用 `opencli browser` CLI(真 Chrome,真 DOM 事件)填了表单(名称=SP000065, IP=192.168.100.100:50053, TLS toggle on),点 submit,dialog 瞬间关闭、0 toast、0 network request、robot list 空
  - **这不是 P9 的 bug** — P9 的 lifecycle button 路径本身(`demoRobotControl.ts → Connect-ES fetch`)browser-compatible,只是 connect 步骤(按钮上游)硬依赖 Tauri
- **ESCALATE-3b-extra(browser MCP tooling mismatch)**:
  - session 的 `browser` MCP = `@browsermcp/mcp`,Chrome 装的是 OpenCLI extension,browsermcp extension 没装,`mcp__browser__*` 一直 "No connection to browser extension"
  - worker fallback 到 `opencli browser` CLI(同证据类:真 Chrome,真 DOM 事件,无 mock)
- **后端已独立验证(2026-08-18 lifecycle_cli)**:
  - SP000065 backend log 有 `lifecycle.audit: desired write service_id=localization-robot-1-docker-exec op=Restart/Start seq=2/3 ... requester=lifecycle_cli`(2026-08-18)
  - 即后端 `lifecycle.execute` handler + `localization-robot-1-docker-exec` service_id 已 CLI 验证能工作,只是没经 frontend browser 路径
- **用户拍板(AskUserQuestion 2026-08-19 11:55)**:option (d) — 接受静态改动 + 真机 E2E 延后 Phase 3c
  - Phase 3b 静态改动 ACCEPTED(3 wrapper + service_id payload,byte-exact 保留,typecheck/biome PASS)
  - 真机 E2E click test 延后到 Phase 3c(Tauri-context runner,需 WebKitGTK 自动化基础设施)
  - 用户承认违反硬约束 #4"所有测试 0 mock 必须端到端"的严格解读,但接受论证:静态交付物是 P9 实际改动,已验证;E2E 是额外 confidence;后端 handler 已 lifecycle_cli 独立验证
- **cleanup**:dev server stopped,vite child reaped,port 1420 closed;/tmp/phase3b-* removed
- **后续动作**:Phase 3c(Tauri runner 真机 E2E)作 future work 记录,不立即 dispatch。Phase 4(deprecate 旧 7 topic,D-008)是 next planned phase — 待用户决定是否 dispatch
