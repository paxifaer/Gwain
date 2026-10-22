# PROMPT-W7b — P7b Fix Worker (kimi-k3), 15-min fix + re-run for V7 RE-DISPATCH

```
Before doing anything else:
1. Read /home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's classifier and follow every rule
   that applies.
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly 5 files (all under demo-app-lifecycle/):
   - examples/lifecycle_cli.rs (MODIFY — add --group flag for group_* ops)
   - reports/P7-FULL-E2E-REPORT.md (REWRITE — §1-§5 structure)
   - reports/P7-EVIDENCE.md (REWRITE — per-(svc, op) 3方对照)
   - reports/P7-DAEMON-LOG.txt (APPEND — W7b session marker + new log)
   - reports/P7b-FIX-REPORT.md (NEW — delta summary)
   Report every file created/modified with line numbers in your final message.

HEAD-guard: before any git touchpoint, run `git log --oneline -1 && git status --short`.

model_selection:
  model: t9s/kimi-k3
  mode: automatic
  reason: deployment_debugging  # P7b fix + re-run — kimi-k3 balanced per workflow.md
```

---

You are **W7b of Lifecycle Robot Takeover P7b** — **fix worker** for V7 RE-DISPATCH verdict on W7's P7 full E2E。V7 (session `bc780eb6-4d4b-4279-a597-cd0f7e4d4c0a`) found **3 hard FAILs**:

| Claim | V7 FAIL | Root cause |
|---|---|---|
| 3 | Report §1-§5 结构 | W7 写成 §1-§6,§4=deployment issues,§5=cleanup+0src；无独立 §5 contract 验证 |
| 4 | 8+ svc × 3 op + 3方对照 | 24 cells 硬 PASS 9/24,EVIDENCE.md `audit` 仅 6 hits / `pre-state` 仅 1 hit — 不足以支撑 per-op 3方对照 |
| 5 | group_restart robot-stack 真跑 | §3 首行 "SKIPPED — ESCALATE";`lifecycle_cli.rs:179` payload 固定 `service_id`,但 `handlers.rs:684` 读 `group_id` |

**用户 explicit approval**: "开 P7b 修代码重跑" — 修 `lifecycle_cli.rs` 加 `--group` flag + 重跑 `group_restart robot-stack` + 重整 reports。0 src/ constraint loosened for `examples/lifecycle_cli.rs` ONLY (examples/ 不是 src/)。

## CRITICAL: 15-MIN HARD CAP + NO PARTIAL RETURNS

- **Hard time cap: 15 min wall clock**。到点必停,partial 状态作为 final message 交付。
- **禁止**返回 plan / outline / status update / "next I'll ..."。Work continuously 直到 5 个 deliverable 文件写完 + final message 交付。

## Pre-known facts (inline, do not re-verify — from W7 P7 + V7)

- SP000065 = 192.168.100.100, SSH `niic@192.168.100.100` (key-based auth via `niic_26` alias)
- roboctl daemon binds `192.168.100.100:8765` (NOT 0.0.0.0), Bearer token at `/home/niic/.config/roboctl/token` (44B incl newline)
- roboctl API: `GET /api/units`, `POST /api/unit/<name>/{start,stop,restart}`, `POST /api/group/<name>/{start,stop,restart}` (Bearer-required, bare name 无 `.service` 后缀)
- musl build cache hit ~30s (W7 已 build 全 target/x86_64-unknown-linux-musl/release/)
- daemon env: `FLEET_ID=p7`, `BOT_NAME=sp000065`, `REGISTRY_YAML=/tmp/registry-sp000065-control.yaml`, `RUST_LOG=info`
- W7 P7 deliverables 已存在(读不修 except reports/):
  - `examples/registry-sp000065-control.yaml` (159L,expose `[lifecycle, status]` all 8 svcs + HTTP provider D-111)
  - `reports/P7-FULL-E2E-REPORT.md` (69L,§1-§6 — V7 要 §1-§5)
  - `reports/P7-EVIDENCE.md` (210L,audit 6 hits / pre-state 1 hit — V7 要 per-(svc,op) 3方对照)
  - `reports/P7-DAEMON-LOG.txt` (672L,W7 raw daemon log)
