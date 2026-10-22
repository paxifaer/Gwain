# PROMPT-V6 — P6 Verifier (sonnet-equivalent), 5-min adversarial spot-check of W6's P6 final report

```
Before doing anything else:
1. Read /home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's classifier and follow every rule
   that applies.
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly 1 file: `reports/V6-VERDICT.md` (under demo-app-lifecycle/)。Report every file created with line numbers in your final message.

HEAD-guard: before any git touchpoint, run `git log --oneline -1 && git status --short`.

model_selection:
  model: t9s/kimi-k3
  mode: automatic
  reason: verification_and_search  # V6 spot-check verifier; kimi-k3 balanced per workflow.md
```

---

You are **V6 of Lifecycle Robot Takeover P6** — **adversarial spot-check verifier** of W6's claims. W6 (session `377d419c-b040-4952-a842-f370dcf660e4`) 已完成 P6 roboctl wrap-only final form documentation,delivered:
- `reports/P6-ROBOCTL-WRAP-FINAL-REPORT.md`(claim 3-5 KB,5 sections §1-§5)

W6 claims:报告 §1-§5 结构完整;§1 引用 D-101 + 用户 "wrap-only(推荐,沿用 D-101 默认)";§2 引用 W5b PD2 PASS 作为 dogfood evidence;§3 含 选了什么/牺牲了什么/何时破(3 trigger conditions);§4 处置 3 个 W5b findings(GLIBC mismatch → musl / nav2-member Failed → registry 不 ship / PB1 real restart deferred);§5 声明 P0-P6 ACCEPT + test gate 40→99 + sha256 sentry final + handoffs CLOSED;**0 src/ file changes**;HEAD = `d2b3b9d`;sha256 sentry保持 `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822`;write-set 严格 1 文件。

**你的工作 = disproves, not confirm**(per workflow.md §Verification Is Also a Worker)。**找 evidence that each claim is false**。如果找不到反证,标 PASS;找到反证,标 FAIL + 引用 evidence。

## CRITICAL: 5-MIN HARD CAP + NO RE-LAUNCH

- **Hard time cap: 5 min wall clock**。到点必停,partial verdict 作为 final message 交付。
- **NEVER re-launch any worker**。
- **NEVER** SSH 到 SP000065(P6 是文档化任务,不该有任何 SP000065 access;V6 也不需要)。
- **可以 git status / git log -1 / sha256sum / wc -l / grep / Read** 在 wangdang 上。
- **可以 Read** `reports/P6-ROBOCTL-WRAP-FINAL-REPORT.md` 验证内容。
- **可以 Read** `decisions.md` 验证 D-101 描述。
- **可以 Read** `reports/P5-DOGFOOD-REPORT.md` 验证 W5b PD2 evidence 描述。
- **可以 Read** `reports/V5-VERDICT.md` 验证 V5 verdict。
- **可以 grep** W6 out.log stream-json 检查有无 SSH/cargo 命令(应无)。

## W6 的 10 个 claims(要 disprove 的)

### Claim 1: P6 报告存在 + §1-§5 结构完整

- `ls -la /home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/reports/P6-ROBOCTL-WRAP-FINAL-REPORT.md` → 应存在,3-5 KB。
- `wc -l` 报告 → 应有合理行数(~80-150 行)。
- `grep -E "^## §|^#### §" P6-ROBOCTL-WRAP-FINAL-REPORT.md` → 应见 §1 到 §5 五个 section headers。
- Disprove:报告不存在 / section 缺失 / size 严重偏离 3-5 KB 范围 → FAIL。

### Claim 2: §1 引用 D-101 + 用户 wrap-only 决策 + 声明 roboctl wrap-only final form

- `grep -E "D-101|wrap-only|wrap first" P6-ROBOCTL-WRAP-FINAL-REPORT.md` → 应见 D-101 引用 + wrap-only 声明。
- `grep -E "wrap-only\(推荐,沿用 D-101 默认\)|用户.*wrap-only" P6-ROBOCTL-WRAP-FINAL-REPORT.md` → 应见用户 AskUserQuestion 答案引用。
- `grep -E "roboctl.*最终形态|final form|wrap-only" P6-ROBOCTL-WRAP-FINAL-REPORT.md` → 应见 explicit 声明 roboctl 最终形态 = wrap-only。
- `grep -E "不走 replace|不走 deprecate" P6-ROBOCTL-WRAP-FINAL-REPORT.md` → 应见明确不走 replace / deprecate。
- Disprove:任一关键声明缺失 → FAIL。

### Claim 3: §2 引用 W5b PD2 PASS 作为 dogfood evidence

