# PROMPT-W1 — demo-app-backend ↔ demo-app-lifecycle integration research worker (kimi-k3)

```
Before doing anything else:
1. Read /home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's classifier and follow every rule
   that applies.
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly 1 file: `reports/RESEARCH-DEMO-BACKEND-LIFECYCLE-INTEGRATION.md`
   (under demo-app-lifecycle/). Report every file created with line numbers
   in your final message.

HEAD-guard: before any git touchpoint, run `git log --oneline -1 && git status --short`.

model_selection:
  model: t9s/kimi-k3
  mode: automatic
  reason: research_and_architecture  # integration research; kimi-k3 balanced per workflow.md
```

---

You are **W1 of demo-app-backend ↔ demo-app-lifecycle integration research** — **research worker** investigating the integration interface between two crates in the same workspace。Lifecycle Robot Takeover (P0-P6 + P7/P7b) CLOSED 2026-08-18,`demo-app-lifecycle` crate 自身 E2E ACCEPTED,但 P7/P7b 只测了 lifecycle 自身的 daemon+CLI,**没有验证 `demo-app-backend` 怎么消费 lifecycle**。

**用户假设 (3 条,worker 需 verify/refute)**:
1. **同进程假设**:demo-app-backend 和 demo-app-lifecycle 应该跑在同一个 process 里
2. **简陋 docker 管理假设**:demo-app-backend 现在已经有 docker 管理代码,但简陋,应该用 demo-app-lifecycle 替换
3. **接口改造问题**:是否应该把 demo-app-backend 的接口改成调用 demo-app-lifecycle?

## CRITICAL: 20-MIN HARD CAP + NO CODE MODIFICATION

- **Hard time cap: 20 min wall clock**。到点必停,partial report 交付。
- **0 code modification** — 这是 research task,worker 只读 + 写 report。NEVER Edit / Write / NotebookEdit / `git add` / `git commit`。
- **0 src/ changes** (demo-app-backend 和 demo-app-lifecycle 都不动)。
- **禁止**返回 plan-only / outline / status update / "next I'll ..."。Work continuously 直到 report 写完 + final message 交付。
- **Write-set 严格 1 个文件**:`reports/RESEARCH-DEMO-BACKEND-LIFECYCLE-INTEGRATION.md` (under `demo-app-lifecycle/`)。

## Pre-known facts (inline, do not re-verify)

- demo-app-backend crate path: `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-backend/`
- demo-app-backend src files: `config.rs / envelope.rs / handlers.rs / main.rs / topic.rs` (5 files)
- demo-app-backend Cargo.toml deps: `argo-dds / demo-app-types / anyhow / base64 / chrono / futures / serde / serde_json / tokio / tracing / uuid` (**NO `demo-app-lifecycle` dep**)
- demo-app-backend description: "Demo backend: subscribes to Zenoh topics and handles robot-side operations"
- demo-app-lifecycle crate path: `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/`
- demo-app-lifecycle 7-spot P7b fix 已 land in `examples/lifecycle_cli.rs` (加 `--group` flag for `group_*` ops)
- demo-app-lifecycle D-117 sha256 sentry 保持: `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822` (`src/runtime/reconcile.rs`)
- demo-app-lifecycle P0-P6 + P7/P7b 全 ACCEPT,takeover CLOSED (D-119)
- HEAD = `d2b3b9d` on `feat/lifecycle-robot-takeover` branch

## Task

### Step 1: 读 demo-app-backend 现状 (~3 min)

Read 5 src files:
- `crates/demo-app-backend/src/main.rs` (主入口)
- `crates/demo-app-backend/src/handlers.rs` (zenoh handler)
- `crates/demo-app-backend/src/envelope.rs` (msg envelope)
- `crates/demo-app-backend/src/topic.rs` (zenoh topic)
- `crates/demo-app-backend/src/config.rs` (config)

也读:
- `crates/demo-app-backend/Cargo.toml` (deps + package metadata)
- `crates/demo-app-backend/examples/` (若有 example)
- `crates/demo-app-backend/script/` (有 `check_robot_status.py`,看是不是 docker 相关)
- `crates/demo-app-backend/debian/` (有 `demo-app-backend.service`,看 systemd unit 怎么跑)

