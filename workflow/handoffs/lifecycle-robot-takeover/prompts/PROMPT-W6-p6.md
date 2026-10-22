# PROMPT-W6 — P6 Worker (sonnet-equivalent), 5-min roboctl wrap-only final form documentation

```
Before doing anything else:
1. Read /home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's classifier and follow every rule
   that applies.
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly 1 file: `reports/P6-ROBOCTL-WRAP-FINAL-REPORT.md` (under demo-app-lifecycle/)。Report every file created with line numbers in your final message.

HEAD-guard: before any git touchpoint, run `git log --oneline -1 && git status --short`.

model_selection:
  model: t9s/kimi-k3
  mode: automatic
  reason: documentation_synthesis  # P6 = wrap-only 立场文档化 + W5b findings 收尾;不涉及代码 / SP000065
```

---

You are **W6 of Lifecycle Robot Takeover P6** — **roboctl wrap-only final form documentation + takeover closing**。P0-P5 已 ACCEPT:
- P0-P4 code phase: V4 clean ACCEPT 2026-08-18(99/99 serial,sha256 D-117 sentry)
- P5 dogfood: V5 ACCEPT 2026-08-18(W5b compressed dogfood on SP000065,5 核心 case PASS + PB1 ESCALATE-by-design,robot host boundary 没违反)

**用户 explicit 选 P6 = wrap-only**(沿用 D-101 默认):
> "wrap-only(推荐,沿用 D-101 默认)" — AskUserQuestion 用户答

P6 是文档化任务,**0 src/ file changes**,**0 SP000065 access**,**0 build**。只写 1 个 markdown 报告。

## CRITICAL: 5-MIN HARD CAP + NO PARTIAL RETURNS

- **Hard time cap: 5 min wall clock**。到点必停,partial 状态作为 final message 交付。
- **禁止**返回 plan / outline / status update / "next I'll ..." 这种局部进度。
- Work continuously until `reports/P6-ROBOCTL-WRAP-FINAL-REPORT.md` 写完 + final message 交付。

## Normative reads, in order(精简 — 只读 5 个文件,30 秒内)

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md` — Gawain classifier + hard constraints。
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/lifecycle-robot-takeover/task.md` — P6 acceptance criteria(line 5: "P6 = acceptance + takeover decision";line 14-18: scope split + default decisions)。
3. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/lifecycle-robot-takeover/decisions.md` — D-101 (roboctl wrap-first) / D-102 (dogfood deferred) / D-103 (auto-through cadence) / D-111 (HTTP provider schema) / D-117 (sha256 sentry)。
4. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/reports/P5-DOGFOOD-REPORT.md` — W5b dogfood evidence(PD2 PASS / PB1 ESCALATE / GLIBC mismatch / nav2-member Failed)。
5. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/reports/V5-VERDICT.md` — V5 ACCEPT P5 verdict(10/10 claim PASS)。

**不要**读其它文件 — P6 是文档化任务,不需要读 src/ 或 registry yaml。

## Deliverables(只 1 个文件 + final message)

### 1. `reports/P6-ROBOCTL-WRAP-FINAL-REPORT.md`(NEW, 3-5 KB)

结构:

#### §1. P6 决策固化 — roboctl wrap-only final form

- 引用 D-101 "wrap first" 立场 + 用户 P6 AskUserQuestion "wrap-only(推荐,沿用 D-101 默认)" 拍板。
- 声明:**roboctl 最终形态 = wrap-only**。P4 HTTP provider(`src/providers/http.rs`)作为 lifecycle ↔ roboctl 的 canonical 接口,lifecycle 不重写 / replace / 内嵌 roboctl 逻辑。
- 不走 replace(不删 roboctl 调用面)、不走 deprecate(不迁 off roboctl)。
- A 组 robot-stack 的 group_restart 操作:**生产路径 = lifecycle HTTP provider → roboctl POST `/api/group/robot-stack/restart`**;P2 原生 depends_on fan-out 拓扑留作 lifecycle 内部 group 不依赖 roboctl 时的备选(见 §3 边界 case)。

#### §2. W5b dogfood evidence 支持 wrap-only

- **PD2 PASS** 是 wrap-only 立场的 dogfood 验证:`rustbot-daemon-http` 通过 HTTP provider + Bearer token from `/home/niic/.config/roboctl/token` + GET `http://192.168.100.100:8765/api/units` → `phase=Running http_status=200`。**证明 P4 HTTP provider 直连 roboctl 在真机上工作**(D-111 schema + D-112 env_file ${VAR} 插值 + Bearer token 注入端到端通)。
- PB1 ESCALATE-by-design 留作 wrap-only 的副作用:真 `group_restart` 不在 P5 dogfood 跑(robot host boundary),但 lifecycle 通过 HTTP provider **能** POST `/api/group/robot-stack/restart` 调用 roboctl 整组 restart(P5 未验证 control verb,留作后续维护窗口)。

#### §3. 为什么 wrap-only(选了什么 / 牺牲了什么 / 何时破)

- **选了什么**:复用 roboctl 已有的 unit/group 启停逻辑、hw.lock 互斥、SHM 重连、`/api/group/robot-stack/restart` 整组原子性。lifecycle 不重新实现这些。
- **牺牲了什么**:
  - lifecycle 不能 bypass roboctl 的 hw.lock 互斥(若 roboctl 拒绝,lifecycle op 也拒绝);
  - lifecycle 不能感知 roboctl 内部状态(如 hw.lock 持有者、SHM 重连进度)—— 只能看 HTTP 响应;
  - lifecycle 的 group_restart 不再是"逐个 fan-out depends_on 成员"语义,而是"一次性委托 roboctl 整组 restart"(roboctl 内部如何 fan-out 对 lifecycle 不透明)。
