# PROMPT-V7 — P7 Verifier (sonnet-equivalent), 5-min adversarial spot-check of W7's P7 full E2E report

```
Before doing anything else:
1. Read /home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's classifier and follow every rule
   that applies.
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly 1 file: `reports/V7-VERDICT.md` (under demo-app-lifecycle/)。Report every file created with line numbers in your final message.

HEAD-guard: before any git touchpoint, run `git log --oneline -1 && git status --short`.

model_selection:
  model: t9s/kimi-k3
  mode: automatic
  reason: verification_and_search  # V7 spot-check verifier; kimi-k3 balanced per workflow.md
```

---

You are **V7 of Lifecycle Robot Takeover P7** — **adversarial spot-check verifier** of W7's claims。W7 (session `44dd9ccd-6d82-4aa8-9fd1-d77be3bd93c7`) 已完成 P7 full E2E real-robot control verbs test on SP000065,delivered:
- `examples/registry-sp000065-control.yaml`(NEW)
- `reports/P7-FULL-E2E-REPORT.md`(NEW)
- `reports/P7-DAEMON-LOG.txt`(NEW)
- `reports/P7-EVIDENCE.md`(NEW)

W7 claims:8+ service × 3 op (start/stop/restart) + 1 group_restart robot-stack 全跑;per-op 3方对照 (daemon audit + roboctl/systemd response + pre/post state diff);cleanup 完整 (daemon pkill + service restore + tmp 清理 + 0 SP000065 host file mods);**0 src/ file changes**;HEAD = `d2b3b9d`;sha256 sentry 保持 `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822`;write-set 严格 4 文件。

**你的工作 = disproves, not confirm**(per workflow.md §Verification Is Also a Worker)。**找 evidence that each claim is false**。如果找不到反证,标 PASS;找到反证,标 FAIL + 引用 evidence。

## CRITICAL: 5-MIN HARD CAP + NO RE-LAUNCH

- **Hard time cap: 5 min wall clock**。到点必停,partial verdict 作为 final message 交付。
- **NEVER re-launch lifecycle daemon on SP000065**(W7 已 cleanup pkill)。
- **NEVER run lifecycle_cli**(没有 daemon 在跑)。
- **可以 SSH 到 SP000065 做只读 cross-check**(`systemctl is-active <svc>`、`docker ps`、`curl GET /api/units`、`ps -ef | grep demo-app-lifecycle-p7`)。
- **可以 grep / Read** P7-FULL-E2E-REPORT.md / P7-DAEMON-LOG.txt / P7-EVIDENCE.md / registry-sp000065-control.yaml。
- **可以 git status / git log -1 / sha256sum** 在 wangdang 上。
- **NEVER POST 启停任何 SP000065 现有 systemd 服务**(只读 cross-check)。
- **NEVER 修改 SP000065 任何 host 文件**。

## W7 的 10 个 claims(要 disprove 的)

### Claim 1: 4 deliverable 文件存在

- `ls -la` 4 个文件都存在:
  - `examples/registry-sp000065-control.yaml`
  - `reports/P7-FULL-E2E-REPORT.md`
  - `reports/P7-DAEMON-LOG.txt`
  - `reports/P7-EVIDENCE.md`
- `wc -l` 4 文件行数合理(control yaml ~150-200L,report ~5-10 KB,daemon log 取决于 op 数量,evidence ~150-300L)。
- Disprove:任一文件缺失或行数严重偏离 → FAIL。

### Claim 2: control registry 全 service expose [lifecycle, status]

- `grep -E "expose: \[lifecycle, status\]" registry-sp000065-control.yaml` → 应见 8+ 处。
- `grep -E "expose: \[status\]" registry-sp000065-control.yaml` → 应**不**见 status-only(全 expand 到 lifecycle, status)。
- 验证 4 group 至少 `robot-stack` 是 `expose: [lifecycle, status]`。
- 验证 HTTP provider entry (`rustbot-daemon-http-control`) 含 `start.url` / `stop.url` / `restart.url` 配置。
- Disprove:有 service 仍 status-only / HTTP entry 缺 control verb selector → FAIL。

