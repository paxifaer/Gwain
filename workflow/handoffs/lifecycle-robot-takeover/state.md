# state.md — 恢复 payload (≤60 lines)

## Phase
**P0-P6 DONE (takeover CLOSED) + P7/P7b bonus DONE**. V5 ACCEPT 2026-08-18 (P5 SP000065 dogfood) → V6 ACCEPT 2026-08-18 (P6 roboctl wrap-only final form) → V7 RE-DISPATCH 2026-08-18 (P7 full E2E, 3 hard FAILs: claim 3/4/5) → V7b **ACCEPT P7b** 2026-08-18 (P7b fix-cycle, 10/10 PASS, ~3 min)。

## Blocked
(空) — takeover 全闭环;followup 移交后续。

## Last completed
- 2026-08-18 **P7b ACCEPT** (V7b clean ACCEPT, 10/10 claim PASS, ~3 min)。Fix-cycle for V7 RE-DISPATCH (P7 3 hard FAILs)。W7b modified `examples/lifecycle_cli.rs` 7 spots (+29/-9) 加 `--group` flag + `group_id` payload for `group_*` ops。Re-ran `lifecycle_cli group_restart --group robot-stack` 真跑通(CLI payload `{"group_id":"robot-stack"}` ✓,daemon accepted 4 members,8 audit lines `orig=be889dbd`)。4 members verdict: 2 PASS (localization + nav2 docker start fan-out) + 2 DEGRADED (rustbot-daemon/monitor polkit)。Restructured 4 reports (§1-§5 / per-(svc,op) 25×3 / W7b session appended / P7b-FIX-REPORT delta)。0 src/ changes (examples/lifecycle_cli.rs 是 examples/ 不是 src/),HEAD=d2b3b9d,SHA256 D-117 sentry 保持。Write-set 5 files。V7b open judgment: docker containers Up from group_restart fan-out = **ACCEPT** (W7b argument: intended post-group_restart semantics)。
- 2026-08-18 **P7 RE-DISPATCH** (V7 verdict, 3 hard FAILs: claim 3 §1-§5 结构 / claim 4 per-op 3方对照 thin / claim 5 group_restart SKIPPED)。W7 ran full E2E on SP000065 (~10.5 min): 8 svc × 3 op = 24 cells (9 PASS + 4 EXP-FAIL + 6 DEGRADED + 3 skipped + 2 group_restart cells) + robot-stack group_restart SKIPPED (`lifecycle_cli.rs:179` 发 service_id,`handlers.rs:684` 读 group_id → MISSING_FIELD)。Write-set 4 files (registry-sp000065-control.yaml / P7-FULL-E2E-REPORT.md / P7-DAEMON-LOG.txt / P7-EVIDENCE.md)。V7 RE-DISPATCH → P7b fix-cycle。
- 2026-08-18 **P6 ACCEPT** (V6 clean ACCEPT)。roboctl wrap-only 固化 (D-101 default + user pick "wrap-only(推荐,沿用 D-101 默认)")。0 src/ changes / 0 SP000065 access / 0 build。Write-set 1 file `reports/P6-ROBOCTL-WRAP-FINAL-REPORT.md` (67 lines, 6917B)。D-118/D-119 landed。
- 2026-08-18 **P5 ACCEPT** (V5 ACCEPT, 10/10 claim PASS, ~90s)。SP000065 compressed dogfood (W5b 10-min compressed worker, 5 核心 case PASS + 9 skipped)。Robot host boundary 没违反。sha256 D-117 sentry 保持。Write-set 4 files (registry-sp000065.yaml / P5-DAEMON-LOG.txt / P5-EVIDENCE.md / P5-DOGFOOD-REPORT.md)。
- 2026-08-18 **P4 ACCEPT** (V4 clean ACCEPT, no WITH CONCERNS)。ProviderKind::Http + http.rs (527 LoC) + bearer env/file XOR + (Restart, Completed) matrix arm + python3 http.server stub。0 Hard FAIL。
- 2026-08-18 P0/P1/P2/P3 已 ACCEPT WITH CONCERNS (non-blocking);P4/P5/P6 是 clean ACCEPT
- Test gate trajectory: 40 (MVP) → 52 (P1) → 63 (P2) → 83 (P3) → **99 (P4 close)** → P5/P6 不跑 cargo test (0 src/ 改, 99/99 baseline 保持),全部 serial `--test-threads=1`
- reconcile.rs sha256 sentry 终态: `74b92f34…72b822` (D-117;P3 单 arm 加法后未再动 — P4/P5/P6 全程 unchanged)
- G1..G12 全部 CLOSED (跨 P1-P4 映射见 V4-VERDICT.md "P0→P4 cumulative close")

