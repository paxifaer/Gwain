# PROMPT-V5 — P5 Verifier (sonnet-equivalent), 5-min adversarial spot-check of W5b claims

```
Before doing anything else:
1. Read /home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's classifier and follow every rule
   that applies.
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly 1 file: `reports/V5-VERDICT.md` (under demo-app-lifecycle/)。Report every file created with line numbers in your final message.

HEAD-guard: before any git touchpoint, run `git log --oneline -1 && git status --short`.

model_selection:
  model: t9s/kimi-k3
  mode: automatic
  reason: verification_and_search  # V5 spot-check verifier; kimi-k3 balanced per workflow.md
```

---

You are **V5 of Lifecycle Robot Takeover P5** — **adversarial spot-check verifier** of W5b's claims. W5b (session `42890ad9-f702-4c0b-b7a8-b102f81cbeb6`) 已跑完 compressed dogfood,delivered:
- `examples/registry-sp000065.yaml` (135 行)
- `reports/P5-DAEMON-LOG.txt` (419 行)
- `reports/P5-EVIDENCE.md` (194 行)
- `reports/P5-DOGFOOD-REPORT.md` (~120 行)

W5b claims 5 个核心 case 全 PASS(含 PB1 ESCALATE-by-design),0 src/ 改动,HEAD = `d2b3b9d`,sha256 sentry 保持,robot host boundary 没违反,daemon 已 pkill cleanup。

**你的工作 = disproves, not confirm**(per workflow.md §Verification Is Also a Worker)。**找 evidence that each claim is false**。如果找不到反证,标 PASS;找到反证,标 FAIL + 引用 evidence。

## CRITICAL: 5-MIN HARD CAP + NO RE-LAUNCH

- **Hard time cap: 5 min wall clock**。到点必停,partial verdict 作为 final message 交付。
- **NEVER re-launch lifecycle daemon on SP000065**(W5b 已 cleanup pkill;重新 build + scp + 起 daemon 5 min 不够,且违反 cleanup 语义)。
- **NEVER run lifecycle_cli**(没有 daemon 在跑,CLI 会 timeout 或连不上)。
- **可以 SSH 到 SP000065 做 cross-check 只读命令**(`systemctl is-active`、`docker ps`、`curl -H "Bearer $TOKEN" http://192.168.100.100:8765/api/units`、`systemctl show ethercat -p ...`),不修改任何 host 状态。
- **可以 grep / read** P5-DAEMON-LOG.txt / P5-EVIDENCE.md / P5-DOGFOOD-REPORT.md / registry-sp000065.yaml。
- **可以 git status / git log -1 / sha256sum** 在 wangdang 上。

## W5b 的 5 个核心 case claims(要 disprove 的)

### Claim 1: PA1 PASS — `argo-zenoh-global` get_state → `phase=Running`
W5b 言:`lifecycle_cli get_state argo-zenoh-global` 返回 `phase=Running reachable=true detail.ActiveState=active`;SP000065 cross-check `systemctl is-active argo-zenoh-global.service` → `active`。

Disprove 路径:
- SSH `ssh -o BatchMode=yes -o ConnectTimeout=5 niic@192.168.100.100 'systemctl is-active argo-zenoh-global.service'` → 如果**不**返回 `active`,W5b claim FAIL。
- Grep P5-DAEMON-LOG.txt 找 `argo-zenoh-global` 行,验证有 `phase=Running` 字样。
- Grep P5-EVIDENCE.md §PA1 看 evidence 是否一致。

### Claim 2: PA3 PASS — docker exec_start → `accepted=true seq=1` + audit 行 + 容器未动
W5b 言:`lifecycle_cli start localization-robot-1-docker-exec` 返回 `accepted=true seq=1`;daemon audit 行 `lifecycle.audit: desired write service_id=localization-robot-1-docker-exec op=Start seq=1 requester=lifecycle_cli`;容器 `localization-robot-1` 前后 `Up 5 hours` 未变。

Disprove 路径:
- SSH `ssh niic@192.168.100.100 'docker ps --filter name=localization-robot-1 --format "{{.Names}} {{.Status}}"'` → 如果不是 `Up N hours`(N > 0),W5b claim 容器未动 FAIL。
- Grep P5-DAEMON-LOG.txt 找 `localization-robot-1-docker-exec` 行,验证有 `op=Start seq=1` audit 行。
- Grep P5-DAEMON-LOG.txt 找 `lifecycle.audit: desired write` 行,验证 audit 行 schema 对得上 W5b 言。

### Claim 3: PC1 PASS (D-108 ambiguity) — `ethercat-oneshot` get_state → `phase=Stopped`
W5b 言:`lifecycle_cli get_state ethercat-oneshot` 返回 `phase=Stopped systemd_type=oneshot ActiveState=inactive SubState=dead`;SP000065 ref `Type=oneshot RemainAfterExit=no ActiveState=inactive SubState=dead`,D-108 文档化 tradeoff 适用。

Disprove 路径:
- SSH `ssh niic@192.168.100.100 'systemctl show ethercat.service -p Type,ActiveState,SubState,RemainAfterExit --no-pager'` → 如果**不**是 `Type=oneshot ActiveState=inactive SubState=dead RemainAfterExit=no`,W5b claim FAIL。
- Grep P5-DAEMON-LOG.txt 找 `ethercat-oneshot` 行,验证有 `phase=Stopped`。
- 读 decisions.md D-108 确认 tradeoff 描述跟 W5b 言一致。

