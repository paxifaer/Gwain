# PROMPT-W7 — P7 Worker (kimi-k3), 10-min full E2E real-robot control verbs test on SP000065

```
Before doing anything else:
1. Read /home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's classifier and follow every rule
   that applies.
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly 4 files (all under demo-app-lifecycle/):
   - examples/registry-sp000065-control.yaml (NEW)
   - reports/P7-FULL-E2E-REPORT.md (NEW)
   - reports/P7-DAEMON-LOG.txt (NEW)
   - reports/P7-EVIDENCE.md (NEW)
   Report every file created with line numbers in your final message.

HEAD-guard: before any git touchpoint, run `git log --oneline -1 && git status --short`.

model_selection:
  model: t9s/kimi-k3
  mode: automatic
  reason: deployment_debugging  # P7 real-robot full E2E control verbs — kimi-k3 balanced
```

---

You are **W7 of Lifecycle Robot Takeover P7** — **full E2E real-robot start/stop/restart test** on SP000065。P0-P6 全 ACCEPT(takeover CLOSED per D-119);P7 是 takeover closing 后的 **bonus real-robot control verb validation**,用户 explicit approve "全量 + 机器人安全"。

**用户 explicit approval**(AskUserQuestion 答案 verbatim):"全量 + 机器人安全" — 跑全部 12+ 服务的 start/stop/restart + robot-stack 整组 restart。机器人处于安全状态(维护窗口 / 周边无人),接受硬件 daemon 启起来 + 机器人可能动。

## CRITICAL: 10-MIN HARD CAP + NO PARTIAL RETURNS

- **Hard time cap: 10 min wall clock**。到点必停,partial 状态作为 final message 交付。
- **禁止**返回 plan / outline / status update / "next I'll ..."。Work continuously 直到 4 个 deliverable 文件写完 + final message 交付。

## Pre-known facts (inline, do not re-verify — from W5b P5 dogfood)

- SP000065 = 192.168.100.100, SSH `niic@192.168.100.100` (key-based auth via `~/.ssh/config` alias `niic_26`)
- roboctl daemon binds `192.168.100.100:8765` (NOT 0.0.0.0 — loopback curl refused), Bearer token at `/home/niic/.config/roboctl/token` (44 bytes incl newline, 43-char token)
- roboctl API:
  - `GET /api/units` (status, returns 200 + JSON, Bearer-required)
  - `POST /api/unit/<name>/<op>` where op ∈ `start | stop | restart | reset-failed` (Bearer-required)
  - `POST /api/group/<name>/<op>` where op ∈ `start | stop | restart` (Bearer-required)
  - `<name>` 用 bare name 无 `.service` 后缀,e.g. `rustbot-daemon` not `rustbot-daemon.service`
- daemon binary musl target(wangdang glibc 2.39 vs SP000065 Ubuntu 22.04 glibc 2.35):`cargo build -p demo-app-lifecycle --release --target x86_64-unknown-linux-musl` ~57s
- daemon env vars: `FLEET_ID=p7`, `BOT_NAME=sp000065`, `REGISTRY_YAML=/tmp/registry-sp000065-control.yaml`, `RUST_LOG=info`
- lifecycle_cli env: same `FLEET_ID`/`BOT_NAME`/`REGISTRY_YAML`,plus `ZENOH_CONFIG` per MVP test pattern(查 `demo_app_service/tests/` 找 e2e test 的 ZENOH_CONFIG 路径)
- P5 dogfood artifact:`examples/registry-sp000065.yaml` 是 status-only(W5b 留下),W7 **不动**它,另写新 `registry-sp000065-control.yaml`
- daemon 端口:查 `src/main.rs` 找 daemon HTTP server port (MVP 用 17447;P7 可能不同)

## Task

在 SP000065 真跑 lifecycle 通过 HTTP provider(systemd / docker / roboctl HTTP)启停所有 service。

### Step 1: 写 `examples/registry-sp000065-control.yaml` (~60s)

基于 `examples/registry-sp000065.yaml`(P5 dogfood artifact),expand `expose` 到 `[lifecycle, status]` 全部 service + group,add control verb selectors:

- **systemd services**(`argo-zenoh-global` / `ethercat-oneshot` / `rustbot-daemon-member` / `rustbot-monitor-member`):lifecycle 通过 D-Bus 直接 `systemctl start/stop/restart`。selector 不变(`unit: <name>.service`),只 expand expose 到 `[lifecycle, status]`。
- **docker services**(`localization-robot-1-docker-exec` / `localization-member` / `nav2-member`):lifecycle 通过 docker daemon 直接 container start/stop/restart。查 `src/providers/docker.rs` 看 docker provider 支持哪些 selector key for start/stop/restart (e.g., `start.cmd` 或 直接用 `container:` key + lifecycle runtime 调 docker API)。`localization-robot-1-docker-exec` 保留 `exec_process: p5-probe` + `exec_start: ...` 作为 PA3 path(已 P5 PASS)。
- **HTTP service**(新增 `rustbot-daemon-http-control`):用 roboctl HTTP provider + start/stop/restart URL。selector:
  ```yaml
  status.url: "http://192.168.100.100:8765/api/units"
  status.method: GET
  status.success_codes: "200"
  start.url: "http://192.168.100.100:8765/api/unit/rustbot-daemon/start"
  start.method: POST
  start.success_codes: "200,202"
  stop.url: "http://192.168.100.100:8765/api/unit/rustbot-daemon/stop"
  stop.method: POST
  stop.success_codes: "200,202"
  restart.url: "http://192.168.100.100:8765/api/unit/rustbot-daemon/restart"
  restart.method: POST
  restart.success_codes: "200,202"
  ```
- **robot-stack group**:expand `expose: [lifecycle, status]`。查 `src/providers/http.rs` + `src/runtime/handlers.rs` 看 group_restart op 怎么路由 HTTP provider(group-level HTTP selector 形态)。如果 lifecycle 当前不支持 group HTTP POST,ESCALATE + skip group_restart HTTP 路径,改用 systemd-direct path(逐个 member `systemctl restart` 4 个 unit 作为 fallback 测试)。

### Step 2: build + scp + 启 daemon (~90s)

```bash
cd /home/wangdang/work/ai-stack/code/ArgoWatch
cargo build -p demo-app-lifecycle --release --target x86_64-unknown-linux-musl 2>&1 | tail -3
scp target/x86_64-unknown-linux-musl/release/demo-app-lifecycle niic@192.168.100.100:/tmp/demo-app-lifecycle-p7
scp examples/registry-sp000065-control.yaml niic@192.168.100.100:/tmp/registry-sp000065-control.yaml
ssh niic@192.168.100.100 'FLEET_ID=p7 BOT_NAME=sp000065 REGISTRY_YAML=/tmp/registry-sp000065-control.yaml RUST_LOG=info nohup /tmp/demo-app-lifecycle-p7 > /tmp/p7-daemon.log 2>&1 &'
sleep 3
ssh niic@192.168.100.100 'ps -ef | grep demo-app-lifecycle-p7 | grep -v grep'  # verify daemon alive
```

### Step 3: 跑测试矩阵 (~6 min)

For each service in `registry-sp000065-control.yaml`(8+ services):
1. **Pre-state snapshot**:`ssh niic@192.168.100.100 'systemctl show <unit> -p ActiveState,SubState,Type'` 或 `docker ps --filter name=<container> --format "{{.Names}} {{.Status}}"`
2. **start**: `lifecycle_cli start <svc>` → record daemon audit log + roboctl/systemd response + post-state
3. **stop**: `lifecycle_cli stop <svc>` → record
4. **restart**: `lifecycle_cli restart <svc>` → record

For group `robot-stack`:
- **Pre-state**: 4 members' systemctl/docker state
- **group_restart**: `lifecycle_cli group_restart robot-stack` → record
- **Post-state**: 4 members' state(应该都 restart 过)

Per-op evidence:
- daemon audit log line(`lifecycle.audit: desired write service_id=... op=... seq=...`)
- roboctl response(for HTTP-provider svcs)或 systemd transition(for systemd/docker svcs)
- pre-state vs post-state diff(3方对照)

**测试顺序**(safety-first):
1. low-risk 先:`argo-zenoh-global`(通讯层 stop 不断硬件)/ `ethercat-oneshot`(oneshot restart)/ `localization-robot-1-docker-exec`(docker exec probe)
2. mid-risk:`localization-member`(docker container restart)/ `nav2-member`(docker container restart,虽然 nav2-dev 不存在 — expect FAIL but record)
3. high-risk 最后:`rustbot-daemon-member`(systemd 启硬件 daemon)/ `rustbot-monitor-member`(systemd 监控)/ `rustbot-daemon-http-control`(HTTP POST to roboctl 启硬件 daemon)/ `robot-stack group_restart`(整组原子 restart,4 members)