### Claim 3: P7-FULL-E2E-REPORT.md §1-§5 结构完整

- `grep -E "^## §|^#### §" P7-FULL-E2E-REPORT.md` → 应见 §1 到 §5 五个 section headers。
- §1 测试范围 + §2 per-op 结果 + §3 group_restart + §4 cleanup + §5 contract 验证。
- Disprove:任一 section 缺失 → FAIL。

### Claim 4: 测试矩阵覆盖 8+ service × 3 op

- `grep -E "start|stop|restart" P7-FULL-E2E-REPORT.md` 应见 8+ service 各有 3 op 记录。
- `grep -E "PASS|FAIL|TIMEOUT|SKIP" P7-FULL-E2E-REPORT.md` → 统计 verdict 数,应 ≥ 24(8 service × 3 op)。
- Per-op evidence 应包含 3 方对照:`lifecycle.audit` log + roboctl/systemd response + pre/post state diff。
- Disprove:测试矩阵 < 24 ops 或 per-op evidence 缺 3 方对照 → FAIL。

### Claim 5: group_restart robot-stack 真跑(非 skip)

- `grep -E "group_restart.*robot-stack|robot-stack.*group_restart" P7-FULL-E2E-REPORT.md` → 应见 group_restart 执行记录。
- `grep -E "robot-stack.*PASS|robot-stack.*FAIL|robot-stack.*TIMEOUT" P7-FULL-E2E-REPORT.md` → 应见 verdict。
- `grep -E "4 members|rustbot-daemon-member.*restart|rustbot-monitor-member.*restart|localization-member.*restart|nav2-member.*restart" P7-FULL-E2E-REPORT.md` → 应见 4 members 状态转换链。
- Disprove:group_restart skip 或 4 members 状态转换缺失 → FAIL(除非 W7 ESCALATE 说明 lifecycle 不支持 group HTTP POST 路径,改用 systemd-direct fallback 测试 4 members — 这种 fallback 应有记录)。

### Claim 6: cleanup 验证(daemon pkill + service restore + tmp 清理 + 0 SP000065 host file mods)

- SSH `ssh niic@192.168.100.100 'ps -ef | grep demo-app-lifecycle-p7 | grep -v grep'` → 应空(W7 cleanup 后 daemon 应 gone)。
- SSH `ssh niic@192.168.100.100 'ls -la /tmp/*p7* 2>/dev/null'` → 应空(W7 清理 /tmp/demo-app-lifecycle-p7 + /tmp/registry-sp000065-control.yaml + /tmp/p7-daemon.log)。
- SSH `ssh niic@192.168.100.100 'ls -la /etc/systemd/system/ | grep -E "p7|lifecycle|argowatch-takeover"'` → 应空(W7 没装 fixture unit on robot host)。
- SSH `ssh niic@192.168.100.100 'cat ~/.config/roboctl/token | wc -c'` → 应 44 字节(W7 没改 token 文件)。
- `grep -E "service restore|pre-test state|restore.*pre" P7-FULL-E2E-REPORT.md` → 应见 service restore 记录。
- Disprove:daemon 还在跑 / /tmp 有 p7 残留 / robot host 上有 fixture unit / token 改动 → FAIL。

### Claim 7: 0 src/ file changes

- `git -C /home/wangdang/work/ai-stack/code/ArgoWatch status --short demo_app_service/crates/demo-app-lifecycle/src/` → 空。
- `git -C /home/wangdang/work/ai-stack/code/ArgoWatch diff --stat HEAD -- demo_app_service/crates/demo-app-lifecycle/src/` → 空。
- Disprove:src/ 下有任何 modified / staged 文件 → FAIL。

### Claim 8: HEAD = `d2b3b9d`

