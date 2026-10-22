# PROMPT-W2 — demo-app-backend ↔ demo-app-lifecycle integration Scheme A implementation (glm-5.2)

```
Before doing anything else:
1. Read /home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's classifier and follow every rule
   that applies. Q4=YES (cross-boundary zenoh integration) → 必读
   agentflow/observability/{README,context,events,propagation}.md。
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly 7 files (all under demo-app-backend/ except
   the new report under demo-app-lifecycle/reports/):
   - crates/demo-app-backend/Cargo.toml          (MODIFY: +1 dep line)
   - crates/demo-app-backend/src/config.rs       (MODIFY: +6 registry_yaml)
   - crates/demo-app-backend/src/main.rs         (MODIFY: +35 Runtime asm + spawn)
   - crates/demo-app-backend/src/handlers.rs     (MODIFY: +40 lifecycle.* arm / −260 删 7 docker fns)
   - crates/demo-app-backend/debian/demo-app-backend.service  (MODIFY: +1 Environment=REGISTRY_YAML)
   - crates/demo-app-backend/debian/registry-robot.yaml       (NEW: ~100 LoC, port from demo-app-lifecycle/examples/registry-sp000065.yaml)
   - crates/demo-app-lifecycle/reports/P8-INTEGRATION-IMPLEMENTATION.md  (NEW: impl report)
   Report every file created/modified with line numbers in your final message.
   ANY file outside this list = contract violation.

HEAD-guard: before any git touchpoint, run `git log --oneline -1 && git status --short`.
HEAD MUST remain `d2b3b9d`. NEVER `git add` / `git commit` / `git push`. NEVER AI attribution.

model_selection:
  model: t9s/glm-5.2
  mode: automatic
  reason: large_refactoring  # +40/-260 LoC cross-crate integration + musl build + ESCALATE self-resolution
```

---

You are **W2 of demo-app-backend ↔ demo-app-lifecycle integration** — **implementation worker** executing **Scheme A (in-process lib integration)** per W1 research verdict。

W1 (session `5d30ea8c-eab4-4674-a6e2-028df872bdcd`) 已完成 research,3 用户假设全 PASS,推荐方案 A。用户拍板 (D-122, 2026-08-18):**Scheme A + 4 关键 ESCALATE 由 W2 实现时一并处理**。

## CRITICAL: 30-MIN HARD CAP + NO PARTIAL RETURNS

