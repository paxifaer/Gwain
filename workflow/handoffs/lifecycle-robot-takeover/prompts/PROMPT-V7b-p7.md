# PROMPT-V7b — P7b Verifier (kimi-k3), 5-min adversarial spot-check of W7b's P7b fix

```
Before doing anything else:
1. Read /home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's classifier and follow every rule
   that applies.
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly 1 file: `reports/V7b-VERDICT.md` (under demo-app-lifecycle/)。Report every file created with line numbers in your final message.

HEAD-guard: before any git touchpoint, run `git log --oneline -1 && git status --short`.

model_selection:
  model: t9s/kimi-k3
  mode: automatic
  reason: verification_and_search  # V7b spot-check verifier; kimi-k3 balanced per workflow.md
```

---

You are **V7b of Lifecycle Robot Takeover P7b** — **adversarial spot-check verifier** of W7b's P7b fix claims。W7b (session `13dce8ed-bd27-43eb-8f65-aa3933118e63`) 已完成 P7b fix,delivered:
- `examples/lifecycle_cli.rs` (MODIFY — 7 spots, 250L total)
- `reports/P7-FULL-E2E-REPORT.md` (REWRITE — §1-§5, 138L)
- `reports/P7-EVIDENCE.md` (REWRITE — 25 subsections × 3 segments, 490L)
- `reports/P7-DAEMON-LOG.txt` (APPEND — W7b session, 716L)
- `reports/P7b-FIX-REPORT.md` (NEW — delta, 101L)

V7 (session `bc780eb6-4d4b-4279-a597-cd0f7e4d4c0a`) found **3 hard FAILs** on W7:
- Claim 3: Report §1-§5 结构 (W7 写成 §1-§6,无独立 §5 contract 验证)
- Claim 4: per-op 3方对照 evidence thin (audit 6 hits / pre-state 1 hit)
- Claim 5: group_restart SKIPPED (lifecycle_cli.rs:179 发 service_id,handler 读 group_id → MISSING_FIELD)

W7b claims 3 FAILs all DONE。**你的工作 = disproves, not confirm**。找 evidence that each fix is false / incomplete / breaks other claims。找不到反证 → PASS;找到反证 → FAIL + 引用 evidence。

## CRITICAL: 5-MIN HARD CAP + NO RE-LAUNCH

- **Hard time cap: 5 min wall clock**。到点必停,partial verdict 作为 final message 交付。
- **0 src/ file changes** — V7b 是 verifier,不写代码。
- **NEVER re-launch lifecycle daemon on SP000065**(W7b 已 cleanup pkill)。
- **NEVER run lifecycle_cli**(没有 daemon 在跑)。
- **可以 SSH 到 SP000065 做只读 cross-check**(`systemctl is-active`、`docker ps`、`ps -ef | grep demo-app-lifecycle-p7`、`ls -la /tmp/*p7*`)。
- **可以 grep / Read** 5 deliverables + V7-VERDICT.md。
- **可以 git status / git log -1 / git diff / sha256sum** 在 wangdang 上。
- **NEVER POST 启停任何 SP000065 现有 systemd 服务**(只读 cross-check)。
- **NEVER 修改 SP000065 任何 host 文件**。

## W7b 的 10 个 claims(要 disprove 的)

### Claim 1: 5 deliverable 文件存在 + 行数合理

- `ls -la` 5 文件都存在:
  - `examples/lifecycle_cli.rs` (250L)
  - `reports/P7-FULL-E2E-REPORT.md` (138L)
  - `reports/P7-EVIDENCE.md` (490L)
  - `reports/P7-DAEMON-LOG.txt` (716L)
  - `reports/P7b-FIX-REPORT.md` (101L)
- Disprove:任一文件缺失或行数严重偏离 → FAIL。

### Claim 2: lifecycle_cli.rs --group flag 真加(V7 FAIL 5 fix 的根因)