Grep (用 Bash + `rg` 或 `grep -r`):
```bash
rg -n "docker|container|Docker|Container" crates/demo-app-backend/
rg -n "systemctl|systemd" crates/demo-app-backend/
rg -n "lifecycle|Lifecycle" crates/demo-app-backend/
rg -n "start|stop|restart" crates/demo-app-backend/src/
```

记录:
- demo-app-backend 主入口在 main.rs 哪里?
- 它订阅什么 zenoh topic? (看 topic.rs)
- 它 handler 处理什么 op? (看 handlers.rs)
- **关键**: 它现在有没有 docker 管理代码? (grep 结果) 如果有,在哪个文件哪一行,怎么实现的? (硬编码 container name? shell out to `docker` CLI? use `bollard` crate?)
- 它现在有没有调用 lifecycle? (应该是 NO,但要 verify)

### Step 2: 读 demo-app-lifecycle 公共 API surface (~3 min)

Read:
- `crates/demo-app-lifecycle/src/lib.rs` (public exports — 找 `pub use` / `pub mod`)
- `crates/demo-app-lifecycle/src/handlers.rs` (lifecycle op 入口 — `handle_lifecycle_start` / `handle_lifecycle_stop` / `handle_lifecycle_restart` / `handle_lifecycle_group_restart` 等)
- `crates/demo-app-lifecycle/src/providers/mod.rs` (provider 抽象 — `ProviderKind` enum)
- `crates/demo-app-lifecycle/src/runtime/` 看 runtime entry + reconcile
- `crates/demo-app-lifecycle/Cargo.toml` (deps + lib vs bin config)
- `crates/demo-app-lifecycle/examples/lifecycle_daemon.rs` (daemon spawn pattern)
- `crates/demo-app-lifecycle/examples/lifecycle_cli.rs` (CLI client pattern — 用 zenoh publish/subscribe)

Grep:
```bash
rg -n "pub fn|pub async fn|pub struct|pub enum|pub use|pub mod" crates/demo-app-lifecycle/src/lib.rs
rg -n "pub fn|pub async fn" crates/demo-app-lifecycle/src/handlers.rs
rg -n "pub fn|pub async fn" crates/demo-app-lifecycle/src/runtime/
```

记录:
- demo-app-lifecycle 作为 lib 暴露什么 public API?
- 它能不能 in-process 被另一个 crate 引用? (看 lib.rs 是否 export `Runtime` / `handle_lifecycle_*` / `Registry` 等)
- 还是只能 out-of-process 通过 zenoh publish `/watch/lifecycle/<op>/submit` 调用?
- 两种路径各自的入口是什么?

### Step 3: 验证/refute 用户 3 假设 (~3 min)

**假设 1 (同进程)**:verify/refute "demo-app-backend 和 demo-app-lifecycle 应该跑在同一个 process 里"
- 看 demo-app-backend main.rs 现在是 single binary 吗?
- demo-app-backend 能否加 `demo-app-lifecycle = { path = "../demo-app-lifecycle" }` 依赖?
- 如果 in-process,怎么 spawn lifecycle daemon task 在 demo-app-backend 的 tokio runtime 里? (看 lifecycle_daemon.rs 怎么 build Runtime,是否可以 `Runtime::new(...).spawn()` 进 demo-app-backend 的 runtime)
- 如果 out-of-process,demo-app-backend 怎么 talk to lifecycle daemon? (zenoh publish)
- Verdict: PASS / FAIL / PARTIAL — 同进程可行吗? 改动量多大?

**假设 2 (简陋 docker 管理假设)**:verify/refute "demo-app-backend 现在已经有 docker 管理代码,但简陋"
- 看 Step 1 的 grep 结果 — demo-app-backend 实际有没有 docker 管理代码?
- 如果有,简陋在哪里? (硬编码 container names / no audit / no group op / no state convergence / 不支持 systemd / no error handling)
- 跟 demo-app-lifecycle 比,差距是什么? (demo-app-lifecycle 有 yaml registry / 多 provider / audit log / group op / state convergence / D-Bus / roboctl HTTP)
- Verdict: PASS / FAIL / PARTIAL — 简陋假设成立吗? 简陋程度是什么?

