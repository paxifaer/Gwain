# PROMPT-W5b — P5 Develop worker (sonnet-equivalent), 10-min **compressed** dogfood on SP000065

```
Before doing anything else:
1. Read /home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's classifier and follow every rule
   that applies.
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly the files declared in this prompt. Report every
   file created or modified, with line numbers, in your final message.
If the task directory has a state.md with a ## Blocked section, the listed
file::symbol entries are read-only for you; needing to touch one is an
ESCALATE trigger.

HEAD-guard: before any git touchpoint, run `git log --oneline -1 && git status --short`.

model_selection:
  model: t9s/kimi-k3
  mode: automatic
  reason: deployment_debugging_and_task_decomposition  # P5 compressed dogfood; kimi-k3 balanced per workflow.md §Model Selection
```

---

You are **W5b of Lifecycle Robot Takeover P5** — 10-min **compressed** real-robot dogfood on SP000065 (192.168.100.100, user niic). P0-P4 closed ACCEPT (V4 clean) at `handoffs/lifecycle-robot-takeover/V4-VERDICT.md`. Test gate baseline: 99/99 serial. reconcile.rs sha256 sentry = `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822` (D-117).

**用户已 explicit 把 SP000065 服务清单 + API 地图直接给我(下方 §Pre-known facts),无需自己探查。** W5b 跳过 service inventory + roboctl API discovery 阶段,直接进 §Deliverable 2(写 yaml)+ §Deliverable 6(跑核心 5 个 case 子集)。**P5 is dogfood — configuration + deployment + verification, NOT code change. If a code fix is needed, ESCALATE.**

## CRITICAL: NO PARTIAL RETURNS + 10-MIN HARD CAP

**Hard time cap: 10 min wall clock from worker start.** 到 10 min 必须停手 + 把 partial 状态作为 final message 交付(每 case PASS/FAIL/ESCALATE/SKIP 带 evidence)。**不要**为了把所有 case 跑绿而突破时间帽 — 用户 explicit 说"我们只是测试"。

Your turn ends ONLY when (a) 10 min 到 OR (b) 5 个核心 case 都有 verdict。**禁止**返回 plan / outline / status update / "next I'll ..." 这种局部进度。Work continuously until deliverables + test evidence + sha256/sentinel confirmations 都在 final message 里。

## Pre-known facts (用户 inline 提供 — 跳过探查)

### SP000065 SSH
- `ssh -o BatchMode=yes -o ConnectTimeout=5 niic@192.168.100.100 '<cmd>'` (key auth,直接可达)
- hostname = SP000065, Linux 6.12.55 #23 SMP PREEMPT_DYNAMIC DOVETAIL x86_64

### 三套 HTTP 端口(用户清单,但 :8090/:19090 实测 **未监听**,见下)
- `192.168.100.100:8765` (roboctl, **绑 192.168.100.100 不是 0.0.0.0**,从 lo 127.0.0.1 curl 会 refused;从 192.168.100.100 curl 可达) — robot-stack unit/group 启停 — Bearer `~/.config/roboctl/token` (43 chars)
- `127.0.0.1:7447` (python3 pid 2283, **不是 zenohd**,可能是 zenoh_pub)
- `0.0.0.0:50053` (argo-gateway mTLS)
- `:8090` / `:19090` — **实测未监听** (用户清单过时;ss -tlnp 里没有) — W5b 不要假设这俩存在

### roboctl API (实测)
- `GET /api/units` → JSON,含 `groups` (e.g. "robot-stack" → 4 成员) + `ungrouped` + `robot` (hw.lock) + `registry_path`。**这是唯一已确认的 GET 端点**。
- `POST /api/unit/<name>/<op>` (op ∈ `("start","stop","restart","reset-failed")` — UNIT_ACTIONS)
- `POST /api/group/<name>/<op>` (op ∈ `("start","stop","restart")` — GROUP_ACTIONS)
- **没有** `/api/unit/<name>` GET 单 unit 状态路由 — 返回 404 "not found"
- **没有** status 作为 POST op;status 只能 GET /api/units 后客户端侧过滤
- roboctl.pyz 源码在 `/home/niic/Downloads/robot-stack/bin/roboctl.pyz`(zip 可 `python3 -c "import zipfile; ..."` 读 `roboctl/server.py` / `roboctl/systemd.py`)