- `grep -n '"--group"' examples/lifecycle_cli.rs` → 应见 parse_args arm
- `grep -n 'group_id' examples/lifecycle_cli.rs` → 应见 payload logic(`{"group_id": g, "requested_by": "lifecycle_cli"}`)
- `grep -n 'needs_group' examples/lifecycle_cli.rs` → 应见 needs_group logic
- `grep -n 'group: Option<String>' examples/lifecycle_cli.rs` → 应见 struct Args field
- `git diff --stat HEAD -- examples/lifecycle_cli.rs` → 应见该文件 modified,+29/-9 line diff
- Disprove:任一 grep 无 hit / git diff 不含该文件 → FAIL(即 W7b 没真加 --group flag)。

### Claim 3: P7-FULL-E2E-REPORT.md §1-§5 结构(V7 FAIL 3 fix)

- `grep -E "^## §1|^## §2|^## §3|^## §4|^## §5" reports/P7-FULL-E2E-REPORT.md` → 应见 §1-§5 五个 section headers。
- **§4 必须是 cleanup**(非 deployment issues)。
- **§5 必须是 contract 验证**(0 src/ + HEAD + sha256 + write-set,非 cleanup+0src)。
- `grep -E "^## §6" reports/P7-FULL-E2E-REPORT.md` → 应**不**见 §6(V7 said W7 写成 §1-§6)。
- §1 测试范围 + §2 per-op 结果 + §3 group_restart + §4 cleanup + §5 contract 验证。
- §2 应有 §2.1 DEGRADED root cause analysis(V7 item 5 — 6 DEGRADED ops 文档化)。
- Disprove:§6 仍存在 / §4 不是 cleanup / §5 不是 contract 验证 / §2.1 缺失 → FAIL。

### Claim 4: P7-EVIDENCE.md per-(svc, op) 3方对照(V7 FAIL 4 fix)

- `grep -E "^## " reports/P7-EVIDENCE.md | wc -l` → 应 ≥25(8 svc × 3 op + 1 group_restart = 25 subsections)。
- `grep -E "Daemon audit|audit" reports/P7-EVIDENCE.md | wc -l` → 应 >>6(V7 said audit 6 hits — insufficient,P7b 应 25 subsections 每节 1+ audit hit = ≥25)。
- `grep -E "Pre:|Post:|pre-state|post-state|pre/post" reports/P7-EVIDENCE.md | wc -l` → 应 >>1(V7 said pre-state 1 hit — insufficient,P7b 应 25 subsections 每节 pre+post = ≥50)。
- 抽样 2-3 个 subsections 检查 3 segments 全(audit + provider response + pre/post state diff)。
- Disprove:<25 subsections / 3 segments 不全 / audit 或 pre/post count 仍低 → FAIL。

### Claim 5: group_restart robot-stack 真跑(V7 FAIL 5 fix)

- `grep -E "group_restart.*robot-stack|robot-stack.*group_restart" reports/P7-FULL-E2E-REPORT.md` → 应见执行记录(**非** SKIPPED,非 ESCALATE)。
- `grep -E '"group_id":"robot-stack"|"group_id": "robot-stack"' reports/P7-DAEMON-LOG.txt reports/P7-EVIDENCE.md` → 应见 CLI payload(非 service_id)。
- `grep -E 'lifecycle.audit.*group_restart|group_restart.*lifecycle.audit|orig=be889dbd' reports/P7-DAEMON-LOG.txt` → 应见 audit line(W7b said 8 audit lines tagged orig=be889dbd-4950-4231-a3a1-2943c4794a8e)。
- `grep -E "rustbot-daemon-member.*restart|rustbot-monitor-member.*restart|localization-member.*restart|nav2-member.*restart" reports/P7-FULL-E2E-REPORT.md reports/P7-EVIDENCE.md` → 应见 4 members 状态转换链。
- W7b verdict:2 PASS (localization-member + nav2-member docker start) + 2 DEGRADED (rustbot-daemon/monitor polkit reject)。
- Disprove:group_restart 仍 SKIPPED / CLI payload 仍 service_id / 4 members state 缺失 / 无 audit line → FAIL。