- **Hard time cap: 30 min wall clock** (`timeout -k 5 1800s`)。到点必停,partial 状态作为 final message 交付。
- **禁止**返回 plan / outline / status update / "next I'll ..."。Work continuously 直到 7 个 deliverable 文件写完 + final message 交付。
- **0 git push / 0 git commit / 0 git add / 0 AI attribution**。
- **0 改动 demo-app-lifecycle/src/*** — lifecycle 全已 pub,W1 §6 验证。本 task 严格 0 改 lifecycle crate src/。
- **0 改动 demo-app-lifecycle/examples/lifecycle_cli.rs** — P7b 已 uncommitted 修改,W2 不碰。
- **NEVER modify SP000065 host 文件 / services** — 本 task 不涉及 SSH / 真机。

## Pre-known facts (inline, do not re-verify — from W1 report)

### demo-app-backend 现状(已 read by W1)
- crate path: `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-backend/`
- src 文件 + 行数: `config.rs` 74L / `envelope.rs` 104L / `handlers.rs` 674L / `main.rs` 140L / `topic.rs` 89L (total 1081L)
- Cargo.toml deps: `argo-dds / demo-app-types / anyhow / base64 / chrono / futures / serde / serde_json / tokio / tracing / tracing-subscriber / uuid` (**NO `demo-app-lifecycle` dep**)
- `main.rs:40` `#[tokio::main]`, `main.rs:70` subscribe `/{f}/{b}/watch/**` wildcard, loop `main.rs:79-137` parses Envelope → `handlers::dispatch_action` → reply
- `handlers.rs:656-674` `dispatch_action` matches 10 actions: `restart_service / start_service / stop_service / logs.collect / ping / echo / status / query_device / robot.status / robot.operational`
- 7 个硬编码 docker fns in handlers.rs (delete targets per Scheme A):
  - `restart_container` (handlers.rs:50-138)
  - `exec_in_container` (handlers.rs:142-196)
  - `handle_start_service` (handlers.rs:200-232) **MISNOMER — 实调 restart_container**
  - `stop_container` (handlers.rs:259-331)
  - `query_robot_in_container` (handlers.rs:601-652)
  - `handle_restart_service` (handlers.rs:33-39 fire-and-forget wrapper)
  - `handle_stop_service` (handlers.rs:242-248 fire-and-forget wrapper)
  - `handle_logs_collect` (handlers.rs:335-499) — NOT docker (tar czf host log), **保留不动**
- debian dir: `demo-app-backend.service` (777B), `scripts/` 子目录

### demo-app-lifecycle 公共 API surface(已 read by W1)
- crate path: `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/`
- `lib.rs` pub 8 modules: `config / envelope / error / handlers / providers / runtime / spec / topic`
- `Runtime` struct + `boot_observe_into_states` + `observer_loop` + `converge_loop` 全 pub (`runtime/` mod)
- `handle_lifecycle_{start,stop,restart,get_state,list_state,list_groups,group_restart}` 全 pub (`handlers` mod)
- `spec::load(path)` + `Registry / ServiceSpec / GroupSpec / ProviderSpec / ProviderKind` (`spec` mod)
- `ProviderRegistry` + 4 providers (docker/systemd/process/http) (`providers` mod)
- daemon in-process entry 参照 `demo-app-lifecycle/src/main.rs:101-190` (40 LoC of Runtime assemble)
- examples 参考:
  - `demo-app-lifecycle/examples/registry-sp000065.yaml` — P5 dogfood yaml(真机 E2E ACCEPTED),作为 `debian/registry-robot.yaml` 起点
  - `demo-app-lifecycle/examples/registry-robot.yaml` — 通用 robot yaml(W2 可对照)
  - `demo-app-lifecycle/examples/lifecycle_cli.rs` — out-of-process client 模式(只读参考,NOT modify)

### W1 §6 推荐 Scheme A 改动表(verbatim, W2 执行 baseline)

| File | Change | LoC |
|---|---|---|
| `crates/demo-app-backend/Cargo.toml` | `+ demo-app-lifecycle = { path = "../demo-app-lifecycle" }` | +1 |
| `crates/demo-app-backend/src/config.rs` | `+ registry_yaml: String` field + env read (mirror lifecycle config.rs:61) | +6 |
| `crates/demo-app-backend/src/main.rs` | in `main()`: load registry, build providers + bound map, `Arc<Runtime>`, `boot_observe_into_states`, spawn `observer_loop` + `converge_loop`, pass `rt` into dispatch | +35 |
| `crates/demo-app-backend/src/handlers.rs` | `dispatch_action` 加 `lifecycle.*` arm calling `demo_app_lifecycle::handlers::*`; 删 7 个 docker fns (restart_container/exec_in_container/stop_container/handle_start_service/handle_restart_service/handle_stop_service/query_robot_in_container); **保留** `handle_logs_collect` (非 docker);net | −260 / +40 |
| `crates/demo-app-backend/src/topic.rs` | unchanged (lifecycle topic.rs 是 backend 的 byte-for-byte 副本) | 0 |
| `crates/demo-app-backend/src/envelope.rs` | unchanged — lifecycle 用同名 envelope field,backend 继续用自己 | 0 |
| `crates/demo-app-lifecycle/*` | **no change** | 0 |
| `crates/demo-app-backend/debian/demo-app-backend.service` | `+ Environment=REGISTRY_YAML=/etc/demo-app-backend/registry.yaml` | +1 |
| `crates/demo-app-backend/debian/registry-robot.yaml` (NEW) | port of `demo-app-lifecycle/examples/registry-sp000065.yaml`,作为 deb asset | ~100 |
| **Net** | | **+83 / −260 + 1 env + 1 yaml asset** |

### 4 关键 ESCALATE(W2 self-resolve,每个在 final message 给 verdict + evidence)

**ESCALATE #1 — Legacy callers 审计**:
- grep `restart_service|start_service|stop_service` (zenoh action string) across:
  - `/home/wangdang/work/ai-stack/code/ArgoWatch/` (本 repo)
  - `/home/wangdang/work/ai-stack/code/ArgoGateway/` (sibling)
  - `/home/wangdang/work/ai-stack/code/ArgoDeploy/` (sibling)
  - `/home/wangdang/work/ai-stack/code/argopilot/` (sibling)
  - `/home/wangdang/work/ai-stack/code/argopilottools/` (sibling)
  - `/home/wangdang/work/ai-stack/code/ArgoDDS/` (sibling)
- 找到 caller → 保留 3 个 legacy action names 作为 thin forwarder shim alias 到 `lifecycle.{restart,start,stop}` (但有 ESCALATE #2 语义冲突警告)
- 未找到 caller → 干脆 retire (delete),只保留 `lifecycle.*` actions
- final message 给出 caller 列表 + decision (alias vs retire) + evidence (grep output 截图)

**ESCALATE #2 — Misnomered `start_service` 语义 bug**:
- 现状 `handlers.rs:200-232` `handle_start_service` 实调 `restart_container` — start=restart 的 misnomer
- 若 ESCALATE #1 决定 retire:删 silently,无 alias
- 若 ESCALATE #1 决定保 alias:`start_service` 不能 1:1 alias 到 `lifecycle.start`(lifecycle op-legality 矩阵拒绝从 Running/Degraded 状态 start),只能 alias 到 `lifecycle.restart`(语义对齐现 misnomer 行为)— **在 alias 代码处加 comment 说明语义对齐选择**,记录在 P8-INTEGRATION-IMPLEMENTATION.md §ESCALATE-2

**ESCALATE #3 — Registry yaml scope**:
- 用 `demo-app-lifecycle/examples/registry-sp000065.yaml` 作起点,写 `debian/registry-robot.yaml`
- 包含的 service_ids(至少):`localization-robot-1-docker-exec` / `nav2-member` / `rustbot-daemon-member` / `rustbot-monitor-member` / `argo-zenoh-global` / `ethercat-oneshot` (P5 dogfood 已验证的 6+ svcs)
- Provider 分配:P5 dogfood 已 mix docker/http/systemd — 保持一致
- 加 `Groups` section (至少 `robot-stack` group,包含上述 svcs) — P7b 已验证 group_restart 跑通
- ship path: `debian/registry-robot.yaml` 作 deb asset,installed to `/etc/demo-app-backend/registry.yaml` (由 service 文件 env 指向)

**ESCALATE #4 — 优先级**:本 task = P8 standalone(不需 W2 决策,已定)

## Task (5 步)

### Step 1: 读 normative + 起草改动 (~3 min)

读:
- `workflow/bootstrap.md` (already via preamble)
- `workflow/agentflow/observability/{README,context,events,propagation}.md` (Q4 mandate)
- W1 report: `demo_app_service/crates/demo-app-lifecycle/reports/RESEARCH-DEMO-BACKEND-LIFECYCLE-INTEGRATION.md` (235L)
- `demo-app-lifecycle/src/main.rs:101-190` (in-process Runtime assemble 模板)
- `demo-app-lifecycle/src/lib.rs` (pub API surface)
- `demo-app-lifecycle/src/handlers.rs` (handle_lifecycle_* 签名)
- `demo-app-lifecycle/examples/registry-sp000065.yaml` (registry 起点)
- `demo-app-backend/src/{main,handlers,config}.rs` (修改目标)
- `demo-app-backend/Cargo.toml` (修改目标)
- `demo-app-backend/debian/demo-app-backend.service` (修改目标)

### Step 2: 执行 ESCALATE #1 legacy callers 审计 (~3 min)

grep 6 个 sibling repos (列出 above)。记录 caller 文件:行号 + action 串。

decision matrix:
- 0 caller → retire 3 个 legacy action names (delete dispatch arms + delete 7 docker fns)
- ≥1 caller → 保留 3 个 legacy action names 作 alias shim,删硬编码 docker impl 但 dispatch arm forward 到 `lifecycle.*`

### Step 3: 改 7 个 write-set 文件 (~15 min)

按 W1 §6 表 + ESCALATE #1/#2/#3 决策执行:

1. **Cargo.toml**: `[dependencies]` 段加 `demo-app-lifecycle = { path = "../demo-app-lifecycle" }`
2. **src/config.rs**: `Config` struct 加 `pub registry_yaml: String` field; `from_env` 加 `registry_yaml: env::var("REGISTRY_YAML").unwrap_or_else(|_| "/etc/demo-app-backend/registry.yaml".to_string())`(mirror lifecycle `config.rs:61`)
3. **src/main.rs**: in `main()`:
   - 加 `use demo_app_lifecycle::{spec, providers::*, runtime::*};`(or 按需)
   - 加 `let registry = spec::load(&PathBuf::from(&cfg.registry_yaml))?;`
   - 加 `let mut providers = ProviderRegistry::default();` + provider factory per `ProviderKind` (参照 `demo-app-lifecycle/src/main.rs:101-150` 40 LoC)
   - 加 `let mut bound = BTreeMap::new();` + bind loop per service
   - 加 `let (converge_tx, converge_rx) = mpsc::channel::<String>(64);`
   - 加 `let rt = Arc::new(Runtime { registry, bound, states: Arc::new(RwLock::new(BTreeMap::new())), converge_tx });`
   - 加 `boot_observe_into_states(&rt).await;`
   - 加 `tokio::spawn(observer_loop(rt.clone(), Duration::from_secs(3)));`
   - 加 `tokio::spawn(converge_loop(rt.clone(), converge_rx));`
   - 修改 `dispatch_action` call 传入 `rt` clone(签名改 `dispatch_action(req, &cfg, &rt).await`)
4. **src/handlers.rs**:
   - `dispatch_action` 签名加 `rt: &Arc<Runtime>` 参数
   - 加 `lifecycle.*` match arm (before `_ => UNKNOWN_ACTION`):`"lifecycle.start" | "lifecycle.stop" | "lifecycle.restart" | "lifecycle.get_state" | "lifecycle.list_state" | "lifecycle.list_groups" | "lifecycle.group_restart"` → call 对应 `demo_app_lifecycle::handlers::handle_lifecycle_*(&rt, &envelope).await`
   - 若 ESCALATE #1 = retire:删 `restart_service|start_service|stop_service` match arms + 删 7 个 docker fns
   - 若 ESCALATE #1 = alias:保留 3 个 match arms,改 forward 到 `lifecycle.restart|start|stop`(注意 ESCALATE #2 `start_service` alias 到 `lifecycle.restart`),删 7 个硬编码 docker fns
   - **保留** `handle_logs_collect` (非 docker) + `query_robot_in_container` (若 caller 仍用)— 注意 `query_robot_in_container` 是 docker exec,W1 列入 delete targets,但若 ESCALATE #1 找到 caller 需 forward 到 `lifecycle.get_state` 或保留(若 query_device action 仍 caller 用)
5. **debian/demo-app-backend.service**: `[Service]` 段加 `Environment=REGISTRY_YAML=/etc/demo-app-backend/registry.yaml`
6. **debian/registry-robot.yaml** (NEW): port `registry-sp000065.yaml` 内容,确保包含 6+ service_ids + `robot-stack` group
7. **reports/P8-INTEGRATION-IMPLEMENTATION.md** (NEW): impl report — 见 Step 5

### Step 4: 编译 + musl build 验证 (~5 min)

```bash
cd /home/wangdang/work/ai-stack/code/ArgoWatch
cargo check -p demo-app-backend 2>&1 | tail -30
cargo build -p demo-app-backend 2>&1 | tail -30
# musl build (W1 ESCALATE #7 — 关键验证点)
cargo build --target x86_64-unknown-linux-musl -p demo-app-backend 2>&1 | tail -50
# clippy (best-effort, 不阻塞)
cargo clippy -p demo-app-backend --no-deps 2>&1 | tail -30
```

记录每个 build 的 exit code + 关键 warning/error。**musl build 失败要 ESCALATE 不能 silently skip** — 失败原因写进 final message + P8-INTEGRATION-IMPLEMENTATION.md §Build。

### Step 5: 写 P8-INTEGRATION-IMPLEMENTATION.md report (~3 min)

路径: `demo_app_service/crates/demo-app-lifecycle/reports/P8-INTEGRATION-IMPLEMENTATION.md`(~80-150L):

```markdown
# P8: demo-app-backend ↔ demo-app-lifecycle integration — Scheme A implementation

- **Worker**: W2 (glm-5.2) — implementation
- **HEAD**: `d2b3b9d` (unchanged, no commit)
- **Scheme**: A (in-process lib)
- **Net diff**: +XXX / −XXX LoC across N files

## §1 改动文件清单
(7 个文件,每个 file:line range + before/after LoC + 简述)

## §2 cargo check / build / musl build 结果
| Command | Exit | Notes |
|---|---|---|

## §3 ESCALATE self-resolution
### ESCALATE #1 — Legacy callers
- grep result: (caller file:line 列表 or "0 callers found")
- decision: (retire / alias)
- evidence: (grep output snippet)

### ESCALATE #2 — Misnomered start_service
- decision: (随 retire 删 / alias 到 lifecycle.restart + comment)
- comment 位置: handlers.rs:LINE

### ESCALATE #3 — Registry yaml
- service_ids 包含: ...
- groups 包含: ...
- 起点: registry-sp000065.yaml

### ESCALATE #4 — Priority
- P8 standalone (已定 by user)

## §4 保留 / 删除的 legacy handlers
- 删除: (7 个 docker fns list)
- 保留: (handle_logs_collect / query_robot_in_container 若有理由)
- 保留理由: ...

## §5 Observability 注入点
(FAIL/ERROR/STATE event 在 dispatch_action lifecycle.* arm 的 file:line)

## §6 Open issues / 后续 V2 验证项
- (lifecycle_cli E2E re-run against merged process — V2 job)
- (wildcard race gone: 1 submit → 1 result — V2 job)
- (musl binary cargo deb — V2 or 后续)
- 其它 W2 ESCALATE
```

## Output Contract — Final Message

W2 final message 必须包含:
1. **§1 改动文件清单** — 7 个 file:line range + before/after LoC + 简述
2. **§2 cargo check / build / musl build / clippy 结果** — 每个 command 的 exit code + 关键输出 tail
3. **§3 ESCALATE self-resolution × 4** — 每个的 decision + evidence
4. **§4 保留 / 删除 legacy handlers** — 列表 + 理由
5. **§5 Observability 注入点** — FAIL/ERROR/STATE event 的 file:line(per agentflow/observability/events.md scene-specific mandatory points)
6. **§6 Open issues / V2 验证项** — list
7. **Files created/modified** — 7 个 file:line count
8. **Time elapsed** — Xs / 1800s cap
9. **ESCALATE to orchestrator** — 任何 W2 自己无法解决的 judgment call

## Hard constraints (recap)

- **30-min hard cap** (`timeout 1800s`)。partial 到点必停。
- **0 git push / 0 git commit / 0 git add / 0 AI attribution**。
- **0 改动 `demo-app-lifecycle/src/*`** — 严格 0。
- **0 改动 `demo-app-lifecycle/examples/lifecycle_cli.rs`** — P7b 已 uncommitted,W2 不碰。
- **0 改动 SP000065 host 文件**。
- **Write-set 严格 7 个文件**(列 above)。任何 file outside = contract violation。
- **HEAD-guard** before any git touchpoint。HEAD 必须保持 `d2b3b9d`。
- **musl build 失败要 ESCALATE**,不能 silently skip。
- **NEVER modify SP000065 host files / services**(本 task 不涉及 SSH)。

## Normative reads (10 files, 60s)

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md`
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/README.md`
3. `/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/context.md`
4. `/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/events.md`
5. `/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/propagation.md`
6. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/reports/RESEARCH-DEMO-BACKEND-LIFECYCLE-INTEGRATION.md` (W1 report)
7. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/src/main.rs` (in-process 模板)
8. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/src/lib.rs` (pub API)
9. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/examples/registry-sp000065.yaml` (registry 起点)
10. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-backend/src/{main,handlers,config}.rs` (修改目标)

工作语言:中文为主,关键术语/文件路径/决策 ID 保留英文。

现在开始:read 10 normative (60s),执行 ESCALATE #1 grep (3 min),改 7 个文件 (15 min),build + musl (5 min),写 P8 report (3 min)。30 min hard cap。