- **何时破(可能转向 replace 或 deprecate 的触发条件)**:
  1. roboctl 上游不可用 / 弃维护 → lifecycle 需自带 unit/group 启停逻辑(replace);
  2. roboctl 的 group 原子性语义不再满足 lifecycle 运维需求(如需要部分成员 fan-out 部分保留)→ 需 lifecycle 原生 group verb(D-101 twin-track 的 P2 路径);
  3. SP000065 之外的机器人 fleet 不用 roboctl → wrap-only 不适用,需 lifecycle 多 backend 抽象。

#### §4. W5b dogfood findings 处置(非 P6 阻断,followup)

- **GLIBC_2.39 mismatch**(wangdang glibc 2.39 → SP000065 Ubuntu 22.04 glibc 2.35):W5b 用 `cargo build --target x86_64-unknown-linux-musl` 静态 build 57s 解决。**P6 followup**:后续 P5 类 dogfood 默认用 musl target(建议 orchestrator 加 memory `feedback_musl_target_for_robot_dogfood`)。
- **nav2-member phase=Failed**(`nav2-dev` 容器在 SP000065 不存在,registry 拷自 `registry-robot.yaml` 模板未替换真实容器名):**P6 followup**:registry-sp000065.yaml 是 dogfood artifact,**不 ship**;真实部署 registry 应该由 SP000065 真实容器名 / 真实 systemd unit 名生成(自动生成 or 人工对齐,留作后续)。
- **PB1 real group_restart dogfood 未跑**:留作后续维护窗口(机器人停机维护时,可验证 lifecycle HTTP provider POST `/api/group/robot-stack/restart` 是否真触发 roboctl 整组 restart + 硬件 daemon 启 + hw.lock 抢占 + SHM 重连)。**不在 P6 scope**。

#### §5. Takeover 关闭声明

- `demo-app-lifecycle` 已实现 task.md §Goal:yaml 声明全部 20 robot-topology entries + 任何 lifecycle op 通过 yaml edit + zenoh command 可达,**无代码改动**。
- P0-P6 全 ACCEPT:
  - P0 = bootstrap reconcile baseline + MVP D-015 warn-only 解除准备
  - P1 = system scope + env_file + docker exec + .target(D-105 polkit / D-106 系统目录 / D-107 exec_start/exec_script 互斥 / D-113 test05/06 让步)
  - P2 = group_restart + depends_on(D-104 sha256 破例未用 / D-115 op-driven cascade)
  - P3 = oneshot Phase::Completed + start_cmd + advanced selectors(D-108 Phase::Completed / D-109 tokio::process / D-110 pid_file/tmux_session/cmdline_regex 互斥 / D-116 sha256 破例单 arm)
  - P4 = ProviderKind::Http + bearer token(D-111 schema / D-112 env_file ${VAR} / D-117 新 sha256 sentry)
  - P5 = SP000065 compressed dogfood(V5 ACCEPT 10/10 claim PASS,5 核心 case PASS + 9 skipped,robot host boundary 没违反)
  - P6 = roboctl wrap-only final form(本报告)
- Test gate trajectory:40 → 52 → 63 → 83 → 99(P4 close)→ P5 不跑 cargo test(0 src/ 改,99/99 已 baseline)→ P6 不跑 cargo test(0 src/ 改)
- reconcile.rs sha256 sentry 终态:`74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822`(D-117;P5/P6 保持 unchanged)
- 0 mock / 0 `std::process::Command::new` in src/ / `.control(` 唯一 sentinel 全程维持
- handoffs/lifecycle-robot-takeover 转 CLOSED 状态(orchestrator 后续 update state.md + decisions.md D-118/D-119/D-120 + evaluation.md 收尾)。

### 2. Final message(写在 final assistant text 里)

- §1-§5 摘要(每 § 一行)
- **0 src/ file changes** ✓
- **HEAD = `d2b3b9d`** ✓(branch `feat/lifecycle-robot-takeover`,clean — verify via `git log --oneline -1 && git status --short`)
- **SHA256 D-117 sentry 保持** ✓(`sha256sum demo_app_service/crates/demo-app-lifecycle/src/runtime/reconcile.rs` = `74b92f34...72b822`)
- Files created:`reports/P6-ROBOCTL-WRAP-FINAL-REPORT.md` + 行数 + 一行描述
- ESCALATEs(如有)
- Time elapsed

## Hard constraints

- **0 src/ file changes** — P6 是文档化任务。**绝对不**改 src/ 下任何文件。
- **0 SP000065 access** — P6 不需要 SSH 到 SP000065。
- **0 build / 0 cargo / 0 cargo test** — 不需要 build,99/99 baseline 已 P0-P4 验证。
- **Hard 5-min wall clock cap** — 到点必停。
- **Write-set 严格 1 个文件**:`reports/P6-ROBOCTL-WRAP-FINAL-REPORT.md`。
- 任何 git touchpoint 之前 HEAD-guard。
- **NEVER** `git push`。
- **NEVER** AI attribution 到 commit。

## Time cap

**5 min wall clock**。

工作语言:中文为主,关键术语/文件路径/决策 ID 保留英文。

现在开始:read 5 个 normative reads(≤30s),然后按 §1-§5 顺序写 `reports/P6-ROBOCTL-WRAP-FINAL-REPORT.md`,然后发 final message。