### Claim 6: cleanup 验证(W7b cleanup)

- SSH `ssh niic@192.168.100.100 'ps -ef | grep demo-app-lifecycle-p7 | grep -v grep'` → 应空(W7b cleanup 后 daemon 应 gone)。
- SSH `ssh niic@192.168.100.100 'ls -la /tmp/*p7* 2>/dev/null'` → 应空。
- SSH `ssh niic@192.168.100.100 'ls -la /etc/systemd/system/ | grep -E "p7|lifecycle|argowatch-takeover"'` → 应空。
- SSH `ssh niic@192.168.100.100 'cat ~/.config/roboctl/token | wc -c'` → 应 44 字节。
- `ssh niic@192.168.100.100 'systemctl is-active argo-zenoh-global'` → 应 `active`。
- `grep -E "service restore|pre-test state|restore.*pre|cleanup" reports/P7-FULL-E2E-REPORT.md` → 应见 service restore 记录。
- **Open judgment — docker containers state**:W7b 报告 localization-member + nav2-member docker containers `Up 3 minutes`(group_restart start fan-out 启的)。W7b argument: "intentional actuation from P7b group_restart start fan-out,恢复到 running baseline 是 group op 预期语义,非 host damage"。V7b 判断:
  - **接受**:group_restart 是 intended op,docker Up 是预期 post-state,非 cleanup regression
  - **拒绝**:W7b 应在 cleanup 时 stop 这 2 个 docker containers 恢复 pre-W7b baseline
  - **ESCALATE**:ambiguous,交 orchestrator
- Disprove:daemon 还在 / /tmp 有 p7 残留 / robot host 上有 fixture unit / token 改动 → FAIL。
- docker container Up 3 min 单独:标 PASS(接受 W7b argument)/ FAIL(拒绝)/ ESCALATE(ambiguous)— 在 verdict 里说明。

### Claim 7: 0 src/ file changes

- `git -C /home/wangdang/work/ai-stack/code/ArgoWatch diff --stat HEAD -- demo_app_service/crates/demo-app-lifecycle/src/` → 空。
- `git -C /home/wangdang/work/ai-stack/code/ArgoWatch status --short demo_app_service/crates/demo-app-lifecycle/src/` → 空。
- Disprove:src/ 下有任何 modified / staged 文件 → FAIL(W7b 误改 src/)。

### Claim 8: HEAD = `d2b3b9d`

- `git -C /home/wangdang/work/ai-stack/code/ArgoWatch log --oneline -1` → 必须 `d2b3b9d feat(lifecycle): demo-app-lifecycle MVP + robot takeover P0-P4`。
- Disprove:HEAD 不是 d2b3b9d → FAIL(W7b 误 commit / reset)。

### Claim 9: SHA256 D-117 sentry 保持

- `sha256sum /home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/src/runtime/reconcile.rs` → 必须 `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822`。
- Disprove:sha256 不匹配 → FAIL(W7b 误改 reconcile.rs)。

### Claim 10: Write-set 严格 5 文件(W7b 不超写)

- `git -C /home/wangdang/work/ai-stack/code/ArgoWatch status --short demo_app_service/crates/demo-app-lifecycle/` → 应见:
  - ` M examples/lifecycle_cli.rs` (W7b MODIFY)
  - `?? examples/registry-sp000065-control.yaml` (W7 P7 NEW,pre-existing)
  - `?? examples/registry-sp000065.yaml` (W5b P5 dogfood,pre-existing)
  - `?? reports/` (整个 reports/ 目录,包含 W7b 4 文件 + W7/V7/前序 worker 文件)
