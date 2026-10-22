# P9 Lifecycle Unified API Implementation — evaluation

## Phase 1 acceptance(本期 worker 自检 + V1 verifier 对抗审计)

### Build & test

- E1.1 `cargo build -p demo-app-backend -p demo-app-lifecycle` 0 warning 0 error
- E1.2 `cargo test  -p demo-app-backend -p demo-app-lifecycle` 0 fail
- E1.3 `cargo clippy -p demo-app-backend -p demo-app-lifecycle` 0 warning(若 worker 习惯跑)
- E1.4 任何新增测试必须真连 zenoh + 真 lifecycle registry,**0 mock**(用户硬约束 #4)

### Git + sha256 sentry

- E2.1 `git -C code/ArgoWatch log --oneline -1` = `d2b3b9d`(未 commit / 未 push)
- E2.2 `git -C code/ArgoWatch status --short` 仅显示本期 write-set 内文件
- E2.3 `sha256sum code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/src/reconcile.rs` = `74b92f34...72b822`
- E2.4 `git -C code/ArgoWatch log --since="1 day ago" --oneline` 无新 commit(0 git ops)

### Additive byte-exact(旧 7 路径不破坏)

- E3.1 旧 7 action 常量 `lifecycle.list_groups` / `list_state` / `get_state` / `start` / `stop` / `restart` / `group_restart` byte-exact 保留
- E3.2 旧 7 topic 订阅 `lifecycle/<verb>/submit` byte-exact 保留
- E3.3 旧 7 handler 函数体 byte-exact 保留(只允新增不允改)
- E3.4 `dispatch_action` 旧 7 match arm byte-exact 保留,只新增 `lifecycle.execute` arm

### 新统一路径

- E4.1 新 action `lifecycle.execute` 常量存在
- E4.2 新 topic `lifecycle/execute/submit` 订阅存在
- E4.3 `handle_lifecycle_execute` 函数存在,且 dispatch 9 个 op:
  - ListGroups / ListState / GetState / Start / Stop / Restart / GroupStart / GroupStop / GroupRestart
  - CustomOp escape hatch(`x-*` 前缀)
- E4.4 9 个 op 全部复用现有 handler 函数,不重写业务逻辑
- E4.5 未知 op 返回 `UNKNOWN_OP`(或现有等价 error code),不 panic

### Observability(8 verifier checks,evidence.md 对抗)

- E5.1 **log presence**:每条 FAIL/ERROR/STATE 事件都有日志行
- E5.2 **correlation correctness**:`correlation_id` 从 request.id 传到 response.ref_id,跨 handler 传播
- E5.3 **identity correctness**:`service` + `instance_id` 字段非空且正确
- E5.4 **failure semantics**:FAIL = caller→callee 一次失败;ERROR = 内部异常;STATE = 状态变迁;不混用
- E5.5 **retry semantics**:`attempt` 字段在 retry 路径递增,首次 = 0 或 1(与 events.md 一致)
- E5.6 **cause preservation**:error_message 包含 cause 链(`{e:#}` 不 `format!("{}", e)`)
- E5.7 **first-failure reconstruction**:首失败可见,downstream_failures 不掩盖 first_failure
- E5.8 **scope completeness**:所有 9 个 op + error path + happy path 都有日志覆盖

### 硬约束(用户 4 条)

- E6.1 0 mock test(所有新增测试真连 zenoh + 真 lifecycle registry)
- E6.2 0 git push / 0 AI attribution
- E6.3 0 跨 write-set 修改(reconcile.rs / robot-app-platform / ArgoGateway proto 全不动)
- E6.4 严格遵循 bootstrap.md 工作方式(worker-preamble 已 prepend,worker 非交互,open judgment → ESCALATE)

## Phase 3 acceptance(后续阶段,真机 E2E,本期不执行)

### Deploy + E2E on SP000065(192.168.100.100)

- F1. Phase 1 产物(.deb 或 cargo install)deploy 到 SP000065 PASS
- F2. 7/7 ops 通过新 `lifecycle.execute` 通路在 SP000065 真机执行 PASS(无 mock):
  - list_groups / list_state / get_state / start / stop / restart / group_restart
- F3. `INVALID_INTENT` 错误 byte-exact 与旧路径一致(message 模板见 DESIGN.md §2.3)
- F4. `MISSING_FEATURE` 错误 byte-exact 与旧路径一致
- F5. `UNKNOWN_SERVICE` 错误 byte-exact 与旧路径一致
- F6. `localization-robot-1-docker-exec` 服务(唯一 expose `[lifecycle, status]` + docker exec,0 副作用)作为安全 E2E 靶标

### 端到端链路(Frontend → ArgoGateway → ArgoDDS → demo-app-backend)

- F7. `correlation_id` 从 frontend → ArgoGateway → zenoh → demo-app-backend → provider 全链路传递
- F8. `run_id` 经 env `GAWAIN_RUN_ID` 注入,所有 FAIL/ERROR 事件可重建 first-failure
- F9. 旧 7 topic 在新 `lifecycle.execute` 上线后仍能用(dual-track 验证)
- F10. 9 个 op + CustomOp escape hatch 在 SP000065 真机 E2E PASS

## Verifier dispatch rule(orchestrator 用)

- Phase 1 完成后:dispatch V1 verifier,adversarial mandate = "用 evidence.md 8 check 对抗审计 Phase 1 worker 产物,**优先寻找反例**,找不到反例才 ACCEPT"
- Phase 1 worker 自检 PASS ≠ V1 ACCEPT;V1 PASS 才进 Phase 2
- Verifier worker 必须读 `code/Gawain/workflow/agentflow/observability/evidence.md` 全文
- Verifier worker write-set:仅 `reports/V1-VERDICT.md`,0 src 修改