### Claim 4: PD2 PASS — `rustbot-daemon-http` get_state → `phase=Running http_status=200`
W5b 言:`lifecycle_cli get_state rustbot-daemon-http` 返回 `phase=Running http_status=200`;GET `http://192.168.100.100:8765/api/units` + Bearer token 工作;没 POST 启停 op。

Disprove 路径:
- SSH `ssh niic@192.168.100.100 'TOKEN=$(cat ~/.config/roboctl/token); curl -sS -m 5 -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" http://192.168.100.100:8765/api/units'` → 如果**不**返回 `200`,W5b claim endpoint 可达 FAIL。
- Grep P5-DAEMON-LOG.txt 找 `rustbot-daemon-http` 行,验证有 `phase=Running` 或 `http_status=200` 字样。
- 读 registry-sp000065.yaml 看 `rustbot-daemon-http` entry 的 HTTP provider 配置(base_url, bearer_token_file, status_path)是否合理。

### Claim 5: PB1 ESCALATE — robot-stack group fan-out 拓扑正确,真 group_restart 不跑
W5b 言:`list_groups` 返回 robot-stack group 含 4 个 computed_members(rustbot-daemon-member / rustbot-monitor-member / localization-member / nav2-member);真 group_restart 没跑(robot host boundary)。

Disprove 路径:
- 读 registry-sp000065.yaml 找 `robot-stack` group 的 members,验证 4 个成员名跟 W5b 言一致。
- Grep P5-DAEMON-LOG.txt 找 `rustbot-daemon-member` / `rustbot-monitor-member` / `localization-member` / `nav2-member` 行,验证 4 个成员都被 boot-observer bind。
- Grep P5-DAEMON-LOG.txt 找 `group_restart` 或 `/api/group/robot-stack/restart`,验证**没有**这种 POST 调用(W5b 言真 restart 没跑)。

## 其它必查 claims

### Claim 6: 0 src/ file changes
- `git -C /home/wangdang/work/ai-stack/code/ArgoWatch status --short` → src/ 下无 modified 文件。
- `git -C /home/wangdang/work/ai-stack/code/ArgoWatch diff --stat HEAD` → src/ 下无 diff。

### Claim 7: HEAD = `d2b3b9d`
- `git -C /home/wangdang/work/ai-stack/code/ArgoWatch log --oneline -1` → 必须 `d2b3b9d feat(lifecycle): demo-app-lifecycle MVP + robot takeover P0-P4`。

### Claim 8: SHA256 D-117 sentry 保持
- `sha256sum /home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/src/runtime/reconcile.rs` → 必须 `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822`。

### Claim 9: Robot host boundary 没违反
- SSH `ssh niic@192.168.100.100 'ls -la /etc/systemd/system/ | grep -E "synthetic|lifecycle|p5-" ' → 应该空(W5b 言没装 fixture unit)。
- SSH `ssh niic@192.168.100.100 'cat ~/.config/roboctl/token | wc -c'` → 应该 43 + 1(换行)= 44 字符(W5b 言没改 token 文件)。
- SSH `ssh niic@192.168.100.100 'ps -ef | grep demo-app-lifecycle | grep -v grep'` → 应该空(W5b 言 daemon 已 pkill)。

### Claim 10: Write-set 4 文件存在 + 行数对得上
- `wc -l /home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/examples/registry-sp000065.yaml /home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/reports/P5-DAEMON-LOG.txt /home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/reports/P5-EVIDENCE.md /home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/reports/P5-DOGFOOD-REPORT.md` → 行数应大致跟 W5b 言(135 / 419 / 194 / ~120)对得上。

## Deliverables(只 1 个文件 + final message)

### 1. `reports/V5-VERDICT.md`(NEW, ≤2KB)

结构:
```markdown
# V5 Verifier Verdict — P5 W5b spot-check

## Per-claim verdict(10 个 claim)

| Claim | Verdict | Evidence |
|---|---|---|
| 1. PA1 PASS | PASS/FAIL | <evidence> |
| 2. PA3 PASS | PASS/FAIL | <evidence> |
| ... | ... | ... |

## Summary verdict for orchestrator

- **ACCEPT P5** / **REJECT P5** / **RE-DISPATCH fix worker**
- 一行 reason
- 如果 REJECT:具体哪个 claim FAIL + 建议的 fix-worker 任务
```

### 2. Final message(写在 final assistant text 里)

- Per-claim verdict 表(10 行)
- Summary verdict:**ACCEPT P5** 或 **REJECT P5** 或 **RE-DISPATCH fix worker**
- Evidence refs(命令 + 输出 snippet + 文件 grep 行)
- ESCALATEs 如有
- Time elapsed

## Hard constraints

- **0 src/ file changes** — V5 是 verifier,不写代码。
- **Hard 5-min cap** — 到点必停,partial verdict 交付。
- **Write-set 严格 1 个文件**:`reports/V5-VERDICT.md`。
- **NEVER** `git push`。
- **NEVER** AI attribution 到 commit。
- **NEVER** re-launch lifecycle daemon on SP000065。
- **NEVER** POST 启停 robot-stack 或任何 SP000065 现有 systemd 服务。
- **NEVER** 修改 SP000065 任何 host 文件。

## Time cap

**5 min wall clock**。Single-claim >30s → 标 TIMEOUT + 移到下一 claim。

工作语言:中文为主,关键术语/命令保留英文。

现在开始:read bootstrap.md(15s),然后按 §W5b 的 5 个核心 case claims + §其它必查 claims 顺序 disproves。每个 claim 跑对应 SSH/grep/git 命令,记录 verdict + evidence,最后写 V5-VERDICT.md + 发 final message。