**假设 3 (接口改造)**:verify/refute "是否应该把 demo-app-backend 的接口改成调用 demo-app-lifecycle?"
- demo-app-backend 现在的接口是什么? (zenoh topic + handler shape)
- 接口改造的路径有几种? (见 Step 4 方案 A/B/C)
- Verdict: PASS / FAIL / PARTIAL — 接口改造可行吗? 推荐哪种?

### Step 4: 提出 3 个整合方案 (~5 min)

#### 方案 A: in-process lib integration

- demo-app-backend `Cargo.toml` 加 `demo-app-lifecycle = { path = "../demo-app-lifecycle" }`
- demo-app-backend `main.rs` 里 spawn lifecycle daemon task:
  ```rust
  // pseudocode
  let lifecycle_rt = demo_app_lifecycle::Runtime::from_registry_yaml(...).await?;
  tokio::spawn(lifecycle_rt.run());
  ```
- demo-app-backend handler 直接 call demo-app-lifecycle public API:
  ```rust
  // pseudocode
  demo_app_lifecycle::handle_lifecycle_start(&lifecycle_rt, &envelope).await
  ```
- zenoh topic namespace 怎么处理? (demo-app-backend 和 demo-app-lifecycle 共用同一 argo-dds session? 还是各自独立?)
- Pros: 0 IPC overhead / 共享 Runtime state / single binary deploy
- Cons: dep coupling / binary size 增加 / Runtime state 互相影响 (demo-app-backend crash 拖死 lifecycle)
- 改动量:估算 LoC + 文件数
- 何时破:demo-app-lifecycle 需要 hot-reload registry yaml 而 demo-app-backend 不能 restart / 多个 robot fleet 需要各自 lifecycle daemon 在不同 process

#### 方案 B: out-of-process daemon

- demo-app-backend 不 depend on demo-app-lifecycle lib
- lifecycle daemon 单独 systemd unit 跑 (`demo-app-lifecycle.service`,跟 `demo-app-backend.service` 并存)
- demo-app-backend 通过 zenoh publish `/watch/lifecycle/<op>/submit` 调用 lifecycle (类似 lifecycle_cli 的 pattern)
- Pros: process isolation / lifecycle daemon 可独立 restart / 可 scale
- Cons: IPC overhead / 部署复杂 (2 systemd units) / 状态不共享 / zenoh topic namespace 必须协调
- 改动量:估算 LoC + 文件数
- 何时破:lifecycle daemon crash 时 demo-app-backend 要 retry/fallback / IPC 延迟敏感场景

#### 方案 C: roboctl-style wrap

- demo-app-backend 保留现有 API (zenoh topic + handler shape),但底层 call 换成 demo-app-lifecycle
- 旧 docker 管理代码 (如有) 删 / 替换为 lifecycle call
- 旧 API 作为 shim 适配层,forward 到 lifecycle
- Pros: backward compat / 渐进迁移 / 外部 caller 无感知
- Cons: shim 维护成本 / 双层 API (旧 + 新) 易 drift
- 改动量:估算 LoC + 文件数
- 何时破:旧 API 语义跟 lifecycle 不一致 / shim 成为 bug source

#### 每方案: pros / cons / 改动量 / 何时破 / migration 路径

### Step 5: 推荐 + 具体改动文件 + 行数估算 (~2 min)

Worker 推荐一方案,理由:
- 哪方案 fits 用户 3 假设最准?
- 改动量最小?
- 风险最低?
- migration 最平滑?

具体改动文件 + 行数估算:
- demo-app-backend Cargo.toml: 加 dep (1 line) / 不加 dep
- demo-app-backend main.rs: spawn lifecycle / publish zenoh / shim (N lines)
- demo-app-backend handlers.rs: 删旧 docker 管理代码 (if any) / 加 lifecycle call (M lines)
- demo-app-lifecycle lib.rs: 暴露 in-process API (if 方案 A, K lines)
- 新增 demo-app-lifecycle.service systemd unit (if 方案 B, 1 file)
- 等等

### Step 6: 写 report + final message (~3 min)

写 `reports/RESEARCH-DEMO-BACKEND-LIFECYCLE-INTEGRATION.md` (~5-10 KB):