- `git -C /home/wangdang/work/ai-stack/code/ArgoWatch log --oneline -1` → 必须 `d2b3b9d feat(lifecycle): demo-app-lifecycle MVP + robot takeover P0-P4`。
- Disprove:HEAD 不是 d2b3b9d → FAIL(W7 误 commit / reset)。

### Claim 9: SHA256 D-117 sentry 保持

- `sha256sum /home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/src/runtime/reconcile.rs` → 必须 `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822`。
- Disprove:sha256 不匹配 → FAIL(W7 误改 reconcile.rs)。

### Claim 10: Write-set 严格 4 文件

- `git -C /home/wangdang/work/ai-stack/code/ArgoWatch status --short demo_app_service/crates/demo-app-lifecycle/` → 应只见 4 个新文件:
  - `?? examples/registry-sp000065-control.yaml`
  - `?? reports/P7-FULL-E2E-REPORT.md`
  - `?? reports/P7-DAEMON-LOG.txt`
  - `?? reports/P7-EVIDENCE.md`
- `demo_app_service/crates/demo-app-lifecycle/` 下不应有 W7 新增的其它文件(尤其 src/ 下)。
- Disprove:有其它文件改动 → FAIL(W7 误超出 write-set)。

## Deliverables(只 1 个文件 + final message)

### 1. `reports/V7-VERDICT.md`(NEW, ≤2KB)

结构:
```markdown
# V7 Verifier Verdict — P7 W7 spot-check

## Per-claim verdict(10 个 claim)

| Claim | Verdict | Evidence |
|---|---|---|
| 1. 4 deliverable 文件存在 | PASS/FAIL | <evidence> |
| 2. control registry 全 service lifecycle expose | PASS/FAIL | <evidence> |
| 3. Report §1-§5 结构 | PASS/FAIL | <evidence> |
| 4. 测试矩阵 8+ service × 3 op + 3方对照 | PASS/FAIL | <evidence> |
| 5. group_restart robot-stack 真跑 | PASS/FAIL | <evidence> |
| 6. cleanup 验证 | PASS/FAIL | <evidence> |
| 7. 0 src/ changes | PASS/FAIL | <evidence> |
| 8. HEAD = d2b3b9d | PASS/FAIL | <evidence> |
| 9. SHA256 D-117 sentry 保持 | PASS/FAIL | <evidence> |
| 10. Write-set 严格 4 文件 | PASS/FAIL | <evidence> |

## Summary verdict for orchestrator

- **ACCEPT P7** / **REJECT P7** / **RE-DISPATCH fix worker**
- 一行 reason
- 如果 REJECT:具体哪个 claim FAIL + 建议的 fix-worker 任务
```

### 2. Final message(写在 final assistant text 里)

- Per-claim verdict 表(10 行)
- Summary verdict:**ACCEPT P7** 或 **REJECT P7** 或 **RE-DISPATCH fix worker**
- Evidence refs(命令 + 输出 snippet + 文件 grep 行)
- ESCALATEs 如有
- Time elapsed

## Hard constraints

- **0 src/ file changes** — V7 是 verifier,不写代码。
- **Hard 5-min cap** — 到点必停,partial verdict 交付。
- **Write-set 严格 1 个文件**:`reports/V7-VERDICT.md`。
- **NEVER** `git push`。
- **NEVER** AI attribution 到 commit。
- **NEVER** re-launch lifecycle daemon on SP000065。
- **NEVER** POST 启停 robot-stack 或任何 SP000065 现有 systemd 服务。
- **NEVER** 修改 SP000065 任何 host 文件。

## Time cap

**5 min wall clock**。Single-claim >30s → 标 TIMEOUT + 移到下一 claim。

工作语言:中文为主,关键术语/命令保留英文。

现在开始:read bootstrap.md(15s),然后按 §1-§10 顺序 disproves。每个 claim 跑对应 SSH/grep/git/sha256sum 命令,记录 verdict + evidence,最后写 V7-VERDICT.md + 发 final message。
