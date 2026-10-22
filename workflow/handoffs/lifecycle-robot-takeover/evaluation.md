# evaluation.md — Lifecycle Robot Takeover 验收记录

> 由 orchestrator 在每个 V* 完成后写。Worker 不写这里。

## 验收矩阵 (与 task.md Acceptance 一一对应)

继承 argowatch-mvp-lifecycle 的 12 条 + 每 P 新增 PA/PB/PC/PD 系列。见各 P 段落。

## 历史判定

### P0 — task-state 落盘 (2026-08-18)

docs: task.md / state.md / decisions.md / evaluation.md / prompts/
继承: 父 MVP task-state CLOSED
默认决策: D-101 (roboctl wrap) / D-102 (no dogfood) / D-103 (auto) / D-104 (sha256 sentry)

### P1 — ACCEPT WITH CONCERNS (2026-08-18, V1 ACCEPT)

Workers: W1 (killed mid-flight at alpine bash fixture) → W1-resume (fixed 3 deviations) → W1-finalize (D-113 zenoh_e2e rewrite)
Verifier: V1 ACCEPT WITH CONCERNS at `handoffs/lifecycle-robot-takeover/V1-VERDICT.md`. 5/5 PA green, all invariants green, 0 Hard FAIL.
Test gate: 52/52 serial (40 MVP − 1 retired per D-113 + 13 new).
Permission: dual-proven (sudo root + polkit `/etc/polkit-1/rules.d/49-argowatch-lifecycle.rules`).
Deltas landed: D-113 (zenoh_e2e test05+test06 auth), D-114 (spec_loader warn+Err auth), D-115 (PB2 = op-driven cascade).
Concerns (non-blocking, track into P2 back-bag):
- C1: `systemd.rs:274` hardcodes `detail["scope"]="user"` — cosmetic, fix in a later P
- C2: `main.rs:101-104` factory comment still says `"system" fails startup` — doc rot
- C3: `zenoh_e2e.rs:42-44` header inventory frames D-014/D-015 as failure-path side rails (the D-113 rewrite makes this partially stale)
- C4: `system_scope_e2e::test05` could tighten post-Start assertion (Requires= ride-along member state)
- C5: schema.rs mtime residue — audit-trail note only

### P2 — ACCEPT WITH CONCERNS (2026-08-18, V2 ACCEPT)

Workers: W2 (returned plan-only, no code — recycled) → W2-resume (delivered all P2 deliverables in 30 min)
Verifier: V2 ACCEPT WITH CONCERNS at `handoffs/lifecycle-robot-takeover/V2-VERDICT.md`. 3/3 PB green, all invariants green, 0 Hard FAIL.
Test gate: 63/63 serial (52 P1 close + 3 spec_loader C6/C7 + 5 group_restart + 3 restart_cascade).
Architecture: D-115 handler-fan-out landed — reconcile.rs sha256 unchanged (`43f0155ec5…09d200`), D-104 P2 exception NOT consumed. Topo order strict (stop c,b,a / start a,b,c). Cascade single-level + desired=Running gate.
Landings: `ACTION_LIFECYCLE_GROUP_RESTART` verb, C6 ref check + C7 acyclic check in loader, `computed_members_for_group` + `topo_sort_group_forward` + `cascade_restart_to_reverse_deps` + `write_desired_group_start` in handlers.
Concerns (non-blocking, back-bag):
- C1: doc rot at `loader.rs:23` + `main.rs:101-105` (carried over from P1)
- C2: W's self-reported LoC figures inaccurate (517 vs claimed 380, 753 vs claimed 430) — reporting hygiene
- C3: stop-leg timeout silently swallowed (5s per-member budget; hang = silent continue)
- C4: cascade errors warn-only (no escalation path)
- C5: test05's `assert_ne!(pre, post)` weakly tautological when `pre=None` — could tighten with `post.is_some()` + pairwise-distinct pins

### P3 — ACCEPT WITH CONCERNS (2026-08-18, V3 ACCEPT)

Worker: W3 delivered all three clusters in ~55-65 min. Zero ESCALATEs.
Verifier: V3 ACCEPT WITH CONCERNS at `handoffs/lifecycle-robot-takeover/V3-VERDICT.md`. 3/3 PC green, all invariants green, 0 Hard FAIL.
Test gate: 83/83 serial (63 P2 baseline + 20 new).
Sha256 sentry PASSED via D-116 scoped exception: `43f0155ec5…09d200` → `74b92f34…72b822` (D-117). Diff = single `matches!()` alternative in `derive_converged` for `(Running, Phase::Completed)`. Rest byte-identical.
G9/G11/G12 all demonstrably lifted.
Concerns (fold into P4):
- C1: state-plane advertises `restart` for Completed but handler op_allowed matrix rejects it → P4 extends `(Restart, Phase::Completed) → true` in `handlers.rs`
- C2: systemd Unknown-interface detection via error substring (cosmetic)
- C3: leaked-child tradeoff in `spawn_start_cmd` (kernel zombie window; documented)
- C4: test05_oneshot_available_actions only pins one half; main.rs matrix unit test covers other half (combined non-tautological)
- C5: no explicit `(Stopped, Completed)` arm in derive_converged — W3 chose implicit exhaustiveness (documented)