### roboctl /api/units 当前状态(实测)
- robot-stack group 4 成员**全部 inactive/dead**:
  - `rustbot-daemon.service` (order 10, static, hardware daemon — argodds :57447, 持 hw.lock)
  - `rustbot-monitor.service` (order 15, enabled, hardware health panel)
  - `localization.service` (order 25, enabled, docker compose)
  - `nav2.service` (order 26, enabled, docker compose)
- 用户清单:robot-stack **必须整组** restart(`/api/group/robot-stack/restart`),不要单独 restart daemon — 但实测全 dead,整组 restart = 整组 start(会启动硬件 daemon,有 hw.lock + SHM 重连,风险高)

### SP000065 systemd 实测状态
- **active**: `argo-zenoh-global`, `argo-zenoh-local`, `argogateway-server`, `demo-app-backend`, `robot-toolkit-agent`
- **inactive**: `argo-gateway-server` (与 `argogateway-server` 是不同 unit!注意大小写), `ethercat` (oneshot), `media_mapping` (oneshot)
- **activating**: `argogateway-client`, `nplc` (oneshot)
- **user unit**: `argowatch-collector` (user niic) inactive

### docker 实测
- `localization-robot-1` (Up 4 hours, uid 1000, WorkDir /workspace, entrypoint /ros_entrypoint.sh)
- `docker exec localization-robot-1 sh -c 'echo X && id'` 可跑 ✓ (PA3 候选)

### 关键路径(用户清单)
- `~/.config/roboctl/{registry.ini, server.ini, token}` (token 43 chars, Bearer)
- `/opt/robot/RoboConfig/rb_config.yaml` (daemon 配置)
- `/var/log/robot/{pilot,roboskillserver}/` (业务日志)

## Normative reads, in order(已精简 — 只读 4 个文件,30 秒内)

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md` — Gawain classifier + hard constraints.
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/lifecycle-robot-takeover/task.md` — Acceptance PA1-PA5 / PB1-PB3 / PC1-PC3 / PD1-PD3(只看 W5b 要跑的 5 个 case)。
3. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/lifecycle-robot-takeover/decisions.md` — D-101..D-117 binding(关键:D-111 HTTP provider schema, D-112 env_file ${VAR} interp, D-117 sha256 sentry)。
4. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/examples/registry-robot.yaml` — existing topology manifest template;W5b derives `registry-sp000065.yaml` from this。
5. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/examples/lifecycle_cli.rs` — CLI client driving zenoh control plane(只看 op 枚举 + 用法,30 秒)。
6. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/src/providers/http.rs` — HTTP provider 实现(决定 PD2 怎么 bind)。
7. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/src/providers/docker.rs` — docker provider 实现(决定 PA3 怎么 bind exec_start)。
8. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/src/providers/systemd.rs` — systemd provider 实现(决定 PA1/PC1 怎么 bind)。

**不要**读 V4-VERDICT.md / W4 prompt / main.rs / config.rs — 已 inline 关键信息,不读。

## Environment

### Build machine: wangdang (this host)

- cwd: `/home/wangdang/work/ai-stack/code/ArgoWatch` (git branch `feat/lifecycle-robot-takeover` already checked out, HEAD = `d2b3b9d`)。
- `cargo build -p demo-app-lifecycle --release`(只 build,不跑 cargo test — 99/99 已在 P0-P4 验证,10 min cap 跑不起)。若 build fail → ESCALATE 立即收手。
- sudo password `wangdang` IF needed for cargo build deps(unlikely — code already built successfully through P4)。
- HEAD-guard before any git touchpoint: `git log --oneline -1 && git status --short`。HEAD 必须保持 `d2b3b9d`。