- `examples/lifecycle_cli.rs` bug 确认:
  - Line 44-52 `struct Args`:无 `group` field
  - Line 54-97 `parse_args`:无 `--group` flag
  - Line 78-83 help text:无 `--group`
  - Line 145-148 `needs_service`:只 exempt `list_state | list_groups`,group_* 仍要求 `--service`
  - Line 178-181 payload:永远发 `service_id`,group_* op 时 handler 读 `group_id` → MISSING_FIELD
- `src/handlers.rs` line 683-693 `handle_lifecycle_group_restart`:读 `req.payload.get("group_id").as_str()`,缺则返回 `MISSING_FIELD "payload missing required field 'group_id' (string)"`
- 6 DEGRADED ops(V7 item 5 — 非本 crate defect,交 NiicAdmin 或另开 worker):
  - 4 systemd system-scope: `rustbot-daemon-member` start/restart + `rustbot-monitor-member` start/restart — niic-user polkit 规则对 hardware-tagged unit 的 StartUnit 无权限
  - 2 docker container: `localization-member` stop/restart — docker restart-policy `always` 或 stop_container SIGKILL timing
- 3 skipped ops: `argo-zenoh-global` stop/restart — 控制面自保护(stop zenoh 切断 daemon 自己的 argo-dds session)
- 4 EXP-FAIL ops: INVALID_INTENT 矩阵合法 reject(Running×start 或 Stopped×stop)
- 9 PASS ops: ethercat-oneshot start/restart + localization-robot-1-docker-exec start/restart + nav2-member 3/3 + rustbot-daemon-http-control stop/restart

## Task

### Step 1: Modify `examples/lifecycle_cli.rs` (surgical, ~60s)

**只动这 7 处,不动其它任何行**:

1. **Line 13** comment: Ops 列表加 `group_start | group_stop | group_restart`
2. **Line 17-26** flags doc: 加一行 `--group <gid>           group_id to target (required for group_* ops).`
3. **Line 44-52** `struct Args`: 加 `group: Option<String>,` field(在 `service` 之后)
4. **Line 54-97** `parse_args`:
   - 加 `let mut group = None;`(在 `let mut service = None;` 之后)
   - 在 `--service => ...` 之后加 `"--group" => group = Some(it.next().context("--group requires a value")?),`
   - 末尾 `Ok(Args { ... })` 加 `group,` field
5. **Line 78-83** help text: usage line加 `[--group <gid>]`
6. **Line 145-148** `needs_service` 逻辑:
   ```rust
   let needs_service = !matches!(op, "list_state" | "list_groups" | "group_start" | "group_stop" | "group_restart");
   let needs_group = matches!(op, "group_start" | "group_stop" | "group_restart");
   if needs_service && args.service.is_none() && !needs_group {
       bail!("--service is required for op '{op}'");
   }
   if needs_group && args.group.is_none() {
       bail!("--group is required for op '{op}'");
   }
   ```
7. **Line 178-181** payload 逻辑:
   ```rust
   let payload = if needs_group {
       let g = args.group.as_ref().context("--group required for group_* op")?;
       serde_json::json!({ "group_id": g, "requested_by": "lifecycle_cli" })
   } else {
       match &args.service {
           Some(s) => serde_json::json!({ "service_id": s, "requested_by": "lifecycle_cli" }),
           None => serde_json::json!({ "requested_by": "lifecycle_cli" }),
       }
   };
   ```

**绝对禁止**修改 lifecycle_cli.rs 其它行 / 其它 examples/ 文件 / 任何 src/ 文件。

### Step 2: Build + scp + 启 daemon (~90s)