**Safety abort**:任何 op 后 daemon 没响应 30s + `systemctl show` 卡住 + SSH timeout → ABORT 测试,跳到 Step 4 cleanup,记录 ESCALATE。

### Step 4: cleanup (~30s)

- **Restore all services to pre-test state**:用 Step 3 pre-state snapshot,对每个被改的 service 做 `systemctl start/stop` 恢复到 pre-state(docker container 同理)
- **daemon pkill**:`ssh niic@192.168.100.100 'pkill -f demo-app-lifecycle-p7; sleep 1; ps -ef | grep demo-app-lifecycle-p7 | grep -v grep'` → 应空
- **tmp 清理**:`ssh niic@192.168.100.100 'rm -f /tmp/demo-app-lifecycle-p7 /tmp/registry-sp000065-control.yaml'`(保留 `/tmp/p7-daemon.log` 等下载到本地 reports/)
- **scp daemon log 到 reports**:`scp niic@192.168.100.100:/tmp/p7-daemon.log /tmp/p7-daemon.log`(然后 read + 写到 `reports/P7-DAEMON-LOG.txt`)
- **清理 SP000065 上 /tmp/p7-daemon.log**:`ssh niic@192.168.100.100 'rm -f /tmp/p7-daemon.log'`

### Step 5: 写 4 deliverables + final message (~90s)

1. `examples/registry-sp000065-control.yaml`(NEW, ~150-200 lines)
2. `reports/P7-FULL-E2E-REPORT.md`(NEW, 5-10 KB):
   - §1 测试范围(服务清单 + op 矩阵 + 用户 approval 引用 + safety-first order)
   - §2 每 op 执行结果(服务 × op 表格 PASS/FAIL/TIMEOUT/SKIP + 3方对照 evidence)
   - §3 group_restart robot-stack 结果(4 members 状态转换链 + 整组原子性验证)
   - §4 cleanup 验证(daemon pkill + service restore + tmp 清理 + 0 SP000065 host file mods)
   - §5 0 src/ + HEAD = d2b3b9d + sha256 D-117 sentry 保持 验证
3. `reports/P7-DAEMON-LOG.txt`(NEW, raw daemon log copy)
4. `reports/P7-EVIDENCE.md`(NEW, per-op commands + output snippets + 3方对照)

## Hard constraints

- **0 src/ file changes** — P7 是 dogfood,不改 src/。新文件只在 `examples/` 和 `reports/` 下。
- **0 SP000065 host file modifications** — 不写 `/etc/systemd/system/`、不改 token、不改 roboctl config。只通过 roboctl HTTP API + systemd D-Bus + docker daemon 启停服务(用户已 explicit approve "全量 + 机器人安全")。
- **Cleanup 必须** — 测试完后所有 service 恢复 pre-test state + daemon pkill + tmp 清理。
- **HEAD-guard** before any git touchpoint。
- **NEVER** `git push`。**NEVER** AI attribution。
- **Hard 10-min cap** — timeout 660s(10 min + 1 min slack)。到点必停 partial 交付。

## Normative reads (5 files, 30s)

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md`
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/lifecycle-robot-takeover/task.md`
3. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/reports/P5-DOGFOOD-REPORT.md`(W5b pattern)
4. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/examples/registry-sp000065.yaml`(P5 dogfood artifact base)
5. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/src/providers/http.rs`(D-111 schema reference)

## Final message

- §1-§5 摘要(每 § 一行)
- Per-service 测试矩阵表(服务 × start/stop/restart PASS/FAIL)
- robot-stack group_restart 结果
- **0 src/ file changes** ✓
- **HEAD = `d2b3b9d`** ✓
- **SHA256 D-117 sentry 保持** ✓(`74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822`)
- **Cleanup 验证** ✓(daemon pkill + service restore + tmp 清理)
- **0 SP000065 host file modifications** ✓
- Files created 4 个 + 行数 + 一行描述
- ESCALATEs
- Time elapsed

工作语言:中文为主,关键术语/文件路径/决策 ID 保留英文。

现在开始:read 5 normative reads(30s),写 control registry(60s),build+scp+起 daemon(90s),跑测试矩阵(~6 min),cleanup(30s),写 4 deliverables + final message(90s)。10 min hard cap。