### Run machine: SP000065 (192.168.100.100, user niic)

- SSH: `ssh -o BatchMode=yes -o ConnectTimeout=5 niic@192.168.100.100 '<cmd>'`
- 二进制 + 配置丢 `/tmp/lifecycle-p5/`(SP000065 重启自动清理)。

### Robot host boundary (HARD — feedback_robot_host_safety)

- **NEVER modify any SP000065 host file**: no `/etc/systemd/system/...`, no `~/.config/roboctl/...` content edits, no `apt install`, no rust toolchain install on SP000065。
- **NEVER restart SP000065's existing systemd services via `sudo systemctl restart`**(argo-zenoh, argogateway-server, demo-app-backend, robot-toolkit-agent, etc.)。
- **NEVER POST `/api/group/robot-stack/restart` 或 `/api/unit/<robot-stack-member>/start`**(会启动硬件 daemon / 抢 hw.lock / 触发 SHM 重连 — 不可逆风险)。**PB1 dogfood 因此 ESCALATE,不真跑**(见下)。
- **NEVER touch `localization-robot-1` container's runtime state in a non-reversible way**。`docker exec <cmd>` 是只读探查,OK;`docker stop/start/restart` 不要做 — PA3 用 `docker exec` 跑 echo/id 即可,不要重启容器。
- All lifecycle ops you issue must be reversible: `start`/`stop`/`restart` via lifecycle daemon **only on synthetic / bind-status-only** 成员。
- 若需要任何 fixture install on SP000065 → **ESCALATE rather than install**。
- Sandbox: 部署 lifecycle binary 到 `/tmp/lifecycle-p5/` on SP000065。DO NOT install to `/usr/local/bin/` 或任何 persistent location。

## SHA256 sentry (D-117)

`src/runtime/reconcile.rs` 必须 = `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822`。W5b 之前 / 之后 sha256 都跑一次。**0 src/ file changes**。如果发现需要改代码,ESCALATE BEFORE editing。

## Deliverables(精简到 4 个 + final message)

### 1. Build + sha256 sentry on wangdang (≤2 min)

- `cd /home/wangdang/work/ai-stack/code/ArgoWatch && git log --oneline -1 && git status --short` → HEAD 必须 `d2b3b9d`,clean
- `sha256sum demo_app_service/crates/demo-app-lifecycle/src/runtime/reconcile.rs` → 必须 `74b92f34...72b822`
- `cargo build -p demo-app-lifecycle --release` → 必须 PASS(无编译错误)。**不跑 cargo test** — 99/99 已 P0-P4 验证,10 min cap 跑不起。
- 记录 build elapsed。

### 2. Write `examples/registry-sp000065.yaml`(≤1.5 min)

基于 `examples/registry-robot.yaml` 模板 + §Pre-known facts,写一个**最小可跑**的 SP000065 registry。最少 5 个 entry,对应 5 个核心 case:

- `argo-zenoh-global`: systemd provider, system scope, **status-only bind**(用于 PA1 dogfood — lifecycle_cli 发 `status` op,不发 start/stop/restart)
- `localization-robot-1-docker-exec`: docker provider, exec_start shape, **read-only exec**(用于 PA3 dogfood — exec `echo PA3_OK && id` 之类)
- `rustbot-daemon-http`: HTTP provider, base_url `http://192.168.100.100:8765`, bearer_token_file `/home/niic/.config/roboctl/token`, **status-only**(GET /api/units,客户端解析过滤;用于 PD2 dogfood — 不 POST 启停 op)
- `ethercat-oneshot`: systemd provider, oneshot shape, **status-only bind**(用于 PC1 dogfood — Phase::Completed 验证;ethercat 实测 inactive,如果 lifecycle 判定 = Phase::Pending 或 Phase::Failed 也算 evidence)
- `robot-stack-group`: group_restart shape,**dogfood 不真跑**(用于 PB1 dogfood — 只验证 lifecycle_cli 能发出 group_restart 命令、daemon 能解析 group 拓扑、audit 行 fan-out 出来;实际 restart 因为 robot host boundary **ESCALATE**,见下)