```bash
cd /home/wangdang/work/ai-stack/code/ArgoWatch
# build CLI (musl, cache hit ~30s)
cargo build -p demo-app-lifecycle --release --target x86_64-unknown-linux-musl --example lifecycle_cli 2>&1 | tail -5
ls -la target/x86_64-unknown-linux-musl/release/examples/lifecycle_cli
# build daemon (musl, cache hit ~10s — daemon unchanged)
cargo build -p demo-app-lifecycle --release --target x86_64-unknown-linux-musl 2>&1 | tail -3
ls -la target/x86_64-unknown-linux-musl/release/demo-app-lifecycle

# scp CLI + daemon + registry to SP000065
scp target/x86_64-unknown-linux-musl/release/examples/lifecycle_cli niic@192.168.100.100:/tmp/lifecycle_cli-p7b
scp target/x86_64-unknown-linux-musl/release/demo-app-lifecycle niic@192.168.100.100:/tmp/demo-app-lifecycle-p7b
scp examples/registry-sp000065-control.yaml niic@192.168.100.100:/tmp/registry-sp000065-control.yaml

# start daemon (use W7 registry — expose [lifecycle, status] all svcs)
ssh niic@192.168.100.100 'FLEET_ID=p7 BOT_NAME=sp000065 REGISTRY_YAML=/tmp/registry-sp000065-control.yaml RUST_LOG=info nohup /tmp/demo-app-lifecycle-p7b > /tmp/p7b-daemon.log 2>&1 &'
sleep 3
ssh niic@192.168.100.100 'ps -ef | grep demo-app-lifecycle-p7b | grep -v grep'  # verify daemon alive
```

### Step 3: Re-run group_restart robot-stack (~90s)

```bash
# Pre-state snapshot of 4 robot-stack members
ssh niic@192.168.100.100 'systemctl show rustbot-daemon-member -p ActiveState,SubState,Type 2>&1'
ssh niic@192.168.100.100 'systemctl show rustbot-monitor-member -p ActiveState,SubState,Type 2>&1'
ssh niic@192.168.100.100 'docker ps --filter name=localization-member --format "{{.Names}} {{.Status}}" 2>&1'
ssh niic@192.168.100.100 'docker ps --filter name=nav2-member --format "{{.Names}} {{.Status}}" 2>&1'

# Run group_restart with NEW --group flag (P7b fix)
ssh niic@192.168.100.100 'FLEET_ID=p7 BOT_NAME=sp000065 /tmp/lifecycle_cli-p7b --op group_restart --group robot-stack --timeout-secs 30' 2>&1 | tee /tmp/p7b-grep.out

# Post-state snapshot of 4 members
ssh niic@192.168.100.100 'systemctl show rustbot-daemon-member -p ActiveState,SubState 2>&1'
ssh niic@192.168.100.100 'systemctl show rustbot-monitor-member -p ActiveState,SubState 2>&1'
ssh niic@192.168.100.100 'docker ps --filter name=localization-member --format "{{.Names}} {{.Status}}" 2>&1'
ssh niic@192.168.100.100 'docker ps --filter name=nav2-member --format "{{.Names}} {{.Status}}" 2>&1'

# Grep daemon audit log for group_restart + 4 members
ssh niic@192.168.100.100 'grep -E "group_restart|robot-stack|rustbot-daemon-member|rustbot-monitor-member|localization-member|nav2-member|lifecycle.audit" /tmp/p7b-daemon.log | tail -60'
```

**Expected**:
- CLI payload line prints `{"group_id":"robot-stack","requested_by":"lifecycle_cli"}` (NOT service_id)
- daemon audit 有 `lifecycle.audit: desired write group_id=robot-stack op=group_restart seq=N` 或类似
- 4 members per-member audit seq(可能 4 个 service_id 的 restart audit)
- nav2-member: pre Up → post Up(restarted,docker ok) → PASS
- rustbot-daemon-member / rustbot-monitor-member: pre inactive → post inactive(DEGRADED — polkit)
- localization-member: pre Up → post Up(DEGRADED — docker restart-policy)