- `git -C /home/wangdang/work/ai-stack/code/ArgoWatch diff --stat HEAD -- demo_app_service/crates/demo-app-lifecycle/examples/` → 应只见 `lifecycle_cli.rs` 1 file modified。
- `demo_app_service/crates/demo-app-lifecycle/src/` 下不应有 W7b 新增 / modified 文件。
- Disprove:src/ 下有 modified / examples/ 下除 lifecycle_cli.rs 外有 modified / 其它非预期文件 → FAIL(W7b 误超出 write-set)。

## Deliverables(只 1 个文件 + final message)

### 1. `reports/V7b-VERDICT.md`(NEW, ≤2KB)

结构:
```markdown
# V7b Verifier Verdict — P7b W7b spot-check

## Per-claim verdict(10 个 claim)

| Claim | Verdict | Evidence |
|---|---|---|
| 1. 5 deliverable 文件存在 | PASS/FAIL | <evidence> |
| 2. lifecycle_cli.rs --group flag 真加 | PASS/FAIL | <evidence> |
| 3. Report §1-§5 结构 | PASS/FAIL | <evidence> |
| 4. per-op 3方对照 25 subsections × 3 segments | PASS/FAIL | <evidence> |
| 5. group_restart robot-stack 真跑 | PASS/FAIL | <evidence> |
| 6. cleanup 验证(含 docker container state 判断)| PASS/FAIL/ESCALATE | <evidence> |
| 7. 0 src/ changes | PASS/FAIL | <evidence> |
| 8. HEAD = d2b3b9d | PASS/FAIL | <evidence> |
| 9. SHA256 D-117 sentry 保持 | PASS/FAIL | <evidence> |
| 10. Write-set 严格 5 文件 | PASS/FAIL | <evidence> |

## V7 3 FAILs resolution verdict

| V7 FAIL | W7b fix | V7b verify |
|---|---|---|
| 3. Report §1-§5 结构 | DONE | PASS/FAIL |
| 4. per-op 3方对照 thin | DONE | PASS/FAIL |
| 5. group_restart SKIPPED | DONE | PASS/FAIL |

## Summary verdict for orchestrator

- **ACCEPT P7b** / **REJECT P7b** / **RE-DISPATCH fix worker**
- 一行 reason
- 如果 REJECT:具体哪个 claim FAIL + 建议的 fix-worker 任务
- 如果 ACCEPT:Lifecycle Robot Takeover P7b 终态 + takeover 终态 + followup A/B/C/D
```

### 2. Final message(写在 final assistant text 里)

- Per-claim verdict 表(10 行)
- V7 3 FAILs resolution 表(3 行)
- Summary verdict:**ACCEPT P7b** 或 **REJECT P7b** 或 **RE-DISPATCH fix worker**
- Evidence refs(命令 + 输出 snippet + 文件 grep 行)
- ESCALATEs 如有(docker container state judgment / 6 DEGRADED ops 归因 / V7b-VERDICT.md 大小等)
- Time elapsed

## Hard constraints

- **0 src/ file changes** — V7b 是 verifier,不写代码。
- **Hard 5-min cap** — 到点必停,partial verdict 交付。
- **Write-set 严格 1 个文件**:`reports/V7b-VERDICT.md`。
- **NEVER** `git push`。**NEVER** AI attribution 到 commit。
- **NEVER** re-launch lifecycle daemon on SP000065。
- **NEVER** POST 启停 robot-stack 或任何 SP000065 现有 systemd 服务。
- **NEVER** 修改 SP000065 任何 host 文件。

## Time cap

**5 min wall clock**。Single-claim >30s → 标 TIMEOUT + 移到下一 claim。

工作语言:中文为主,关键术语/命令保留英文。

现在开始:read bootstrap.md(15s cache),然后按 §1-§10 顺序 disproves。每个 claim 跑对应 SSH/grep/git/sha256sum 命令,记录 verdict + evidence,最后写 V7b-VERDICT.md + 发 final message。