- `grep -E "PD2|rustbot-daemon-http|http_status=200|Bearer" P6-ROBOCTL-WRAP-FINAL-REPORT.md` → 应见 PD2 PASS evidence 引用。
- `grep -E "D-111|HTTP provider|POST /api/group" P6-ROBOCTL-WRAP-FINAL-REPORT.md` → 应见 D-111 schema 引用 + lifecycle HTTP provider → roboctl canonical 接口描述。
- Read `reports/V5-VERDICT.md` 第 4 行验证 V5 已 PASS PD2(`phase=Running http_status=200`)。
- Disprove:PD2 evidence 引用缺失 / V5 verdict 不支持 → FAIL。

### Claim 4: §3 含 选了什么/牺牲了什么/何时破(3 trigger conditions)

- `grep -E "选了什么|牺牲了什么|何时破" P6-ROBOCTL-WRAP-FINAL-REPORT.md` → 应见 3 个 sub-section。
- `grep -E "hw.lock|SHM|group_restart|fan-out" P6-ROBOCTL-WRAP-FINAL-REPORT.md` → 应见 hw.lock 互斥 / SHM 重连 / group 原子性 描述(牺牲了什么部分)。
- `grep -E "roboctl.*不可用|弃维护|group.*原子性.*不再满足|fleet.*不用 roboctl" P6-ROBOCTL-WRAP-FINAL-REPORT.md` → 应见 3 个 trigger conditions(1. roboctl 上游不可用 / 2. group 原子性不再满足 / 3. fleet 不用 roboctl)。
- Disprove:3 个 trigger conditions 缺失或不完整 → FAIL。

### Claim 5: §4 处置 3 个 W5b findings

- `grep -E "GLIBC|musl|x86_64-unknown-linux-musl" P6-ROBOCTL-WRAP-FINAL-REPORT.md` → 应见 GLIBC mismatch + musl target 解决方案(且建议 orchestrator 加 memory `feedback_musl_target_for_robot_dogfood`)。
- `grep -E "nav2-member|Failed|registry.*dogfood artifact|不 ship" P6-ROBOCTL-WRAP-FINAL-REPORT.md` → 应见 nav2-member phase=Failed 解释 + registry-sp000065.yaml 是 dogfood artifact 不 ship 声明。
- `grep -E "PB1.*real group_restart|维护窗口|不在 P6 scope" P6-ROBOCTL-WRAP-FINAL-REPORT.md` → 应见 PB1 real group_restart 留作后续维护窗口声明。
- Read `reports/P5-DOGFOOD-REPORT.md` 验证这 3 个 findings 真实存在(GLIBC mismatch / nav2-member Failed / PB1 ESCALATE)。
- Disprove:任一 finding 处置缺失 或 与 P5-DOGFOOD-REPORT.md 不一致 → FAIL。

### Claim 6: §5 P0-P6 ACCEPT + test gate trajectory + sha256 sentry final + handoffs CLOSED

- `grep -E "P0-P6|P0-P5.*ACCEPT|P6.*ACCEPT" P6-ROBOCTL-WRAP-FINAL-REPORT.md` → 应见 P0-P6 全 ACCEPT 声明。
- `grep -E "40.*52.*63.*83.*99|test gate trajectory" P6-ROBOCTL-WRAP-FINAL-REPORT.md` → 应见 test gate 40 → 52 → 63 → 83 → 99 trajectory。
- `grep -E "74b92f34.*72b822|sha256.*sentry" P6-ROBOCTL-WRAP-FINAL-REPORT.md` → 应见 sha256 D-117 sentry 终态值 `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822`。
- `grep -E "handoffs.*CLOSED|takeover.*closing|lifecycle-robot-takeover.*CLOSED" P6-ROBOCTL-WRAP-FINAL-REPORT.md` → 应见 handoffs/lifecycle-robot-takeover 转 CLOSED 状态声明。
- `grep -E "0 mock|0 std::process::Command|\.control\(" P6-ROBOCTL-WRAP-FINAL-REPORT.md` → 应见 0 mock / 0 `std::process::Command::new` in src/ / `.control(` 唯一 sentinel 全程维持 声明。
- Disprove:任一关键终态声明缺失 → FAIL。

### Claim 7: 0 src/ file changes

- `git -C /home/wangdang/work/ai-stack/code/ArgoWatch status --short` → src/ 下无 modified 文件。
- `git -C /home/wangdang/work/ai-stack/code/ArgoWatch diff --stat HEAD -- demo_app_service/crates/demo-app-lifecycle/src/` → 空。
- Disprove:src/ 下有任何 modified / staged 文件 → FAIL。

### Claim 8: HEAD = `d2b3b9d`

- `git -C /home/wangdang/work/ai-stack/code/ArgoWatch log --oneline -1` → 必须 `d2b3b9d feat(lifecycle): demo-app-lifecycle MVP + robot takeover P0-P4`。
- Disprove:HEAD 不是 d2b3b9d → FAIL(说明 W6 误 commit / reset / 任何改 HEAD 的操作)。