### P4 — ACCEPT (2026-08-18, V4 ACCEPT)

Worker: W4 delivered in ~55 min. Zero ESCALATEs. Two documented judgment calls:
- Flat dotted selector keys (`status.url`, `restart.method`) — SelectorMap=BTreeMap<String,String> cannot deserialize nested maps
- Explicit-version reqwest `version = "0.12"` over workspace inheritance — cargo 1.95 workspace+default-features=false quirk
Verifier: V4 **ACCEPT** (clean, no WITH CONCERNS) at `handoffs/lifecycle-robot-takeover/V4-VERDICT.md`. 3/3 PD green, all invariants green, 0 Hard FAIL. Every dynamic claim re-executed in verifier's shell; V3-C1 matrix fix was reverted-then-restored by verifier to independently prove before/after behavior.
Test gate: 99/99 serial (83 baseline + 4 status + 5 control + 5 bearer + 2 spec_loader).
Sha256 sentry PASSED: `74b92f34…72b822` unchanged end-of-P4 (D-117). `.control(` = 1. 0 `std::process::Command::new` in src/. 0 mock imports. git HEAD `43f9c55` no commit/push.
Matrix purity: only Restart arm extended with `Completed`; Start/Stop arms unchanged. V3-C1 closed.
Concerns (non-blocking, back-bag):
- C1: response body not drained (connection pool reuse foregone)
- C2: no default `Content-Type: application/json` header on POST bodies
- C3: `user_agent` override path untested
- C4: provider-wide `default_timeout_ms` with per-verb selector override (documented)

### P5 — ACCEPT (2026-08-18, V5 ACCEPT)

Worker: W5 (killed mid-flight at探查 phase after ~5 min, no lifecycle_cli invocations) → W5b (compressed 10-min worker, inline pre-known facts) → W5b-resume (timeout hit mid P5-DOGFOOD-REPORT.md, resumed to finish missing report + final message in ~40s)。
Verifier: V5 **ACCEPT** at `demo_app_service/crates/demo-app-lifecycle/reports/V5-VERDICT.md`. 10/10 claim PASS (~90s, well under 5-min cap). Adversarial disprove via SSH cross-check + log grep + git forensics。
Scope: SP000065 compressed dogfood (192.168.100.100, user niic)。5 核心 case PASS + 9 skipped (robot host boundary respected):
- PA1 argo-zenoh-global `phase=Running` (host cross-check `is-active=active`)
- PA3 docker exec_start `accepted=true seq=1` + audit 行 + 容器未动 (Up 5 hours unchanged)
- PC1 ethercat-oneshot `phase=Stopped` (D-108 tradeoff — oneshot RemainAfterExit=no,ActiveState=inactive SubState=dead)
- PD2 rustbot-daemon-http `phase=Running http_status=200` (Bearer token from `~/.config/roboctl/token` + D-111 schema + D-112 env_file `${VAR}` 插值 端到端通)
- PB1 robot-stack 4 members bind, no group_restart POST (ESCALATE-by-design, robot host boundary — POST 会启动硬件 daemon / 抢 hw.lock / SHM 重连,不可逆风险)
Test gate: P5 不跑 cargo test (0 src/ 改, 99/99 P4 baseline 保持)。
Sha256 sentry 保持: `74b92f34...72b822` unchanged (D-117)。
Robot host boundary verified: 0 synthetic/lifecycle/p5- units in /etc/systemd/system/, token file = 44 bytes (43+\n) unchanged, daemon pkill cleanup verified (ps -ef empty)。
Write-set: 4 files — `examples/registry-sp000065.yaml` (135L) / `reports/P5-DAEMON-LOG.txt` (419L) / `reports/P5-EVIDENCE.md` (194L) / `reports/P5-DOGFOOD-REPORT.md` (136L)。
W5b findings (non-blocking, P6 followup):
- GLIBC_2.39 mismatch (wangdang glibc 2.39 → SP000065 Ubuntu 22.04 glibc 2.35): solved via `cargo build --target x86_64-unknown-linux-musl` 静态 build 57s。P6 followup: orchestrator add memory `feedback_musl_target_for_robot_dogfood`。
- nav2-member phase=Failed (registry-sp000065.yaml 拷自 registry-robot.yaml 模板未替换真实容器名): dogfood artifact, 不 ship。P6 followup: registry 自动生成 from SP000065 真实容器名/systemd unit 名。
- PB1 real group_restart dogfood: 未跑 (robot host boundary), 留作机器人停机维护窗口。
Concerns (fold into P6):
- W5b self-reported P5-DOGFOOD-REPORT.md size as "~120" vs actual 136 (13% drift, non-fatal per V5)。

