# task.md — demo-app-backend ↔ demo-app-lifecycle integration research

## 背景

Lifecycle Robot Takeover (P0-P6 + P7/P7b) 已 CLOSED 2026-08-18。`demo-app-lifecycle` crate 实现了 yaml-declared topology + lifecycle op (start/stop/restart/group_restart) via zenoh + HTTP/systemd/docker providers。**但 P7/P7b 只测试了 demo-app-lifecycle 自身的 E2E (单独跑 daemon + lifecycle_cli),没有验证 demo-app-backend 怎么消费它**。

用户观察(2026-08-18):
> "我们现在是不是简单测试了一下,但是并没有和 demo-app-backend 进行接口兼容,派人考虑一下。首先我们肯定是和 demo-app-backend 一个进程,demo-app-backend 已经有了 docker 管理但是这个台简陋肯定要使用 demo-app-lifecycle。所以是不是 demo-app-backend 接口改低哦用 demo-app-lifecycle。"

## 用户假设 (3 条,worker 需 verify/refute)

1. **同进程假设**:demo-app-backend 和 demo-app-lifecycle 应该跑在同一个 process 里
2. **简陋 docker 管理假设**:demo-app-backend 现在已经有 docker 管理代码,但简陋,应该用 demo-app-lifecycle 替换
3. **接口改造问题**:是否应该把 demo-app-backend 的接口改成调用 demo-app-lifecycle?

## Worker 任务 (research only, NO code modification)

W1 research worker 调研:

1. **demo-app-backend 现状**
   - 读 `crates/demo-app-backend/src/` 5 文件 (main.rs / handlers.rs / envelope.rs / topic.rs / config.rs)
   - 读 `crates/demo-app-backend/examples/` + `script/` + `debian/`
   - 读 `Cargo.toml` (已知不依赖 demo-app-lifecycle,但要看 argo-dds 怎么用)
   - grep "docker" / "container" / "start" / "stop" / "restart" / "Bocker" / "ContainerEngine" 在 demo-app-backend 全 crate
   - 找出:demo-app-backend 现在的 zenoh topic 是什么?handler 处理什么 op?有没有 docker 管理代码?如果有,在哪里,怎么实现的?

2. **demo-app-lifecycle 公共 API surface**
   - 读 `crates/demo-app-lifecycle/src/lib.rs` 找 public exports
   - 读 `crates/demo-app-lifecycle/src/handlers.rs` 找 lifecycle op 入口
   - 读 `crates/demo-app-lifecycle/src/providers/` 找 provider 抽象 (systemd / docker / http)
   - 读 `crates/demo-app-lifecycle/examples/lifecycle_daemon.rs` + `examples/lifecycle_cli.rs` 找 daemon/CLI 入口
   - 找出:demo-app-lifecycle 作为 library 可以怎么被另一个 crate 引用?有没有 lib.rs 暴露的 in-process API?还是只能通过 zenoh topic out-of-process 调用?

3. **验证/refute 用户 3 假设**
   - 假设 1 (同进程):看 demo-app-backend main.rs 是 single binary 吗?它能直接 depend on demo-app-lifecycle lib 吗?如果可以,how to integrate (cargo dep + lib import + 调用入口)? 如果 out-of-process,demo-app-backend 怎么 talk to demo-app-lifecycle daemon (zenoh publish/subscribe)?
   - 假设 2 (简陋 docker):demo-app-backend 实际有没有 docker 管理代码?如果有,简陋在哪里 (hard-coded container names? no audit? no group op? no state convergence? 不支持 systemd?) 跟 demo-app-lifecycle 比,差距是什么?
   - 假设 3 (接口改造):接口改造的具体路径是什么?有几种方案?