**Verdict criteria**:
- CLI fix PASS = payload `group_id` 正确发出 + daemon handler 不返 MISSING_FIELD
- 4 members 实际 actuate = per-member PASS / DEGRADED / FAIL
- group_restart 整体 PASS = CLI fix PASS + ≥1 member 真actuate (nav2-member PASS 即可)

### Step 4: Restructure reports (~6-7 min)

#### 4a. REWRITE `reports/P7-FULL-E2E-REPORT.md` (§1-§5, 100-150L)

**结构**(严格按 V7 prompt §1-§5):

- **§1 测试范围**:8 services × 3 op + 1 group_restart robot-stack,用户 approval verbatim "全量 + 机器人安全",safety-first order(low/mid/high risk)
- **§2 per-op 结果矩阵**:8 svc × 3 op 表格(24 cells)+ group_restart row,每 cell PASS/FAIL/DEGRADED/EXP-FAIL/SKIP verdict
  - §2.1 DEGRADED root cause analysis(6 ops):
    - 4 systemd system-scope:rustbot-daemon-member / rustbot-monitor-member start/restart — niic-user polkit 缺 StartUnit 权限 on hardware-tagged units
    - 2 docker container:localization-member stop/restart — docker restart-policy `always` 或 stop_container SIGKILL timing
    - **非本 crate defect** → NiicAdmin 或另开 worker
- **§3 group_restart robot-stack**:
  - W7:SKIPPED(`lifecycle_cli.rs:179` 发 service_id,handler 读 group_id → MISSING_FIELD)
  - W7b re-run with --group flag (P7b fix):CLI payload `{"group_id":"robot-stack"}` sent correctly,handler 接收 group_id,processed 4 members
  - 4 members state transitions table(pre/post + verdict)
  - Verdict:CLI fix PASS(group_id 正确路由);3/4 members DEGRADED at actuation layer(deployment,非 src/ defect)
- **§4 cleanup 验证**:
  - W7 cleanup:daemon pkill ✓ + 4 tmp files removed ✓ + service restore ✓
  - W7b cleanup:daemon pkill ✓ + tmp files removed ✓ + service restore to pre-W7b state ✓
  - 0 SP000065 host file modifications(token unchanged / `/etc/systemd/system/` no fixture / `/tmp` clean)
- **§5 contract 验证**:
  - **0 src/ file changes** — examples/lifecycle_cli.rs 是 examples/,非 src/(用户 approved P7b 修此 1 文件)
  - **HEAD = `d2b3b9d`** — 无新 commit(P7b 修改文件 in-place,不 git add/commit)
  - **SHA256 D-117 sentry 保持**: `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822`
  - **Write-set 严格 5 文件**:examples/lifecycle_cli.rs (MODIFY) + 4 reports/

#### 4b. REWRITE `reports/P7-EVIDENCE.md` (per-(svc, op) 3方对照, 300-400L)

**结构**(per-(svc, op) 二元组建小节,每节 3 段):

```markdown
## <service> / <op>

### 1. Daemon audit log
[verbatim `lifecycle.audit:` line from P7-DAEMON-LOG.txt 或 W7b daemon log]

### 2. Provider response (systemctl / docker / HTTP)
[verbatim systemctl/docker/HTTP response]

### 3. Pre/post state diff
- Pre: [state before op]
- Post: [state after op]
- Verdict: PASS / DEGRADED / EXP-FAIL / FAIL / SKIP

---
```

**覆盖**:8 svc × 3 op = 24 subsections + 1 group_restart (W7b re-run) = 25 subsections total