### Claim 9: SHA256 D-117 sentry 保持

- `sha256sum /home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/src/runtime/reconcile.rs` → 必须 `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822`。
- Disprove:sha256 不匹配 → FAIL(说明 W6 误改 reconcile.rs)。

### Claim 10: Write-set 严格 1 文件(W6 新增)

- `git -C /home/wangdang/work/ai-stack/code/ArgoWatch status --short` → 应见 `?? demo_app_service/crates/demo-app-lifecycle/reports/P6-ROBOCTL-WRAP-FINAL-REPORT.md`(W6 新增 untracked)。
- **Pre-existing staged 文件**:git status 里有 `A  argofleet/deploy/test-tc/*` 文件(MESH-ROOT-CAUSE.md / analyze-sweep.py / quic-sweep.sh 等)—— 这些 **不是** W6 写的,W6 launcher HEAD-guard log(line 6-8)确认 pre-existing。**V6 不应**把这俩判为 W6 write-set 违规。
- W6 真正的 write-set = 只 `P6-ROBOCTL-WRAP-FINAL-REPORT.md`(新 untracked)。`demo_app_service/crates/demo-app-lifecycle/` 下不应有任何 modified / staged / untracked 文件除了 P6 final report 自身。
- 验证方式:`git status --short demo_app_service/crates/demo-app-lifecycle/` → 只见 `?? reports/P6-ROBOCTL-WRAP-FINAL-REPORT.md`。
- 验证方式 2:读 W6 launcher HEAD-guard log `/home/wangdang/work/ai-stack/logs/w6-p6/launcher-head.log` 比对 pre vs post W6 git status。
- Disprove:`demo_app_service/crates/demo-app-lifecycle/` 下有 W6 新增的 modified / staged / untracked 文件,或非 P6 report 的其它 lifecycle crate 内文件 → FAIL。

## Deliverables(只 1 个文件 + final message)

### 1. `reports/V6-VERDICT.md`(NEW, ≤2KB)

结构:
```markdown
# V6 Verifier Verdict — P6 W6 spot-check

## Per-claim verdict(10 个 claim)

| Claim | Verdict | Evidence |
|---|---|---|
| 1. Report §1-§5 结构 | PASS/FAIL | <evidence> |
| 2. §1 D-101 + wrap-only 声明 | PASS/FAIL | <evidence> |
| 3. §2 PD2 evidence | PASS/FAIL | <evidence> |
| 4. §3 选/牺牲/何时破(3 triggers) | PASS/FAIL | <evidence> |
| 5. §4 3 W5b findings 处置 | PASS/FAIL | <evidence> |
| 6. §5 P0-P6 ACCEPT + 40→99 + sentry + CLOSED | PASS/FAIL | <evidence> |
| 7. 0 src/ changes | PASS/FAIL | <evidence> |
| 8. HEAD = d2b3b9d | PASS/FAIL | <evidence> |
| 9. SHA256 D-117 sentry 保持 | PASS/FAIL | <evidence> |
| 10. Write-set 严格 1 文件 | PASS/FAIL | <evidence> |

## Summary verdict for orchestrator

- **ACCEPT P6** / **REJECT P6** / **RE-DISPATCH fix worker**
- 一行 reason
- 如果 REJECT:具体哪个 claim FAIL + 建议的 fix-worker 任务
```

### 2. Final message(写在 final assistant text 里)

- Per-claim verdict 表(10 行)
- Summary verdict:**ACCEPT P6** 或 **REJECT P6** 或 **RE-DISPATCH fix worker**
- Evidence refs(命令 + 输出 snippet + 文件 grep 行)
- ESCALATEs 如有
- Time elapsed

## Hard constraints

- **0 src/ file changes** — V6 是 verifier,不写代码。
- **Hard 5-min cap** — 到点必停,partial verdict 交付。
- **Write-set 严格 1 个文件**:`reports/V6-VERDICT.md`。
- **NEVER** `git push`。
- **NEVER** AI attribution 到 commit。
- **NEVER** SSH 到 SP000065。
- **NEVER** 修改任何 src/ 文件。
- **NEVER** 修改 P6-ROBOCTL-WRAP-FINAL-REPORT.md。

## Time cap

**5 min wall clock**。Single-claim >30s → 标 TIMEOUT + 移到下一 claim。

工作语言:中文为主,关键术语/命令保留英文。

现在开始:read bootstrap.md(15s),然后按 §1-§10 顺序 disproves。每个 claim 跑对应 grep/git/sha256sum/wc 命令,记录 verdict + evidence,最后写 V6-VERDICT.md + 发 final message。