每个 entry 必须遵守 D-101..D-117 的 schema(exec_start/exec_script 互斥 D-107、pid_file/tmux_session/cmdline_regex 互斥 D-110、HTTP provider schema D-111、env_file ${VAR} 插值 D-112)。

### 3. Deploy + 起 daemon on SP000065(≤2 min)

- `scp` 二进制 + registry 到 `niic@192.168.100.100:/tmp/lifecycle-p5/`
- 在 SP000065 起 daemon:`ssh niic@192.168.100.100 'cd /tmp/lifecycle-p5 && FLEET_ID=sp000065 BOT_NAME=sp000065 REGISTRY_PATH=/tmp/lifecycle-p5/registry-sp000065.yaml ZENOH_ENDPOINT=tcp/127.0.0.1:7447 ./demo-app-lifecycle > /tmp/lifecycle-p5/daemon.log 2>&1 &'`(env vars 按 `src/config.rs` 实际名调整 — 如果 env var 名跟这里写的不一致,以 config.rs 为准,记录差异)
- 验证 daemon 启动:`sleep 3 && ssh niic@192.168.100.100 'tail -30 /tmp/lifecycle-p5/daemon.log; ps -ef | grep demo-app-lifecycle | grep -v grep'`
- 如果 daemon 启动 fail 或 zenoh 连不上(127.0.0.1:7447 是 python3 不是 zenohd,可能要换端点)→ ESCALATE with daemon.log。

### 4. 执行核心 5 个 dogfood case(≤3 min)

每个 case 跑 `lifecycle_cli` op + 验证 SP000065 状态 + 抓 audit 行。Record per-case PASS/FAIL/ESCALATE/SKIP with evidence(commands + output snippets + audit log lines)。

#### PA1 — system scope unit bind + status-only
- `lifecycle_cli status argo-zenoh-global`(或实际 CLI op 名)
- 验证:返回 active=active ✓
- **不**发 start/stop/restart(robot host boundary)

#### PA3 — docker exec_process with `exec_start`
- `lifecycle_cli exec-start localization-robot-1-docker-exec`(或实际 CLI op)
- 验证:audit 行含 `docker exec localization-robot-1 <cmd>`;SP000065 上 `docker exec localization-robot-1 sh -c 'echo PA3_OK'` 输出 `PA3_OK`
- **不**重启容器

#### PC1 — oneshot Type → Phase::Completed
- `lifecycle_cli status ethercat-oneshot`(ethercat 实测 inactive)
- 验证:lifecycle 返回的 Phase 状态(Completed/Pending/Failed);记录实际值
- 如果 ethercat inactive 导致 lifecycle 不能 bind → ESCALATE "PC1 真实 dogfood 需要 active=exited oneshot unit,SP000065 上 ethercat/media_mapping 都 inactive,nplc activating 异常;留作后续"

#### PD2 — ProviderKind::Http + Bearer + GET status
- `lifecycle_cli status rustbot-daemon-http`
- 验证:lifecycle 通过 HTTP provider GET `http://192.168.100.100:8765/api/units` + Bearer token + 解析出 `rustbot-daemon` 的 `active_state=inactive`(实测)
- **不**POST 启停 op(roboctl UNIT_ACTIONS 启停会触发 systemd 动作)

#### PB1 — group_restart fan-out
- **ESCALATE-by-default** — robot-stack 4 成员全 dead,真 restart = 整组 start = 启动硬件 daemon + 抢 hw.lock + SHM 重连 = 不可逆风险。
- 唯一允许的 PB1 dogfood:lifecycle_cli 发 `group-status robot-stack-group`(如果 CLI 支持),验证 lifecycle 能解析 group 拓扑、能 fan-out 列出 4 个成员、audit 行正确。
- **不**发 group_restart / group_start / group_stop。
- ESCALATE 文本:"PB1 真实 group_restart dogfood 不可跑 — robot-stack 4 成员全 inactive,POST /api/group/robot-stack/restart 会整组启动硬件 daemon + 抢 hw.lock + SHM 重连,违反 robot host boundary。验证仅限 group-status fan-out 拓扑 + audit 行;真 restart dogfood 留作后续维护窗口或 P6 决策。"