### P6 — ACCEPT (2026-08-18, V6 ACCEPT)

Worker: W6 delivered in ~2.5 min。Zero ESCALATEs。0 src/ changes / 0 SP000065 access / 0 build / 0 cargo test。
Verifier: V6 **ACCEPT** at `demo_app_service/crates/demo-app-lifecycle/reports/V6-VERDICT.md`. 10/10 claim PASS (~75s, well under 5-min cap)。Adversarial disprove via git forensics + report content grep + cross-confirmation against V5-VERDICT/P5-DOGFOOD-REPORT/decisions.md。
Decision: D-118 (roboctl wrap-only 固化) + D-119 (takeover CLOSED) landed。
Write-set: 1 file `reports/P6-ROBOCTL-WRAP-FINAL-REPORT.md` (67 lines, 6917B, ~7KB)。
P6 final form 声明: roboctl = wrap-only (P4 HTTP provider canonical interface, 不 replace / 不 deprecate)。
5 sections:
- §1: D-101 + user wrap-only 固化 (L8-17)
- §2: W5b PD2 PASS dogfood evidence 支持 wrap-only (L19-25)
- §3: 选了什么/牺牲了什么/何时破 — 3 trigger conditions for replace/deprecate (L27-39)
- §4: W5b 3 findings 处置 — GLIBC musl / nav2-member registry artifact / PB1 deferred (L41-45)
- §5: P0-P6 ACCEPT + test gate 40→99 + sha256 sentry final + handoffs CLOSED (L47-67)
Takeover closing: `handoffs/lifecycle-robot-takeover` 转 CLOSED。Followup (registry 自动生成 / PB1 real dogfood / fleet 扩展 / musl toolchain) 移交后续 task。
Memory: orchestrator add `feedback_musl_target_for_robot_dogfood` per W6 §4 recommendation。
Minor non-fatal (V6 noted): W6 self-reported size as "~4 KB" but actual is 6917B (~7KB, ~38% over target)。Non-blocking — 5 section structure intact, content dense。

### P7 — RE-DISPATCH (2026-08-18, V7 RE-DISPATCH → P7b fix-cycle)

Worker: W7 (kimi-k3, ~10.5 min wall clock, slightly over 10-min cap but `timeout 660s` did NOT trigger — worker ended naturally)。Ran full E2E on SP000065 with explicit user approval "全量 + 机器人安全" (维护窗口 / 周边无人 / 接受硬件风险)。
Verifier: V7 **RE-DISPATCH** at `demo_app_service/crates/demo-app-lifecycle/reports/V7-VERDICT.md`. 3 hard FAILs (claim 3/4/5), 7 PASS。
Test matrix: 8 svc × 3 op = 24 cells + group_restart robot-stack。
Verdict tally:
- 9 PASS (ethercat-oneshot start/restart + localization-robot-1-docker-exec start/restart + nav2-member 3/3 + rustbot-daemon-http-control stop/restart)
- 4 EXP-FAIL (INVALID_INTENT 矩阵合法 reject — Running×start / Stopped×stop)
- 6 DEGRADED (CLI accept + audit seq 但 host 未 actuate — 4 systemd system-scope polkit reject + 2 docker container restart-policy)
- 3 skipped (argo-zenoh-global stop/restart 控制面自保护 + 1 deferred)
- 1 group_restart SKIPPED (lifecycle_cli.rs:179 发 service_id,handlers.rs:684 读 group_id → MISSING_FIELD,0 src/ constraint 下 W7 ESCALATE)
3 hard FAILs (V7):
- Claim 3: Report §1-§5 结构 — W7 写成 §1-§6,§4=deployment issues,无独立 §5 contract 验证
- Claim 4: per-op 3方对照 thin — EVIDENCE.md `audit` 仅 6 hits / `pre-state` 仅 1 hit
- Claim 5: group_restart SKIPPED — `lifecycle_cli.rs:179` payload 固定 `service_id`,handler 读 `group_id` → MISSING_FIELD
Sha256 sentry 保持: `74b92f34...72b822` unchanged (D-117)。
0 src/ file changes (P7 dogfood,不改 src/)。HEAD=d2b3b9d。
Write-set 4 files: `examples/registry-sp000065-control.yaml` (159L) / `reports/P7-FULL-E2E-REPORT.md` (69L) / `reports/P7-DAEMON-LOG.txt` (672L) / `reports/P7-EVIDENCE.md` (210L)。
User decision: "开 P7b 修代码重跑" — 授权 P7b fix-cycle 修 `examples/lifecycle_cli.rs` (examples/,不是 src/) + 重跑 group_restart + 重整 reports。