4. **提出整合方案** (architect level, NOT code)
   - 方案 A:**in-process lib integration** — demo-app-backend Cargo 加 `demo-app-lifecycle = { path = "../demo-app-lifecycle" }` 依赖,demo-app-backend main.rs 里 spawn lifecycle daemon task (in tokio runtime),demo-app-backend handler 直接 call demo-app-lifecycle public API (in-process)。
   - 方案 B:**out-of-process daemon** — demo-app-backend 不 depend on demo-app-lifecycle,而是 lifecycle daemon 单独 systemd unit 跑,demo-app-backend 通过 zenoh publish `/watch/lifecycle/<op>/submit` 调用 lifecycle (类似 lifecycle_cli)。
   - 方案 C:**roboctl-style wrap** — demo-app-backend 保留现有 docker 管理 UI,但底层调用换成 demo-app-lifecycle (作为 lib 或 daemon),旧 API 作为 shim 适配。
   - 每方案:pros / cons / 改动量 / 何时破 / migration 路径。
   - Worker 推荐:选一方案 + 理由 + 具体改动文件 + 改动行数估算。

5. **Open questions / ESCALATEs**
   - demo-app-backend 现在的 docker 管理代码量有多大?能不能直接删 / 替换?
   - 同进程会不会有 zenoh topic namespace 冲突 (两个 crate 都用 argo-dds,但 bot_name 不同)?
   - demo-app-backend 的现有 API 调用方 (frontend? CLI? external?) 需要兼容吗?
   - 还有其它 crate 在 demo_app_service/ 下 (demo-app-frontend, demo-app-types) 需要考虑吗?

## Deliverables (1 个 research report 文件)

写 `reports/RESEARCH-DEMO-BACKEND-LIFECYCLE-INTEGRATION.md` (~5-10 KB, under `crates/demo-app-lifecycle/reports/`):

结构:
- §1 调研范围 (读哪些文件 / grep 什么)
- §2 demo-app-backend 现状 (架构 + zenoh topic + handler + 现有 docker 管理代码如有)
- §3 demo-app-lifecycle 公共 API surface (lib.rs exports / in-process vs out-of-process)
- §4 用户 3 假设 verify/refute (每条 PASS/FAIL/PARTIAL + evidence)
- §5 整合方案 A/B/C (pros/cons/改动量/何时破/migration)
- §6 推荐 + 理由 + 具体改动文件 + 行数估算
- §7 Open questions / ESCALATEs

## Hard constraints

- **0 code modification** — 这是 research task,worker 只读 + 写 report。
- **0 src/ changes** (demo-app-backend 和 demo-app-lifecycle 都不动)。
- **Hard 20-min cap** — timeout 1200s。到点必停 partial report 交付。
- **Write-set 严格 1 个文件**:`reports/RESEARCH-DEMO-BACKEND-LIFECYCLE-INTEGRATION.md`。
- **NEVER** `git push`。**NEVER** `git add` 或 `git commit`。**NEVER** AI attribution。
- **NEVER** modify SP000065 host files / services。
- **HEAD-guard** before any git touchpoint。HEAD 必须保持 `d2b3b9d` (无 commit)。

## Pre-known facts (inline)

- demo-app-backend crate path: `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-backend/`
- demo-app-backend src files: `config.rs / envelope.rs / handlers.rs / main.rs / topic.rs` (5 files)
- demo-app-backend Cargo.toml deps: `argo-dds / demo-app-types / anyhow / base64 / chrono / futures / serde / serde_json / tokio / tracing / uuid` (**NO demo-app-lifecycle dep**)
- demo-app-backend description: "Demo backend: subscribes to Zenoh topics and handles robot-side operations"
- demo-app-lifecycle crate path: `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/`
- demo-app-lifecycle 7-spot P7b fix 已 land in `examples/lifecycle_cli.rs` (加 `--group` flag for `group_*` ops)
- demo-app-lifecycle D-117 sha256 sentry 保持: `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822` (`src/runtime/reconcile.rs`)
- demo-app-lifecycle P0-P6 + P7/P7b 全 ACCEPT,takeover CLOSED (D-119)
- HEAD = `d2b3b9d` on `feat/lifecycle-robot-takeover` branch

## Time budget

**20 min wall clock**。Single-section >3 min → 标 PARTIAL + 移到下一 section。

工作语言:中文为主,关键术语/文件路径/决策 ID 保留英文。

现在开始:read demo-app-backend 5 src files + Cargo.toml (60s),grep docker/container (30s),read demo-app-lifecycle lib.rs + handlers.rs (60s),verify 3 假设 (3 min),写方案 A/B/C + 推荐 (5-7 min),写 report (3-5 min)。20 min hard cap。
