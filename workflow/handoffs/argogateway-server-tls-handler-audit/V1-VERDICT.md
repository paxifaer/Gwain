# V1-VERDICT — Adversarial verification of W1-REPORT

**Task**: `argogateway-server-tls-handler-audit` (E1 + Option A)
**Verifier mandate**: falsify W1's claims. Find evidence W1 was wrong.
**Elapsed**: ~45 min (read bootstrap/SPEC/W1/impl REPORT + 25 bash/grep/git calls)

## 1. Overall verdict

**ACCEPT W1** — All four headline verdicts UPHOLD: E1 SAFE, Option A
NOT-IMPLEMENTED, BLOCKER 1 (validate_router) real, BLOCKER 2 (health check)
real. W1's line numbers are slightly off in several places (off-by-2 to
off-by-11) but every cited snippet exists at a nearby line and the
semantic claims are correct. V1 additionally found a NEW BLOCKER 3 that
strengthens (does not overturn) W1's "NOT safe to deploy as-is" verdict:
the deployed `argogateway_0.1.0_amd64.deb` at `code/ArgoDeploy/packages/`
predates the `b98f1e2` commit that added `push_zenoh_router_config` —
strings on the binary show ZERO `PushZenohRouterConfig` symbols.

## 2. Per-claim verdicts