### P7b — ACCEPT (2026-08-18, V7b ACCEPT)

Worker: W7b (kimi-k3, ~7.5 min wall clock, well under 15-min cap)。Fixed 3 V7 FAILs + re-ran group_restart + restructured reports。
Verifier: V7b **ACCEPT** at `demo_app_service/crates/demo-app-lifecycle/reports/V7b-VERDICT.md`. 10/10 claim PASS (~3 min, well under 5-min cap)。Adversarial disprove via SSH cross-check + git forensics + grep on 5 deliverables。
V7 3 FAILs resolution:
- Claim 3 (§1-§5 结构): W7b rewrote P7-FULL-E2E-REPORT.md to §1-§5 (§1 测试范围 / §2 per-op 矩阵 + §2.1 DEGRADED root cause / §3 group_restart / §4 cleanup / §5 contract 验证)。V7b PASS (5 L2 headers 语义对;format annotation: `## N.` vs prompt pattern `## §N` — V7b 按语义判 PASS,orchestrator 如认 strict 可 flip)。
- Claim 4 (per-op 3方对照 thin): W7b rewrote P7-EVIDENCE.md to 26 L2 headers (8 svc × 3 op + group_restart + summary) × 3 segments (audit + provider + pre/post)。audit 63 hits / pre-post 51 hits — 远超 ≥25/>>6/>>1 thresholds。V7b PASS。
- Claim 5 (group_restart SKIPPED): W7b modified `examples/lifecycle_cli.rs` 7 spots (+29/-9) 加 `--group` flag (parse_args arm L74 / payload group_id L195 / needs_group L152,158,190 / struct field L53 / help text L80-81 / comment L13-15)。Re-ran `lifecycle_cli group_restart --group robot-stack` on SP000065 with new daemon + new CLI binary。CLI payload `{"group_id":"robot-stack"}` ✓ (非 service_id)。Daemon accepted 4 members (`accepted:true, members_affected:4, member_order:[4 stopped + 4 started]`)。8 audit lines tagged `orig=be889dbd-4950-4231-a3a1-2943c4794a8e` ✓。V7b PASS。
4 members verdict (group_restart re-run):
- nav2-member: pre=no container → post=Up 3 min → PASS (docker start fan-out)
- localization-member: pre=no container → post=Up 3 min → PASS (docker start fan-out)
- rustbot-daemon-member: pre=inactive → post=inactive → DEGRADED (polkit reject)
- rustbot-monitor-member: pre=inactive → post=inactive → DEGRADED (polkit reject)
Open judgment (Claim 6 docker container state): W7b reported docker `nav2-dev` + `localization-robot-1` `Up 10 min` CreatedAt 2026-07-17/13 (~1 month ago) — `docker start` 复用 existing containers,group_restart start fan-out 预期语义,非 host damage。V7b **ACCEPT** (W7b argument)。
Sha256 sentry 保持: `74b92f34...72b822` unchanged (D-117)。
0 src/ file changes (W7b modified `examples/lifecycle_cli.rs` ONLY — examples/ 不是 src/,用户 approved)。HEAD=d2b3b9d (无新 commit)。
Write-set 5 files:
- `examples/lifecycle_cli.rs` (MODIFY, 250L, +29/-9 = 38 line diff)
- `reports/P7-FULL-E2E-REPORT.md` (REWRITE, 138L)
- `reports/P7-EVIDENCE.md` (REWRITE, 490L)
- `reports/P7-DAEMON-LOG.txt` (APPEND W7b session, 672→716L, +44)
- `reports/P7b-FIX-REPORT.md` (NEW delta, 101L)
Cleanup verified: daemon pkill ✓ / /tmp clean ✓ / no fixture unit ✓ / token 44B ✓ / argo-zenoh-global active ✓。
V7b ESCALATE: V7b-VERDICT.md self-reported 53L/1.7KB vs actual 32L/2.8KB — minor self-report drift (similar to V5/W6 pattern)。Claim 3 prompt pattern `^## §N` vs actual `## N.` — V7b judged semantic PASS。
Decision: D-120 (P7 RE-DISPATCH) + D-121 (P7b ACCEPT) landed。
P7b closing: lifecycle-robot-takeover 留 CLOSED 状态 (D-119),P7/P7b 是 bonus validation phase。Followup E (NEW): polkit systemd system-scope DEGRADED 修复 + docker restart-policy DEGRADED 修复 — 非本 crate src/ defect,交 NiicAdmin 或另开 worker。