## Pending user decisions
(空) — 用户已答 (P5 host = SP000065 / P6 形态 = wrap-only),takeover 全闭环。

## Current
- takeover CLOSED (D-119) + P7/P7b bonus real-robot E2E DONE (D-120/D-121)。`handoffs/lifecycle-robot-takeover` 留 CLOSED 状态,P7/P7b 是 takeover closing 后的 bonus validation phase。
- evaluation.md 含 P0-P7b 全 verdict 链路;decisions.md 收 D-101..D-121 全决策 (D-118 roboctl wrap-only / D-119 takeover CLOSED / D-120 P7 RE-DISPATCH / D-121 P7b ACCEPT)。

## Next (followup 移交后续 — 不在 takeover scope, 也不在 P7b scope)
1. followup A: registry-sp000065.yaml 自动生成 — 从 SP000065 真实容器名/真实 systemd unit 名生成,而非拷 registry-robot.yaml 模板 (W5b nav2-member Failed 根因)。
2. followup B: PB1 real group_restart dogfood — 机器人停机维护窗口时验证 lifecycle HTTP provider POST `/api/group/robot-stack/restart` 端到端 (roboctl 整组 restart + 硬件 daemon 起 + hw.lock 抢占 + SHM 重连)。**P7b 已部分覆盖**: CLI fix PASS + group_restart 真跑 (2/4 docker PASS + 2/4 polkit DEGRADED)。剩余 systemd system-scope 启 hardware-tagged units 需要 polkit 授权。
3. followup C: robot fleet 扩展 — 非 roboctl 机器 (wrap-only 边界 case,见 P6 report §3 trigger 3)。需 lifecycle 多 backend 抽象。
4. followup D: GLIBC musl toolchain 默认化 — W5b learning (W6 §4 推荐),memory `feedback_musl_target_for_robot_dogfood` 已落地。
5. **followup E (NEW from P7b): polkit systemd system-scope DEGRADED 修复** — `rustbot-daemon-member` / `rustbot-monitor-member` start/restart 4 ops DEGRADED at actuation layer (CLI accept + audit seq,但 host `ActiveState=inactive` 未变)。根因:niic-user polkit 规则对 hardware-tagged unit 的 StartUnit 无权限。**非本 crate src/ defect — 交 NiicAdmin 或另开 worker** (V7 item 5)。同理 docker container `localization-member` stop/restart DEGRADED — docker restart-policy `always` 或 stop_container SIGKILL timing 嫌疑。

## Watch-out 累计 (takeover CLOSED — 已是最终态,不再增加)
- 0 mock / 0 `std::process::Command::new` in src/ / `.control(` 唯一 sentinel 全程维持 (P0-P6)
- reconcile.rs sha256 终态 `74b92f34…72b822`;P2 免破例 (D-115 handler 扇出),P3 D-116 scoped 单臂破例,P4/P5/P6 不动 (D-117 保持)
- testing.md §5 7 条模板 + HEAD-guard + model_selection 全程生效
- PROTOC=/tmp/protoc/bin/protoc; cargo -p demo-app-lifecycle; --test-threads=1
- sudo 可用 (密码 abc123 本次 session 用户已供);polkit `/etc/polkit-1/rules.d/49-argowatch-lifecycle.rules` 已装
- 4 份 W prompt (W1-W4) + 4 份 V verdict (V1-V4) 是 P0-P4 code phase 迭代模板;W5b+V5 (P5 dogfood) + W6+V6 (P6 wrap-only closing) 用 kimi-k3 model,文档化/验证 task 的迭代模板
- P5/P6 followup (registry 自动生成 / PB1 real dogfood / fleet 扩展 / musl toolchain) 不在本 takeover scope,移交后续 task