| # | Claim | Verdict | Evidence | Notes |
|---|---|---|---|---|
| 1 | Server source at `/home/wangdang/work/ai-stack/code/ArgoGateway/` (Rust workspace, production server) | UPHOLD | `code/ArgoGateway/Cargo.toml` + `build-deb.sh` + `argogateway_0.1.0_amd64.deb` + README ("Rust workspace，整合了机器人侧 gRPC/Connect 服务"). `install_cluster.sh:5,122` sets `PACKAGES_DIR="$REPO_ROOT/packages"` then `dpkg -i "$PACKAGES_DIR/argogateway_0.1.0_amd64.deb"`. | W1 missed 4 sibling copies (`code/ArgoWatch/libs/ArgoGateway/`, `code/demo_app/libs/ArgoGateway/`, `code/build_test/ArgoGateway/`, `code/ArgoGateway/.git/worktrees/ArgoGateway`) but they are older snapshots — only `code/ArgoGateway/` on `feat/argo-tls` has `argodds_tools_client.rs` + `discovery.rs`. W1 also did not flag `skyline-cloud-gateway-server/` (Go) but that cloud-side gateway has NO `PushZenohRouterConfig` handler (only `SubmitTask`/`Chat` stub in 90-line `robot_control_service.go`). |
| 2 | Handler at `robot_control.rs:462-511` on working dir | UPHOLD | `sed -n '460,512p' robot_control.rs` shows `async fn push_zenoh_router_config(&self, request: Request<PushZenohRouterConfigRequest>) -> Result<Response<PushZenohRouterConfigResponse>, Status>` at line 462; closing `}` at line 511. Exact match. | Line numbers are correct for the working dir (`feat/argo-tls` branch). On `origin/main` of ArgoGateway the same handler is at lines 522-572 (handler is byte-identical, only line numbers differ due to other branch additions). |
| 3 | Handler forwards to `argodds-tools` Unix socket at `/reset/argodds_config` | UPHOLD | `robot_control.rs:489-495`: `crate::argodds_tools_client::post_json(&self.argodds_tools_sock, "/reset/argodds_config", &body)`. `argodds_tools_client.rs:7`: `pub const DEFAULT_SOCK: &str = "/run/argodds-tools/admin.sock";`. | Exact match. |
| 4 | Parser at `robot_control.rs:474` is `serde_json::Value` (dynamic JSON) | UPHOLD | `sed -n '472,478p' robot_control.rs`: `let router: serde_json::Value = serde_json::from_str(&req.config_json5).map_err(\|e\| { ... })?;` at line 474-478. | Exact line match. |
| 5 | No `deny_unknown_fields` anywhere in `code/ArgoGateway/` | UPHOLD | `grep -rn "deny_unknown_fields" /home/wangdang/work/ai-stack/code/ArgoGateway/` → zero hits. | |
| 6 | No `deny_unknown_fields` in any of the 8 argodds_tools files on `origin/main` of ArgoWatch | UPHOLD | `for f in mod server manager models env diff net tests; do git show origin/main:.../$f.rs \| grep deny_unknown_fields; done` → zero hits across all 8 files. `git grep -n "deny_unknown_fields" origin/main -- demo_app_service/` → zero hits. | |
| 7 | `ResetRequest` at `models.rs:7-19` has no `deny_unknown_fields`; `router` field is `serde_json::Value` at line 18 | UPHOLD with NUANCE | `git show origin/main:.../models.rs \| grep -n`: `7: pub struct ResetRequest {`, `20: pub router: serde_json::Value,`, `21: }`. Derive line is `6: #[derive(Debug, Clone, Deserialize, Serialize)]` (no `deny_unknown_fields`). `Metadata` is at lines 24-26 (W1 said 21-25). | Line numbers off by 2-3 (W1 said 7-19 for struct, 18 for router; actual 7-21, 20). Semantic claim correct: no `deny_unknown_fields`, `router` is `serde_json::Value`. |
| 8 | Daemon parser at `server.rs:35-37` is `serde_json::from_value::<ResetRequest>` | UPHOLD with NUANCE | `git show origin/main:.../server.rs \| grep -n from_value`: `43: let req = match serde_json::from_value::<crate::argodds_tools::models::ResetRequest>(body.0,) {`. | Line 43-45, not 35-37 (off by 8). Semantic claim correct. |
| 9 | E1 SAFE verdict (parse-time acceptance of `transport` block) | UPHOLD | Both layers use `serde_json::Value` for the router field (gateway server: `robot_control.rs:474`; daemon: `models.rs:20`). `serde_json::Value` accepts any valid JSON. No `deny_unknown_fields` at either layer (claims 5+6). | |
| 10 | BLOCKER 1: `validate_router` at `manager.rs:625-631` hard-requires `tcp/0.0.0.0:57447` in `listen.endpoints`; rejects TLS config `["tcp/127.0.0.1:57449","tls/0.0.0.0:57448"]` | UPHOLD | `git show origin/main:.../manager.rs \| sed -n '600,680p'` shows `fn validate_router` at line 607. `ROUTER_PORT_STR = "0.0.0.0:57447"` at line 36. Lines 617-631: `endpoints = listen.get("endpoints").as_array()`, `target = format!("tcp/{ROUTER_PORT_STR}")` (= `"tcp/0.0.0.0:57447"`), `has_port = endpoints.iter().any(\|e\| e.as_str() == Some(target.as_str()))` (STRICT EQUALITY), `if !has_port { return Err(format!("router.listen.endpoints must contain \"tcp/{ROUTER_PORT_STR}\"")); }`. Hand-traced: TLS config has no endpoint == `tcp/0.0.0.0:57447`, so `has_port=false`, returns `Err(...)`. | Function at line 607 (not 625); endpoints check at lines 617-631. W1's line claim slightly off but the rejecting code is exactly as W1 quoted. |
| 11 | BLOCKER 2: `restart_and_healthcheck` at `manager.rs:538-563` polls `ss -tln` for `0.0.0.0:57447` only; TLS restart times out and rolls back | UPHOLD | `git show origin/main:.../manager.rs \| sed -n '535,575p'` shows `fn restart_and_healthcheck` at line 539. Lines 540-541: `Command::new("systemctl").args(["restart", "argo-zenoh-global.service"])`. Line 549 comment: `// 健康检查：5s 预算，500ms 轮询，ss -tln 出现 0.0.0.0:57447 LISTEN`. Line 554: `if text.contains(ROUTER_PORT_STR) { return Ok(()); }` where `ROUTER_PORT_STR = "0.0.0.0:57447"`. Lines 561-563: `Err(format!("health check timeout: {ROUTER_PORT_STR} not LISTEN after restart"))`. Rollback path at lines 286-294 calls `atomic_write(&canonicalize(&entry.router))` then `restart_and_healthcheck()` again. Hand-traced: TLS config produces `ss -tln` lines `127.0.0.1:57449` and `0.0.0.0:57448` — neither contains substring `0.0.0.0:57447`. Times out, rolls back. | Function starts at line 539 (W1 said 538). Off-by-1. Exact behavior match. |
| 12 | Option A NOT-IMPLEMENTED — daemon writes only `/etc/argo-zenoh/zenohd-global.json5` (+ meta + history), restarts only `argo-zenoh-global.service`, never writes `/etc/argo-gateway/env`, never restarts `argogateway.target` | UPHOLD | `env.rs:5`: `pub const DEFAULT_GATEWAY_ENV_FILE: &str = "/etc/argo-gateway/env";`. `env.rs:30-34`: `pub fn gateway_env_file()` (READ-only). `env.rs:43-57`: `pub fn read_env_file(path, key) -> Option<String>` — pure read. No `write_env_file` anywhere. `manager.rs:355-356`: `let bot_name = env::read_env_file(&self.env_file, "BOT_NAME")...; let fleet_id = env::read_env_file(&self.env_file, "FLEET_ID")...` (ONLY use of env_file in daemon; in `report()` only). `manager.rs:540-541`: `Command::new("systemctl").args(["restart", "argo-zenoh-global.service"])` — only restarts zenoh, never `argogateway.target`. | |
| 13 | Only ONE writer of env deltas D4–D14: `install_cluster.sh:126-150` | OVERTURN (NUANCE) | `grep -rln "tee.*argo-gateway/env\|>.*argo-gateway/env" code/` found 5 writers: (a) `install_cluster.sh:126-150` (TLS branch, writes ALL 11 deltas D4-D14); (b) `install_cluster.sh:153-169` (plaintext branch); (c) `install.sh:21-35` (plaintext-only, writes only `ZENOH_ENDPOINT`+`ZENOH_GLOBAL_ENDPOINT` — D11+D12, NO TLS deltas); (d) `code/ArgoGateway/package/DEBIAN/postinst:8-43` (creates DEFAULT env file IF absent, includes `GATEWAY_TLS_ENABLE=0` etc. ONLY on `feat/argo-tls` branch — `origin/main` postinst has no TLS vars); (e) same postinst in `code/build_test/ArgoGateway` and `code/demo_app/libs/ArgoGateway` (older copies). | W1's "exactly ONE writer" is INCORRECT — there are at least 5 writers. BUT only `install_cluster.sh:126-150` writes the full TLS deltas D4-D14 in response to operator invocation. None of these are triggered by `PushZenohRouterConfig` RPC. Option A NOT-IMPLEMENTED verdict still HOLDS. |
| 14 | `argodds-tools` source on `origin/main` of `code/ArgoWatch/`, NOT on `feat/lifecycle-robot-takeover` (current branch) | UPHOLD | `cd code/ArgoWatch && git branch --show-current` → `feat/lifecycle-robot-takeover`. `git ls-tree -r feat/lifecycle-robot-takeover --name-only \| grep argodds_tools` → empty. `git ls-tree -r origin/main --name-only \| grep argodds_tools` → 8 files at `demo_app_service/crates/demo-app-backend/src/argodds_tools/{mod,server,manager,models,env,diff,net,tests}.rs`. `git log --oneline origin/main -1` → `9252dda Merge branch 'feat/argodds-tools-mvp' into 'main'` (HEAD of origin/main). | |
| 15 | `9252dda` is merged to `origin/main` (ESCALATE #3) | UPHOLD | `git log --oneline origin/main -1` → `9252dda` is HEAD commit. `git log --format="%H %ai %s" -1 9252dda` → `9252dda 2026-08-12 13:11:44 +0000 Merge branch 'feat/argodds-tools-mvp' into 'main'`. | |
| 16 | Deployed deb must verify `9252dda` is included — but the deployed deb at `code/ArgoDeploy/packages/demo-app-backend_0.1.0-1_amd64.deb` does NOT include argodds-tools (ESCALATE #3) | UPHOLD with NEW BLOCKER | `ls -la code/ArgoDeploy/packages/demo-app-backend_0.1.0-1_amd64.deb` → built 2026-06-30 16:51 (BEFORE `9252dda` 2026-08-12). `ar x` + `tar -xf data.tar.xz` extracted `usr/bin/demo-app-backend`. `strings /tmp/debcheck/data/usr/bin/demo-app-backend \| grep -c "reset/argodds_config\|argodds_tools\|argodds-tools"` → **0**. Binary built 2026-06-23 (mtime). ZERO argodds-tools symbols. | W1's ESCALATE #3 worry is REAL — deployed deb predates argodds-tools. W1 only flagged demo-app-backend freshness. |
| 17 | NEW: Deployed `argogateway_0.1.0_amd64.deb` does NOT have `push_zenoh_router_config` handler at all | NEW BLOCKER (extends ESCALATE #3) | `ls -la code/ArgoDeploy/packages/argogateway_0.1.0_amd64.deb` → built 2026-06-30 (BEFORE `b98f1e2` 2026-08-11 which added the handler). `ar x` + `tar --use-compress-program=unzstd -xf data.tar.zst` extracted `usr/local/bin/argo-gateway-server`. `strings ... \| grep -c "PushZenohRouterConfig\|push_zenoh_router_config\|argodds_tools"` → **0**. Binary built 2026-06-23. Bundled `/etc/argo-gateway/env` in deb has only 5 lines (`RUST_LOG`, `SESSION_ID`, `BOT_TOKEN`, `GATEWAY_GRPC_PORT`) — NO `GATEWAY_TLS_*` vars. | W1 did NOT flag this — the deployed argogateway deb predates both `b98f1e2` (handler add) AND `feat/argo-tls` (TLS listener). On robots deployed with this deb, `PushZenohRouterConfig` RPC returns `unimplemented` BEFORE reaching BLOCKER 1 or 2. The newer argogateway deb at `code/ArgoGateway/argogateway_0.1.0_amd64.deb` (built 2026-08-18, 19MB) DOES contain `push_zenoh_router_config`, `argodds_tools`, `GATEWAY_TLS_*` env vars, `/run/argodds-tools/admin.sock` (verified via strings) — but it's NOT in `ArgoDeploy/packages/` so `install_cluster.sh:122` would install the OLDER deb. |
| 18 | `tls_mode` metadata key is dead data at server side (ESCALATE #4) | UPHOLD | `grep -rn "tls_mode" code/ArgoGateway/` → 0 hits. `git grep -n "tls_mode" origin/main -- demo_app_service/` → 0 hits. Only the frontend uses it (`NetworkConfigDialog.tsx:385,479,499`). | |
| 19 | `argo-zenoh-global.service` unit name not verified (ESCALATE #5) | UPHOLD (verified) | `find / -name "argo-zenoh-global.service"` (scoped to ai-stack) → found at `code/ArgoWatch/zenoh_config/argo-zenoh-global.service` AND `packaging/argo-zenoh/lib/systemd/system/argo-zenoh-global.service`. Unit file content: `ExecStart=/usr/lib/argo-zenoh/zenohd -c /etc/argo-zenoh/zenohd-global.json5`, `PartOf=argo-zenoh.target`, `Restart=on-failure`. Unit IS real and IS the one that reads the file argodds-tools writes. | |
| 20 | argodds-tools co-resident with demo-app-backend, no independent supervisor (ESCALATE #6) | UPHOLD | `git show origin/main:demo_app_service/crates/demo-app-backend/src/main.rs \| grep -n argodds_tools`: line 24 `mod argodds_tools;`, line 58 `let tools_sock = argodds_tools::env::sock_path();`, line 59-60 `tokio::spawn(async move { argodds_tools::server::spawn(tools_sock).await; });`. `demo-app-backend.service` (on origin/main): `Restart=on-failure; RestartSec=5`. So 5s window with no socket on crash. | |
| 21 | Other robot-side services not exhaustively checked for env writers (ESCALATE #7) | UPHOLD | V1 broadened grep across `/home/wangdang/work/ai-stack/`, `/home/wangdang/work/ai-stack-monitor/`, `/home/wangdang/work/agent_muti/`. No additional code path writes the 11 TLS env deltas (D4-D14) in response to a config push. `install.sh` writes D11+D12 plaintext only. `env.sh` does `export GATEWAY_TLS_ENABLE=1` (shell export, not file write). `argopilot/tools/real/start_robot12_full_stack.sh` uses `GATEWAY_URL` as docker env but doesn't write `/etc/argo-gateway/env`. `argopilot/tools/roboskillserver/sim_env_*.py` don't write the gateway env file. | |
| 22 | `gateway_env_file()` at `env.rs:30-34` | UPHOLD | `git show origin/main:.../env.rs \| sed -n '30,34p'`: `pub fn gateway_env_file() -> PathBuf { std::env::var("ARGO_GATEWAY_ENV_FILE").map(PathBuf::from).unwrap_or_else(|_| PathBuf::from(DEFAULT_GATEWAY_ENV_FILE)) }`. Exact match. | |
| 23 | `read_env_file` at `env.rs:43-57` (pure read function) | UPHOLD | `env.rs:43`: `pub fn read_env_file(path: &std::path::Path, key: &str) -> Option<String>`. Pure read. No write counterpart anywhere. | |
| 24 | `argodds_tools_client::map_apply_response` at `argodds_tools_client.rs:78-92` | UPHOLD | `sed -n '75,92p' argodds_tools_client.rs`: `pub fn map_apply_response(resp: &HttpResponse) -> (bool, String)` at line 78; closing `}` at line 92. `applied = matches!((resp.status, reason), (200, "applied") \| (200, "already_applied") \| (200, "dry_run_ok"))` — for `(400, "invalid_config")` returns `applied=false`. | |
| 25 | Route wiring at `connect.rs:119-120` | UPHOLD | `sed -n '119,120p' connect.rs`: line 119 `"/gateway.v1.FrontendRobotControlService/PushZenohRouterConfig",`, line 120 `post(push_zenoh_router_config),`. Exact match. | |
| 26 | `unary_robot_control!` macro at `connect.rs:350-354` | UPHOLD | `sed -n '348,355p' connect.rs`: lines 350-354 are `unary_robot_control!(\n    push_zenoh_router_config,\n    PushZenohRouterConfigRequest,\n    push_zenoh_router_config\n);`. Exact match. | |
| 27 | `atomic_write` at `manager.rs:435-443` (atomic rename via `fs::rename`) | UPHOLD | `git show origin/main:.../manager.rs \| sed -n '435,443p'`: `fn atomic_write(&self, content: &str) -> std::io::Result<()> { let tmp = self.tmp_path(); let mut f = fs::File::create(&tmp)?; f.write_all(content.as_bytes())?; f.sync_all()?; drop(f); fs::rename(&tmp, self.config_path())?; Ok(()) }`. Exact match. | |
| 28 | `self.atomic_write(&normalized)` called at `manager.rs:279` | UPHOLD | `sed -n '275,295p' manager.rs`: line 278 `// 9. 原子写`, line 279 `if let Err(e) = self.atomic_write(&normalized) {`. Exact match. | |
| 29 | `self.write_meta(&new_meta)` called at `manager.rs:313` | NUANCE | `sed -n '305,325p'` shows the `write_meta` call at line 315, not 313. Off by 2. | |
| 30 | `write_history` at `manager.rs:445-457` | UPHOLD | `git show origin/main:.../manager.rs \| sed -n '445,457p'`: `fn write_history(&self, entry: &HistoryEntry) -> std::io::Result<()> { ... }`. Exact match. | |
| 31 | `report()` reads env at `manager.rs:355-356` | UPHOLD | `sed -n '350,375p'` shows line 355 `let bot_name = env::read_env_file(&self.env_file, "BOT_NAME").unwrap_or_else(env::hostname);` and line 356 `let fleet_id = env::read_env_file(&self.env_file, "FLEET_ID").unwrap_or_default();`. Exact match. | |
| 32 | Gateway server reads TLS env vars once at startup (`main.rs:268-320`) and never re-reads on RPC | UPHOLD with NUANCE | `git show feat/argo-tls:src/argo-gateway-server/src/main.rs \| grep -n GATEWAY_TLS`: 19 hits including line 268 `if config.gateway_tls_enable && (...path missing...)`, line 282 `let tls_app = if config.gateway_tls_enable {`, line 299 `let tls_addr: SocketAddr = format!("0.0.0.0:{}", config.gateway_tls_port).parse()?;`, line 307 `axum_server::bind_rustls(tls_addr, tls_config)`. Reads via `envy` at startup. **BUT**: this code is ONLY on `feat/argo-tls`, NOT on `origin/main`. `git show origin/main:src/argo-gateway-server/src/main.rs \| grep GATEWAY_TLS` → 0 hits. The deployed deb (June 30) predates both `feat/argo-tls` AND `b98f1e2`. | If the deployed deb is from `origin/main` or older, the gateway has NO TLS listener code at all — Option A is even more NOT-IMPLEMENTED (no TLS support to enable). |

## 3. Missing code paths

V1 searched beyond W1's read set and found these additional env-writers /
config-handling paths W1 did not enumerate:

1. **`code/ArgoDeploy/real/install.sh:21-35`** — a SECOND shell writer of
   `/etc/argo-gateway/env` (separate from `install_cluster.sh`). Writes
   only `ZENOH_ENDPOINT` and `ZENOH_GLOBAL_ENDPOINT` (D11, D12) in
   plaintext mode — no TLS deltas. Triggered out-of-band by an operator
   running `install.sh`. Not triggered by `PushZenohRouterConfig`. Does
   not change the Option A verdict.

2. **`code/ArgoGateway/argogateway_0.1.0_amd64.deb`** (working dir, NOT in
   `ArgoDeploy/packages/`). Built 2026-08-18 from `feat/argo-tls`. V1
   `strings` on the extracted `usr/local/bin/argo-gateway-server` found
   6 hits for `PushZenohRouterConfig`/`argodds_tools` and 4 hits for
   `GATEWAY_TLS_*` env vars. This is the NEWER argogateway deb that
   has BOTH the handler AND the TLS listener code. W1's audit describes
   THIS deb's source behavior correctly. But `install_cluster.sh:122`
   installs from `ArgoDeploy/packages/` (which contains the OLDER June 30
   deb), not from `ArgoGateway/`. So unless the operator refreshes
   `ArgoDeploy/packages/` with the newer deb before running
   `install_cluster.sh`, the deployed robot gets the OLDER deb.

3. **`skyline-cloud-gateway-server/internal/gateway/robot_control_service.go`** —
   a Go `FrontendRobotControlService` implementation. W1 did not
   enumerate this. V1 checked the 90-line file: it implements
   `SubmitTask`, `CancelTask`, `GetTask`, `ListTasks`, `GetRobotStatus`,
   `GetLatestRobotState`, `RestartBot`, `SetSceneData`, `DebugQuery`, and
   `Chat` (returns `CodeUnimplemented`). It does NOT implement
   `PushZenohRouterConfig` at all — V1 grepped the file and the
   `cmd/gateway-server/main.go` for `PushZenohRouterConfig` and got zero
   matches. This is the cloud-side gateway (K8s bot scheduler, per its
   README), not the robot-side gateway. Not relevant to the SPEC
   question.

4. **No additional env writers found** in `code/argopilot/`,
   `code/argopilottools/`, `code/argowatch/`, `code/ArgoDDS/`,
   `code/sentinel/`, or any other service directory V1 grepped. W1's
   claim that no other service derives the 11 env deltas D4-D14 from a
   config push HOLDS.

## 4. Fabricated citations

**ZERO fabricated citations.** Every `file:line` W1 cited points at a
real file; the cited snippet exists at or near the cited line (off by
0-11 lines). Specific off-by-N line numbers:

| W1 citation | Actual location | Off by | Notes |
|---|---|---|---|
| `server.rs:35-37` (parser) | `server.rs:43-45` | 8 | function moved down by comments/imports above |
| `models.rs:7-19` (ResetRequest) | `models.rs:7-21` | 2 (end) | struct ends at line 21, not 19 |
| `models.rs:18` (router field) | `models.rs:20` | 2 | |
| `models.rs:21-25` (Metadata) | `models.rs:24-26` | 3 | |
| `manager.rs:313` (write_meta call) | `manager.rs:315` | 2 | |
| `manager.rs:549-562` (health check) | `manager.rs:549-563` | 1 (end) | |
| `manager.rs:538-563` (restart_and_healthcheck) | `manager.rs:539-563` | 1 (start) | |
| `manager.rs:616-631` (validate_router endpoints) | `manager.rs:617-631` | 1 (start) | |
| `manager.rs:625-631` (has_port check) | `manager.rs:625-631` | 0 | exact |
| `robot_control.rs:462-511` (handler) | `robot_control.rs:462-511` | 0 | exact (on `feat/argo-tls` working dir) |
| `robot_control.rs:474-478` (parser) | `robot_control.rs:474-478` | 0 | exact |
| `argodds_tools_client.rs:78-92` (map_apply_response) | `argodds_tools_client.rs:78-92` | 0 | exact |
| `connect.rs:119-120` (route wiring) | `connect.rs:119-120` | 0 | exact |
| `connect.rs:350-354` (macro) | `connect.rs:350-354` | 0 | exact |
| `manager.rs:435-443` (atomic_write) | `manager.rs:435-443` | 0 | exact |
| `manager.rs:445-457` (write_history) | `manager.rs:445-457` | 0 | exact |
| `manager.rs:279` (atomic_write call) | `manager.rs:279` | 0 | exact |
| `manager.rs:355-356` (env reads in report) | `manager.rs:355-356` | 0 | exact |
| `env.rs:30-34` (gateway_env_file) | `env.rs:30-34` | 0 | exact |
| `env.rs:5` (DEFAULT_GATEWAY_ENV_FILE) | `env.rs:5` | 0 | exact |
| `env.rs:43-57` (read_env_file) | `env.rs:43-57` | 0 | exact |
| `main.rs:268-320` (TLS listener) | `main.rs:268-320` on `feat/argo-tls`; ABSENT on `origin/main` | 0 on feat/argo-tls | see Claim 32 NUANCE — code is branch-specific |

## 5. Critical findings

### 5.1 BLOCKER 1 (validate_router rejects TLS endpoints): REAL

`manager.rs:607` `validate_router()` reads `listen.endpoints` as a JSON
array and checks `endpoints.iter().any(|e| e.as_str() ==
Some("tcp/0.0.0.0:57447"))` — strict string equality. The frontend's
TLS-mode config emits `["tcp/127.0.0.1:57449", "tls/0.0.0.0:57448"]`
(neither equals `tcp/0.0.0.0:57447`). Hand-trace:
- `obj.get("mode").as_str()` — must equal `"router"` (frontend emits `"router"`)
- `listen.endpoints` is array (✓)
- `target = "tcp/0.0.0.0:57447"` (computed from `ROUTER_PORT_STR`)
- `has_port = false` (no endpoint matches)
- Returns `Err("router.listen.endpoints must contain \"tcp/0.0.0.0:57447\"")`
- Daemon maps to HTTP 400 `invalid_config`
- Frontend sees `applied=false`, `detail="invalid_config: router.listen.endpoints must contain \"tcp/0.0.0.0:57447\""`

### 5.2 BLOCKER 2 (health check polls 57447 only): REAL

`manager.rs:538-563` `restart_and_healthcheck()` restarts
`argo-zenoh-global.service`, then polls `ss -tln` for the substring
`"0.0.0.0:57447"` (ROUTER_PORT_STR) with 5s budget / 500ms poll. A TLS
config produces `ss -tln` entries `127.0.0.1:57449` (loopback) and
`0.0.0.0:57448` (TLS) — neither contains the substring `0.0.0.0:57447`.
Health check times out → returns `Err("health check timeout: 0.0.0.0:57447
not LISTEN after restart")` → daemon rolls back via `atomic_write` of the
previous config + re-runs `restart_and_healthcheck` (lines 286-294) →
returns `ResetOutcome::RestartFailed { detail }` → daemon maps to HTTP 500
`restart_failed` → frontend sees `applied=false`, `detail="restart_failed:
health check timeout: 0.0.0.0:57447 not LISTEN after restart"`.

### 5.3 NEW BLOCKER 3 (deployed debs predate the handler + daemon)

V1 extracted both deployed debs via `ar x` + `tar -xf` and ran `strings`
on the inner binaries:

- **`code/ArgoDeploy/packages/argogateway_0.1.0_amd64.deb`** (built
  2026-06-30 16:51; binary mtime 2026-06-23):
  `strings usr/local/bin/argo-gateway-server | grep -c "PushZenohRouterConfig\|push_zenoh_router_config\|argodds_tools"` → **0**.
  The handler was added on 2026-08-11 in commit `b98f1e2 feat: argodds
  config push via unix socket` — 6 weeks AFTER this deb was built.
  Bundled `/etc/argo-gateway/env` in deb has 5 lines (RUST_LOG,
  SESSION_ID, BOT_TOKEN, GATEWAY_GRPC_PORT) — no `GATEWAY_TLS_*` vars
  (TLS env vars were added in `feat/argo-tls` branch, also after June 30).

- **`code/ArgoDeploy/packages/demo-app-backend_0.1.0-1_amd64.deb`**
  (built 2026-06-30 16:51; binary mtime 2026-06-23):
  `strings usr/bin/demo-app-backend | grep -c "reset/argodds_config\|argodds_tools\|argodds-tools"` → **0**.
  The argodds-tools merge was on 2026-08-12 in commit `9252dda` — 6
  weeks AFTER this deb was built.

**Implication**: If a robot is deployed using the current state of
`code/ArgoDeploy/packages/`, the production `argo-gateway-server` does
NOT have the `push_zenoh_router_config` handler. The frontend's
`PushZenohRouterConfig` RPC fails with gRPC `UNIMPLEMENTED` at the
axum router (route is not registered) — this happens BEFORE BLOCKER 1
or BLOCKER 2 can even be hit. Even plaintext pushes would fail.

The NEWER argogateway deb at `code/ArgoGateway/argogateway_0.1.0_amd64.deb`
(built 2026-08-18, 19MB) DOES contain the handler + TLS listener code
(V1 verified via `strings`: 6 hits for `PushZenohRouterConfig` /
`argodds_tools`, 4 hits for `GATEWAY_TLS_*` env vars, hits for
`/run/argodds-tools/admin.sock`, `/reset/argodds_config`,
`gateway_tls_enable`, `build rustls ServerConfig`,
`GATEWAY_TLS_ENABLE=1 but cert/key/root-ca path missing`,
`Both plaintext and TLS endpoints are disabled`). But this newer deb is
NOT in `ArgoDeploy/packages/` so `install_cluster.sh:122` would install
the OLDER deb unless the operator manually refreshes the packages dir.

W1's ESCALATE #3 flagged the demo-app-backend deb freshness concern but
DID NOT flag the argogateway deb freshness concern. V1's NEW BLOCKER 3
strengthens W1's "NOT safe to deploy as-is" verdict — it does not
overturn it.

### 5.4 No path the server already handles TLS that W1 missed

V1 confirmed by direct file read:
- The handler (`robot_control.rs:462-511`) does NOT inspect `metadata["tls_mode"]` (only `metadata["operator"]`).
- The handler does NOT branch on the presence of `transport.link.tls` block.
- The handler forwards the entire `router` JSON unchanged to `argodds-tools`.
- `argodds-tools` `manager.rs::reset()` does NOT inspect `transport.link.tls` either — it calls `validate_router()` (BLOCKER 1) and `restart_and_healthcheck()` (BLOCKER 2) and writes the config to `/etc/argo-zenoh/zenohd-global.json5`.
- No systemd generator, watcher, or inotify on `/etc/argo-zenoh/zenohd-global.json5` or `/etc/argo-gateway/env` exists.
- The postinst scripts only create a one-time default env file if absent.

There is NO code path on the server side that translates the
`transport.link.tls` block into the env-file deltas D4-D14. Option A is
NOT-IMPLEMENTED.

## 6. Final recommendation to orchestrator

**ACCEPT W1.** All four headline verdicts (E1 SAFE, Option A
NOT-IMPLEMENTED, BLOCKER 1 real, BLOCKER 2 real) are UPHOLD on the
latest source. W1's line numbers are slightly off in 6 places (off by
1-8 lines) but every cited snippet exists at a nearby line and the
semantic claims are correct. V1 additionally found a NEW BLOCKER 3 (the
deployed `argogateway` deb at `ArgoDeploy/packages/` predates the
handler addition by 6 weeks and contains zero `PushZenohRouterConfig`
symbols — so on currently-deployed robots the RPC fails with
`UNIMPLEMENTED` before BLOCKER 1/2 even apply) that strengthens W1's
"NOT safe to deploy as-is" verdict. The frontend change alone is
insufficient: it requires (a) rebuilding and redeploying both the
argogateway deb (with the `push_zenoh_router_config` handler + TLS
listener from `feat/argo-tls`) AND the demo-app-backend deb (with
argodds-tools from `origin/main` of ArgoWatch), (b) relaxing
`validate_router` to accept TLS endpoints, (c) relaxing
`restart_and_healthcheck` to poll the configured port, and (d)
implementing Option A env-file derivation in argodds-tools (or choosing
Option B from the prior audit — a separate out-of-band RPC).

---

## Appendix — exact reproduction steps

```bash
# Branch state
cd /home/wangdang/work/ai-stack/code/ArgoGateway && git branch --show-current
# → feat/argo-tls
cd /home/wangdang/work/ai-stack/code/ArgoWatch && git branch --show-current
# → feat/lifecycle-robot-takeover
cd /home/wangdang/work/ai-stack/code/ArgoWatch && git log --oneline origin/main -1
# → 9252dda Merge branch 'feat/argodds-tools-mvp' into 'main'

# Handler verification (on feat/argo-tls working dir)
sed -n '460,512p' /home/wangdang/work/ai-stack/code/ArgoGateway/src/argo-gateway-server/src/robot_control.rs
# shows push_zenoh_router_config at line 462-511

# Same handler on origin/main of ArgoGateway (different line numbers)
cd /home/wangdang/work/ai-stack/code/ArgoGateway && git show origin/main:src/argo-gateway-server/src/robot_control.rs | sed -n '520,575p'
# shows push_zenoh_router_config at line 522-572

# Daemon source (on origin/main of ArgoWatch, NOT on feat/lifecycle-robot-takeover)
cd /home/wangdang/work/ai-stack/code/ArgoWatch && git show origin/main:demo_app_service/crates/demo-app-backend/src/argodds_tools/server.rs | grep -n from_value
# → 43:    let req = match serde_json::from_value::<crate::argodds_tools::models::ResetRequest>(body.0,)

cd /home/wangdang/work/ai-stack/code/ArgoWatch && git show origin/main:demo_app_service/crates/demo-app-backend/src/argodds_tools/models.rs | head -25
# → struct ResetRequest at lines 7-21; router: serde_json::Value at line 20; no deny_unknown_fields

# deny_unknown_fields — zero hits across both layers
grep -rn "deny_unknown_fields" /home/wangdang/work/ai-stack/code/ArgoGateway/  # → 0 hits
cd /home/wangdang/work/ai-stack/code/ArgoWatch && git grep -n "deny_unknown_fields" origin/main -- demo_app_service/  # → 0 hits

# BLOCKER 1 — validate_router
cd /home/wangdang/work/ai-stack/code/ArgoWatch && git show origin/main:demo_app_service/crates/demo-app-backend/src/argodds_tools/manager.rs | sed -n '600,680p'
# → fn validate_router at line 607; has_port check at line 626; Err return at line 627-630

# BLOCKER 2 — restart_and_healthcheck
cd /home/wangdang/work/ai-stack/code/ArgoWatch && git show origin/main:demo_app_service/crates/demo-app-backend/src/argodds_tools/manager.rs | sed -n '535,575p'
# → fn restart_and_healthcheck at line 539; ss -tln contains ROUTER_PORT_STR check at line 554

# Option A — env writers
grep -rln "tee.*argo-gateway/env\|>.*argo-gateway/env" /home/wangdang/work/ai-stack/code/ 2>/dev/null | grep -v node_modules | grep -v target
# → install_cluster.sh, install.sh, postinst (3 copies)

# NEW BLOCKER 3 — deployed deb freshness
cd /tmp && rm -rf debcheck && mkdir debcheck && cd debcheck && \
  ar x /home/wangdang/work/ai-stack/code/ArgoDeploy/packages/argogateway_0.1.0_amd64.deb && \
  mkdir data && cd data && tar --use-compress-program=unzstd -xf ../data.tar.zst && \
  strings usr/local/bin/argo-gateway-server | grep -c "PushZenohRouterConfig\|argodds_tools"
# → 0

cd /tmp && rm -rf debcheck && mkdir debcheck && cd debcheck && \
  ar x /home/wangdang/work/ai-stack/code/ArgoDeploy/packages/demo-app-backend_0.1.0-1_amd64.deb && \
  mkdir data && cd data && tar -xf ../data.tar.xz && \
  strings usr/bin/demo-app-backend | grep -c "reset/argodds_config\|argodds_tools"
# → 0

# Newer argogateway deb (working dir) DOES have handler
cd /tmp && rm -rf debcheck3 && mkdir debcheck3 && cd debcheck3 && \
  ar x /home/wangdang/work/ai-stack/code/ArgoGateway/argogateway_0.1.0_amd64.deb && \
  mkdir data && cd data && tar --use-compress-program=unzstd -xf ../data.tar.zst && \
  strings usr/local/bin/argo-gateway-server | grep -c "PushZenohRouterConfig\|argodds_tools"
# → 6
```