**Evidence 来源**:
- W7 P7-DAEMON-LOG.txt(672L,有 audit lines — grep `lifecycle.audit`)
- W7 P7-EVIDENCE.md(210L,有 per-op commands — 拆解重组)
- W7b 新 daemon log(/tmp/p7b-daemon.log,group_restart re-run)
- 6 DEGRADED ops:audit + pre/post 有,provider response 仍 accept 但 host 未 actuate — verdict DEGRADED
- 4 EXP-FAIL ops:audit 有(INVALID_INTENT 返回),provider response 是 INVALID_INTENT,pre=post — verdict EXP-FAIL
- 3 skipped ops:无 audit(未发 op),只有 pre-state,verdict SKIP

**关键**:每个 (svc, op) 必须有 §1 audit + §2 provider + §3 pre/post 三段(若 W7 没捕全,从 daemon log 提取 + 加 inference note "extracted from P7-DAEMON-LOG.txt line N")。V7 FAIL 4 的 root cause = audit 仅 6 hits / pre-state 仅 1 hit — P7b 必须 25 subsections × 3 segments 全填。

#### 4c. APPEND `reports/P7-DAEMON-LOG.txt` (W7b session)

在文件末尾 append:

```
=== P7b session at <ISO timestamp> ===
=== group_restart robot-stack re-run with --group flag (P7b fix) ===
[verbatim /tmp/p7b-daemon.log content from ssh pull]
=== end P7b session ===
```

#### 4d. NEW `reports/P7b-FIX-REPORT.md` (delta, 30-50L)

```markdown
# P7b Fix Report — V7 RE-DISPATCH resolution

## V7 3 hard FAILs addressed

| Claim | V7 FAIL | P7b fix | Status |
|---|---|---|---|
| 3 | Report §1-§5 结构 | Rewrote P7-FULL-E2E-REPORT.md to §1-§5 (§4=cleanup, §5=contract 验证) | DONE |
| 4 | per-op 3方对照 evidence thin | Rewrote P7-EVIDENCE.md to per-(svc,op) 25 subsections × 3 segments | DONE |
| 5 | group_restart SKIPPED | Modified examples/lifecycle_cli.rs (7 spots) + re-ran group_restart with --group flag | DONE |

## lifecycle_cli.rs modification summary (7 spots)

- Line 13: comment Ops 列表加 group_start/group_stop/group_restart
- Line 17-26: flags doc 加 --group
- Line 44-52: struct Args 加 group: Option<String>
- Line 54-97: parse_args 加 --group flag + group field
- Line 78-83: help text 加 [--group <gid>]
- Line 145-148: needs_service + needs_group logic (group_* exempt from --service, require --group)
- Line 178-181: payload — group_id for group_*, service_id otherwise

## group_restart re-run result

- CLI payload: `{"group_id":"robot-stack","requested_by":"lifecycle_cli"}` (correctly sent)
- Daemon handler: handle_lifecycle_group_restart received group_id, processed 4 members
- 4 members verdict:
  - nav2-member: PASS (docker container restart ok)
  - rustbot-daemon-member: DEGRADED (polkit — deployment)
  - rustbot-monitor-member: DEGRADED (polkit — deployment)
  - localization-member: DEGRADED (docker restart-policy — deployment)
- CLI fix PASS; group_restart 整体 PASS (≥1 member 真actuate); 3/4 DEGRADED at actuation layer (非 src/ defect)

## Out-of-scope (V7 item 5 — 6 DEGRADED ops)

- 4 systemd system-scope (rustbot-daemon-member / rustbot-monitor-member start/restart): niic-user polkit 缺 StartUnit 权限 on hardware-tagged units → NiicAdmin or separate worker
- 2 docker container (localization-member stop/restart): docker restart-policy `always` 或 stop_container SIGKILL timing → NiicAdmin or separate worker
- P7b documents but does NOT fix (deployment-layer, not src/ defect)

## Time elapsed

~12-15 min wall clock.
```

### Step 5: Cleanup (~30s)