```markdown
# Research: demo-app-backend ↔ demo-app-lifecycle integration

## §1 调研范围
- 读 demo-app-backend 5 src + Cargo.toml + examples + script + debian
- 读 demo-app-lifecycle lib.rs + handlers.rs + providers/ + runtime/ + Cargo.toml + examples
- grep docker / container / systemctl / lifecycle / start / stop / restart

## §2 demo-app-backend 现状
- main.rs entry: <line N, code snippet>
- zenoh topic: <topic.rs 找的>
- handler shape: <handlers.rs 找的>
- 现有 docker 管理代码: <grep 结果 + 文件:行号 + 代码 snippet>
- 跟 demo-app-lifecycle 关系: <currently no dep / no call>

## §3 demo-app-lifecycle 公共 API surface
- lib.rs public exports: <list>
- in-process 入口: <Runtime::new / handle_lifecycle_* / etc.>
- out-of-process 入口: <zenoh publish pattern from lifecycle_cli.rs>

## §4 用户 3 假设 verify/refute

### 假设 1: 同进程 — <PASS/FAIL/PARTIAL>
- evidence: <...>
- verdict + caveat

### 假设 2: 简陋 docker 管理 — <PASS/FAIL/PARTIAL>
- evidence: <...>
- verdict + caveat

### 假设 3: 接口改造 — <PASS/FAIL/PARTIAL>
- evidence: <...>
- verdict + caveat

## §5 整合方案 A/B/C

### 方案 A: in-process lib integration
- pros / cons / 改动量 / 何时破 / migration

### 方案 B: out-of-process daemon
- pros / cons / 改动量 / 何时破 / migration

### 方案 C: roboctl-style wrap
- pros / cons / 改动量 / 何时破 / migration

## §6 推荐 — <方案 X>
- 理由
- 具体改动文件 + 行数估算:
  - `crates/demo-app-backend/Cargo.toml`: ...
  - `crates/demo-app-backend/src/main.rs`: ... lines
  - `crates/demo-app-backend/src/handlers.rs`: ... lines
  - `crates/demo-app-lifecycle/src/lib.rs`: ... lines (if needed)
  - 等等

## §7 Open questions / ESCALATEs
- demo-app-backend 现有 API 调用方 (frontend? CLI? external?) 需要兼容吗?
- 同进程会不会有 zenoh topic namespace 冲突?
- 其它 crate (demo-app-frontend / demo-app-types) 需要考虑吗?
- 整合优先级? P8 or 并入 PB1 dogfood followup?
```

## Deliverables

### 1. `reports/RESEARCH-DEMO-BACKEND-LIFECYCLE-INTEGRATION.md` (NEW, ~5-10 KB)

### 2. Final message

- §1-§7 摘要 (每 § 一行)
- 用户 3 假设 verdict (3 行)
- 推荐方案 + 理由
- 具体改动文件 + 行数估算
- Open questions / ESCALATEs
- Files created (1 file + line count)
- Time elapsed

## Hard constraints

- **0 code modification** — research task,只读 + 写 report。
- **0 src/ changes** (demo-app-backend 和 demo-app-lifecycle 都不动)。
- **Hard 20-min cap** — timeout 1200s。到点必停 partial 交付。
- **Write-set 严格 1 个文件**:`reports/RESEARCH-DEMO-BACKEND-LIFECYCLE-INTEGRATION.md` (under `demo-app-lifecycle/`)。
- **NEVER** `git push`。**NEVER** `git add` 或 `git commit`。**NEVER** AI attribution。
- **NEVER** Edit / Write (除 report 文件外) / NotebookEdit。
- **HEAD-guard** before any git touchpoint。HEAD 必须保持 `d2b3b9d`。
- **NEVER** modify SP000065 host files / services (本 task 不涉及 SSH)。

## Normative reads (5 files, 30s — cache from P7b)

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md`
2. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-backend/src/main.rs`
3. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-backend/src/handlers.rs`
4. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/src/lib.rs`
5. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/examples/lifecycle_daemon.rs`

工作语言:中文为主,关键术语/文件路径保留英文。

现在开始:read 5 normative + Cargo.toml + grep (3 min),read demo-app-lifecycle API surface (3 min),verify 3 假设 (3 min),写方案 A/B/C + 推荐 (5-7 min),写 report (3-5 min)。20 min hard cap。