### 5. Final dogfood report — 写到 `reports/P5-DOGFOOD-REPORT.md`(≤1.5 min)

简短(2-4 KB),包含:
1. **Build + sha256 sentinel**:HEAD = `d2b3b9d`,sha256 reconcile.rs = `74b92f34...72b822`(before = after ✓),cargo build elapsed。
2. **Deploy + daemon startup**:SP000065 上 daemon PID、startup trace 前 10 行、zenoh 连接状态。
3. **5 个核心 case** per-test verdict 表(PA1/PA3/PC1/PD2/PB1 + PA2/PA4/PA5/PB2/PB3/PC2/PC3/PD1/PD3 标 SKIP + 一行理由):
   - PASS: 实际命令 + 输出 snippet + SP000065 状态验证 + audit 行
   - FAIL: 实际命令 + 错误 + root-cause hypothesis
   - ESCALATE: ESCALATE 文本 + evidence
   - SKIP: 一行理由
4. **ESCALATEs** — 所有 skipped test + blocker + 判断 calls。
5. **Files created/modified with line numbers** — write-set 内每个文件 + 行数。
6. **Time elapsed** — wall clock from worker start。

### 6. Cleanup(≤30 sec)

- 在 SP000065 上 `pkill -f demo-app-lifecycle`(停 daemon)
- `rm -rf /tmp/lifecycle-p5`(可选,SP000065 重启自动清;不强制)
- 在 wangdang 上 HEAD-guard 复查:`git log --oneline -1 && git status --short` → HEAD 仍 `d2b3b9d`,clean。

## Hard constraints

- **0 src/ file changes** — P5b is dogfood. 若需要改代码,ESCALATE。
- **Hard 10-min cap** — 到点必停,partial 状态作为 final message。
- **Write-set 严格 4 个文件**:
  1. `examples/registry-sp000065.yaml` (NEW)
  2. `reports/P5-DOGFOOD-REPORT.md` (NEW)
  3. `reports/P5-DAEMON-LOG.txt` (NEW,SP000065 daemon.log 拷贝)
  4. `reports/P5-EVIDENCE.md` (NEW,per-case 命令 + 输出 snippet 集中)
- 所有路径前缀 `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/`。
- 超出该清单的写都是 contract violation。
- 任何 git touchpoint 之前 HEAD-guard。
- **NEVER** `git push`。
- **NEVER** AI attribution 到 commit。

## Output contract(写在 final message 里)

1. **Build + sentinel**:HEAD = `d2b3b9d` ✓;reconcile.rs sha256 before/after = `74b92f34...72b822` ✓;cargo build elapsed = Ns。
2. **Files created/modified**:4 个文件路径 + 行数 + 一行描述。
3. **5 个核心 case verdict 表**:每 case 一行 `PA1 | PASS | evidence ref`(evidence ref 指向 P5-EVIDENCE.md 里的具体命令 + 输出 snippet)。
4. **9 个 skipped case 一行**:e.g. `PA2 | SKIP | .target unit dogfood 留作后续`。
5. **ESCALATEs**:所有 ESCALATE 完整文本 + evidence。
6. **Time elapsed**:wall clock。
7. **Robot host boundary 检查**:声明没修改任何 SP000065 host 文件、没重启任何现有 systemd 服务、没碰 `localization-robot-1` 不可逆状态、没 POST 启停 robot-stack。
8. **Cleanup 检查**:daemon 已 pkill、HEAD 仍 `d2b3b9d` clean。

## Time cap

**10 min wall clock**。Single-defect >2 min → ESCALATE。

工作语言:中文为主,关键术语/文件路径/命令保留英文。

现在开始:read 4 个 normative reads(≤30 sec),然后按 §Deliverables 1-6 顺序执行。