```bash
# daemon pkill
ssh niic@192.168.100.100 'pkill -f demo-app-lifecycle-p7b; sleep 1; ps -ef | grep demo-app-lifecycle-p7b | grep -v grep'  # 应空

# tmp cleanup (保留 daemon log scp 到本地 reports/ 后再删)
scp niic@192.168.100.100:/tmp/p7b-daemon.log /tmp/p7b-daemon.log
ssh niic@192.168.100.100 'rm -f /tmp/demo-app-lifecycle-p7b /tmp/lifecycle_cli-p7b /tmp/registry-sp000065-control.yaml /tmp/p7b-daemon.log /tmp/p7b-grep.out'

# verify cleanup
ssh niic@192.168.100.100 'ps -ef | grep demo-app-lifecycle-p7 | grep -v grep; ls -la /tmp/*p7* 2>/dev/null'
# both should be empty

# service restore: 4 members 已被 group_restart attempt 过,确保状态合理
# nav2-member 应 Up (docker restart ok)
# rustbot-daemon-member / rustbot-monitor-member: pre-W7b state = inactive (W7 cleanup 后 baseline)
# localization-member: pre-W7b state = Up (docker restart-policy 保住)
# 如有偏离 baseline,record in ESCALATE
```

### Step 6: Final message

- V7 3 FAILs addressed summary(每 claim 一行 + DONE status)
- lifecycle_cli.rs modification summary(7 spots,line ranges changed)
- group_restart re-run result(4 members verdict table + CLI fix PASS)
- 6 DEGRADED out-of-scope ESCALATE(NiicAdmin or separate worker)
- **0 src/ file changes** ✓(examples/lifecycle_cli.rs 是 examples/ 不是 src/)
- **HEAD = `d2b3b9d`** ✓(无新 commit)
- **SHA256 D-117 sentry 保持** ✓(`74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822`)
- **Write-set 5 files** + line counts:
  - examples/lifecycle_cli.rs (MODIFY, ~7 spots)
  - reports/P7-FULL-E2E-REPORT.md (REWRITE, ~100-150L)
  - reports/P7-EVIDENCE.md (REWRITE, ~300-400L)
  - reports/P7-DAEMON-LOG.txt (APPEND, +N lines)
  - reports/P7b-FIX-REPORT.md (NEW, ~30-50L)
- Cleanup verification(daemon pkill + tmp 清理 + service state)
- Time elapsed

## Hard constraints

- **Modify `examples/lifecycle_cli.rs` ONLY** — 不动其它 src/ 或 examples/ 文件。
- **0 SP000065 host file modifications** — 不写 `/etc/systemd/system/`、不改 token、不改 roboctl config。只通过 roboctl HTTP API + systemd D-Bus + docker daemon启停服务。
- **NEVER** `git push`。**NEVER** AI attribution。**NEVER** `git add` 或 `git commit`(P7b 修改文件 in-place,不 commit — HEAD 保持 `d2b3b9d`)。
- **HEAD-guard** before any git touchpoint。HEAD 必须保持 `d2b3b9d`。
- **SHA256 D-117 sentry** 必须保持 `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822`。
- **Hard 15-min cap** — timeout 900s。到点必停 partial 交付。
- **Cleanup 必须** — daemon pkill + tmp 清理 + service state 恢复 baseline(W7 cleanup 后态)。

## Normative reads (3 files, 30s — cache from W7)

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md`
2. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/examples/lifecycle_cli.rs` (file to modify — 7 spots in scope)
3. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/src/handlers.rs` (line 683-693 — handle_lifecycle_group_restart reads group_id)

工作语言:中文为主,关键术语/文件路径/决策 ID 保留英文。

现在开始:modify lifecycle_cli.rs 7 spots (60s), build + scp + start daemon (90s), re-run group_restart + capture 4 members state (90s), restructure 4 reports + write P7b-FIX-REPORT (6-7 min), cleanup (30s), final message (30s)。15 min hard cap。
