# W1-REPORT — Gateway server `PushZenohRouterConfig` handler audit (E1 + Option A)

## 1. Summary

The gateway server's `PushZenohRouterConfig` handler parses the received
`config_json5` as a dynamic `serde_json::Value` and forwards it unchanged to a
separate `argodds-tools` daemon (embedded in `demo-app-backend`) over a Unix
socket. Neither layer uses `#[serde(deny_unknown_fields)]`, so the new
`transport.link.tls` block emitted by the frontend is accepted at parse time.
**E1: SAFE.** However, `argodds-tools`'s `validate_router` hard-requires
`tcp/0.0.0.0:57447` in `listen.endpoints`, which the TLS-shaped config does
NOT contain — so TLS-mode pushes will be rejected with `invalid_config` even
though E1 itself is safe. The daemon writes only `/etc/argo-zenoh/zenohd-global.json5`
(+ meta + history) and restarts only `argo-zenoh-global.service`. It never
writes `/etc/argo-gateway/env` and never restarts `argogateway.target`.
**Option A: NOT-IMPLEMENTED.** The frontend change is NOT safe to deploy
as-is: it will fail at `validate_router`, and even if that were relaxed it
would not light up TLS on the gateway because no code path derives the env
deltas D4–D14 from the received config.

- **E1: SAFE** (parser is `serde_json::Value`; no `deny_unknown_fields` at
  either the gateway server or the `argodds-tools` daemon).
- **Option A: NOT-IMPLEMENTED** (no env-file derivation anywhere; daemon
  only writes zenohd config + restarts `argo-zenoh-global.service`).

## 2. Method

### Trees searched (priority order from SPEC)
1. `/home/wangdang/work/ai-stack/` — found `code/ArgoGateway/` (Rust workspace, primary).
2. `/home/wangdang/work/ai-stack-monitor/` — only `argofleet/` present; no ArgoGateway source.
3. `/home/wangdang/work/agent_muti/ArgoDDS/` — has `argo-admin-space`, `argo-admin-spaced`, `argo-cli`, `argo-dds`, `argo-dds-py`, `argo-monitoring`; NONE of these is the `argodds-tools` daemon (they are topology monitor / CLI / DDS lib).

### Grep patterns run
- `find /home/wangdang/work/ai-stack -maxdepth 4 -type d \( -name "argogateway" -o -name "argo-gateway" -o -name "gateway-server" ... \)` — discovered 11 candidate dirs; narrowed to `code/ArgoGateway/` because it has `Cargo.toml` + `build-deb.sh` + `argogateway_0.1.0_amd64.deb` matching `install_cluster.sh:122`.
- `grep -rn "PushZenohRouterConfig|push_zenoh_router_config|pushZenohRouterConfig"` across `code/ArgoGateway/` — found handler at `src/argo-gateway-server/src/robot_control.rs:462`.
- `grep -rln "argodds-tools|argodds_tools|admin.sock|/reset/argodds_config"` across all three roots — found references only inside `code/ArgoGateway/` (the CLIENT of argodds-tools). The daemon source is NOT in any searched root on the current checked-out branch.
- `find /home/wangdang -name "argodds-tools*"` — no binary/deb named `argodds-tools*`; the daemon is embedded in `demo-app-backend` binary.
- `git log --oneline --all --grep="argodds-tools"` in `code/ArgoWatch/` — found merge commit `9252dda Merge branch 'feat/argodds-tools-mvp' into 'main'` (2026-08-12).
- `git ls-tree -r origin/main --name-only | grep argodds_tools` in `code/ArgoWatch/` — confirmed 8 files at `demo_app_service/crates/demo-app-backend/src/argodds_tools/{mod,server,manager,models,env,diff,net,tests}.rs` on `origin/main`.
- `git show origin/main:<path>` — used to read each argodds-tools source file from `origin/main` WITHOUT modifying the working tree (current branch `feat/lifecycle-robot-takeover` does NOT contain these files).
- `grep -rln "GATEWAY_TLS_ENABLE|GATEWAY_TLS_PORT|GATEWAY_TLS_CERT_PATH|/etc/argo-gateway/env"` across `code/ArgoGateway/`, `code/ArgoWatch/`, `code/ArgoDeploy/` — confirmed ArgoGateway only READS these env vars at startup; no writer anywhere except `install_cluster.sh`.

### Files read end-to-end
- `/home/wangdang/work/ai-stack/code/ArgoGateway/src/argo-gateway-server/src/robot_control.rs` (1–512, full)
- `/home/wangdang/work/ai-stack/code/ArgoGateway/src/argo-gateway-server/src/argodds_tools_client.rs` (1–228, full)
- `/home/wangdang/work/ai-stack/code/ArgoGateway/src/argo-gateway-server/src/main.rs` (1–340+ partial; 240–340 for TLS listener startup)
- `/home/wangdang/work/ai-stack/code/ArgoGateway/src/argo-gateway-server/src/connect.rs` (110–125, 340–375)
- `/home/wangdang/work/ai-stack/code/ArgoGateway/package/DEBIAN/postinst` (full)
- `/home/wangdang/work/ai-stack/code/ArgoGateway/package/src/argogateway-server.service` (full)
- `git show origin/main:demo_app_service/crates/demo-app-backend/src/argodds_tools/mod.rs` (full)
- `git show origin/main:demo_app_service/crates/demo-app-backend/src/argodds_tools/server.rs` (full, 88 lines)
- `git show origin/main:demo_app_service/crates/demo-app-backend/src/argodds_tools/manager.rs` (full, 716 lines)
- `git show origin/main:demo_app_service/crates/demo-app-backend/src/argodds_tools/models.rs` (full, 135 lines)
- `git show origin/main:demo_app_service/crates/demo-app-backend/src/argodds_tools/env.rs` (full, 80 lines)
- `git show origin/main:demo_app_service/crates/demo-app-backend/src/argodds_tools/diff.rs` (head only — diff util, not load-bearing)
- `git show origin/main:demo_app_service/crates/demo-app-backend/src/main.rs` (head — confirmed `tokio::spawn(argodds_tools::server::spawn(tools_sock))` at lines 58–60)
- `git show origin/main:demo_app_service/crates/demo-app-backend/Cargo.toml` (confirmed `demo-app-backend` binary includes argodds_tools module)
- `/home/wangdang/work/ai-stack/code/ArgoDeploy/real/install_cluster.sh` (1–190, full)
- `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-backend/debian/demo-app-backend.service` (full — confirmed `EnvironmentFile=/etc/argo-gateway/env` is read-only input)
- `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-backend/debian/scripts/postinst` (full — no env derivation)
- `/home/wangdang/work/ai-stack/packaging/argo-zenoh/DEBIAN/postinst` (full — no env derivation)
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src/components/manage-robot/zenohRouterConfig.ts` (lines 8–16, 219–276, 339–378 — confirmed TLS branch emits `["tcp/127.0.0.1:57449", "tls/0.0.0.0:57448"]` and NO `tcp/0.0.0.0:57447`)
- `/home/wangdang/work/ai-stack/docs/superpowers/specs/2026-08-04-argodds-router-config-design.md` (full — design contract for argodds-tools)

### No `cargo check` was needed
The serde attributes are visible directly in the source (no macro-generated
structs). `cargo check --offline` was not run.

## 3. Q1 — Server source location

**Primary server (the gRPC handler):** `/home/wangdang/work/ai-stack/code/ArgoGateway/`
- Language: Rust 2021 edition.
- Build: Cargo workspace with 10 crates (`Cargo.toml` workspace members listed
  in §3 of `code/ArgoGateway/CLAUDE.md`).
- Primary binary crate: `src/argo-gateway-server/` (binary name
  `argo-gateway-server`).
- Packaging: `package/build-deb.sh` produces `argogateway_0.1.0_amd64.deb`,
  which `install_cluster.sh:122` installs via `dpkg -i`. The same deb sits at
  `code/ArgoGateway/argogateway_0.1.0_amd64.deb` (artifact) and
  `code/ArgoDeploy/packages/argogateway_0.1.0_amd64.deb` (deploy input).
- systemd unit: `argogateway-server.service` (in deb) —
  `ExecStart=/usr/local/bin/argo-gateway-server`,
  `EnvironmentFile=/etc/argo-gateway/env`, part of `argogateway.target`.

**Forwarded-to daemon (the actual config applier):**
`/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-backend/`
- Language: Rust 2021 edition.
- The `argodds-tools` Unix-socket server is a MODULE inside the
  `demo-app-backend` binary, NOT a standalone crate. Spawned at
  `demo-app-backend/src/main.rs:58-60`:
  `tokio::spawn(async move { argodds_tools::server::spawn(tools_sock).await; });`
- Built into `demo-app-backend_0.1.0-1_amd64.deb`, installed by
  `install_cluster.sh:178`.
- systemd unit: `demo-app-backend.service`, also uses
  `EnvironmentFile=/etc/argo-gateway/env` (read-only).
- **IMPORTANT**: the `argodds_tools/` module exists on `origin/main` (merged
  2026-08-12 in commit `9252dda`) but is NOT present on the currently
  checked-out branch `feat/lifecycle-robot-takeover`. W1 read the source via
  `git show origin/main:<path>`. The deployed `demo-app-backend_0.1.0-1_amd64.deb`
  in `code/ArgoDeploy/packages/` was built from a `main`-branch snapshot that
  includes argodds-tools (V1 must verify this by checking the deb's build
  provenance or by running `strings` on the binary to look for
  `/reset/argodds_config`).

**Search roots where the daemon is NOT found**:
- `/home/wangdang/work/ai-stack-monitor/` — no `argodds-tools` source.
- `/home/wangdang/work/agent_muti/ArgoDDS/` — has `argo-admin-spaced` (topology
  monitor) and `argo-cli` (CLI), neither of which serves `/reset/argodds_config`.

## 4. Q2 — `PushZenohRouterConfig` handler

**Handler file:line**: `/home/wangdang/work/ai-stack/code/ArgoGateway/src/argo-gateway-server/src/robot_control.rs:462-511`

**Function signature** (lines 462–465):
```rust
async fn push_zenoh_router_config(
    &self,
    request: Request<PushZenohRouterConfigRequest>,
) -> Result<Response<PushZenohRouterConfigResponse>, Status> {
```

**Route wiring**: `connect.rs:119-120`:
```rust
.route(
    "/gateway.v1.FrontendRobotControlService/PushZenohRouterConfig",
    post(push_zenoh_router_config),
)
```
The `post(push_zenoh_router_config)` reference at `connect.rs:120` is the
axum handler produced by the `unary_robot_control!` macro at
`connect.rs:350-354`. There is only ONE implementation of the
`FrontendRobotControlService::push_zenoh_router_config` trait method — the
one at `robot_control.rs:462`.

**High-level behavior** (5 steps, lines 466–510):
1. Validate session (`self.get_session(&req.session_id)?` — line 467).
2. Read `operator` from `req.metadata` (lines 469–473). NOTE: only `operator`
   is read; the new `tls_mode` metadata key is NOT inspected.
3. Parse `req.config_json5` as `serde_json::Value` (lines 474–478). On parse
   failure: return `Status::invalid_argument("config_json5 must be valid JSON/JSON5")`.
4. Build a JSON body wrapping the router (lines 480–487):
   ```rust
   let body = json!({
       "mode": "manual",
       "source": "demoapp",
       "operator": operator,
       "dry_run": false,
       "schema_version": 1,
       "router": router,
   });
   ```
5. POST the body to `argodds-tools` Unix socket at path
   `/reset/argodds_config` via `crate::argodds_tools_client::post_json`
   (lines 489–495). On socket failure: return
   `Status::internal("failed to reach argodds-tools")`.
6. Map the daemon's HTTP response to `(applied, detail)` via
   `map_apply_response` (line 497) and return `PushZenohRouterConfigResponse`
   (lines 505–510).

The handler does NOT itself write any file to disk, does NOT touch
`/etc/argo-gateway/env`, and does NOT restart any service. It only forwards
to `argodds-tools`.

## 5. Q3 — Handler behavior on received config

| Aspect | Evidence |
|---|---|
| Parser used at gateway server | `serde_json::from_str::<serde_json::Value>` at `robot_control.rs:474-478`. Dynamic JSON tree, no typed struct. |
| Struct's serde attributes (gateway server) | None — `serde_json::Value` is a library type with no `deny_unknown_fields`. The only error path is `serde_json::Error` when the input is not valid JSON. |
| Parser used at argodds-tools daemon | `serde_json::from_value::<ResetRequest>` at `server.rs:35-37`. `ResetRequest` (models.rs:7-19) is a typed struct, BUT its `router` field is typed `pub router: serde_json::Value` (line 18). The outer struct uses `#[derive(Debug, Clone, Deserialize, Serialize)]` with NO `deny_unknown_fields`. |
| Would `transport` top-level field be accepted? | **YES at both layers.** At the gateway server, the entire config is parsed as `Value` (any JSON accepted). At argodds-tools, the `router` field of `ResetRequest` is itself `serde_json::Value`, so any sub-field including `transport` is accepted. The outer `ResetRequest` struct does NOT have `deny_unknown_fields`, so even an extra top-level key in the request body would be ignored. Evidence: models.rs:7-19 has only `#[derive(Debug, Clone, Deserialize, Serialize)]`, no `#[serde(deny_unknown_fields)]`. |
| Where is the config written to disk? | NOT at the gateway server. At argodds-tools: `/etc/argo-zenoh/zenohd-global.json5` (atomic rename via `atomic_write` at `manager.rs:435-443`, called from `manager.rs:279`). Also writes `/etc/argo-zenoh/.config_meta.json` (`manager.rs:382-385`) and `/etc/argo-zenoh/history/<v>__<src>__<ts>.json5` (`manager.rs:445-457`). |
| Where is env file derived from config? | **NOWHERE.** `argodds-tools` reads `/etc/argo-gateway/env` ONLY in `report()` (`manager.rs:355-356`) for `BOT_NAME` and `FLEET_ID`. No write to `/etc/argo-gateway/env` exists anywhere in the daemon. `gateway_env_file()` is plumbed in (`env.rs:30-34`, `manager.rs:128/137/145/151`) but only ever read. |
| Where is a service restarted? | `argodds-tools` restarts `argo-zenoh-global.service` (`manager.rs:538-563`). It does NOT restart `argogateway.target` or any gateway-side unit. The gateway server itself never restarts anything in this RPC path. |
| Where is `metadata` field read? | Gateway server reads only `metadata["operator"]` (`robot_control.rs:469-473`). The new `tls_mode` key is NOT read. argodds-tools reads `metadata` only in fleet mode for `config_version` / `generated_at` (`manager.rs:193-213`, `models.rs:21-25`). `tls_mode` is NOT read at either layer. |

## 6. Q4 — Other config-handling paths

Bullet list of every other code path that handles the zenohd-global config or
`/etc/argo-gateway/env`:

- **`install_cluster.sh`** (lines 78–102, 124–170): the deploy script. It
  writes `/etc/argo-zenoh/zenohd-global.json5` directly via `sudo tee` (TLS
  branch at lines 80–92, plaintext branch at lines 95–101) and writes
  `/etc/argo-gateway/env` directly via `sudo tee` (TLS branch at lines
  126–150, plaintext branch at lines 153–169). It then restarts
  `argo-zenoh.target` (line 119) and `argogateway.target` (line 173). This is
  the ONLY code path that derives env-file TLS deltas D4–D14. It runs
  out-of-band, triggered by an operator running `install_cluster.sh --tlsdeploy`.
  It is NOT triggered by `PushZenohRouterConfig`.
- **`ArgoGateway package/DEBIAN/postinst`**: creates a DEFAULT
  `/etc/argo-gateway/env` (with `GATEWAY_TLS_ENABLE=0`,
  `GATEWAY_TLS_PORT=50053`, empty cert paths) IF AND ONLY IF the file does
  not already exist. One-time, no derivation from zenohd config.
- **`argo-zenoh package/DEBIAN/postinst`**: creates `argo-zenoh` user +
  `/var/lib/argo-zenoh` + `/var/log/robot/argo-zenoh`. No env derivation.
- **`demo-app-backend package/DEBIAN/postinst`**: creates
  `/var/log/robot/demo-app-backend` + `systemctl enable demo-app-backend`. No
  env derivation.
- **`argo-gateway-server/src/main.rs`** (lines 268–320): at STARTUP, reads
  `GATEWAY_TLS_ENABLE`, `GATEWAY_TLS_PORT`, `GATEWAY_TLS_CERT_PATH`,
  `GATEWAY_TLS_KEY_PATH`, `GATEWAY_TLS_ROOT_CA_PATH`, `GATEWAY_GRPC_ENABLE`
  from environment (populated by systemd `EnvironmentFile=/etc/argo-gateway/env`).
  Conditionally spawns a TLS listener on `0.0.0.0:${GATEWAY_TLS_PORT}`. Does
  NOT re-read these on `PushZenohRouterConfig` — they are read once at
  process startup.
- **No systemd generator, no watcher, no inotify** on
  `/etc/argo-zenoh/zenohd-global.json5` or `/etc/argo-gateway/env` was found
  in any searched root. `grep -rln "systemd.generator|postinst|config.watch|watch.*config|env.generator"`
  returned only the postinst scripts already enumerated above and irrelevant
  node_modules hits.

## 7. Q5 — E1 verdict: SAFE

**Verdict: SAFE** — the new `transport` top-level field will NOT cause a
parse failure at either the gateway server or the `argodds-tools` daemon.

### Evidence
1. **Gateway server parser** — `robot_control.rs:474-478`:
   ```rust
   let router: serde_json::Value =
       serde_json::from_str(&req.config_json5).map_err(|e| {
           warn!(error = %format!("{e:#}"), "config_json5 is not valid JSON");
           Status::invalid_argument("config_json5 must be valid JSON/JSON5")
       })?;
   ```
   `serde_json::Value` accepts any valid JSON. No `deny_unknown_fields`
   attribute is possible on a library type. The only failure mode is
   syntactically invalid JSON.

2. **argodds-tools daemon parser** — `server.rs:35-37`:
   ```rust
   let req = match serde_json::from_value::<crate::argodds_tools::models::ResetRequest>(
       body.0,
   ) {
       Ok(r) => r,
       Err(e) => { ... }
   };
   ```
   `ResetRequest` at `models.rs:7-19`:
   ```rust
   #[derive(Debug, Clone, Deserialize, Serialize)]
   pub struct ResetRequest {
       pub mode: String,
       pub source: String,
       pub operator: Option<String>,
       #[serde(default)]
       pub dry_run: bool,
       pub schema_version: i64,
       pub metadata: Option<Metadata>,
       pub router: serde_json::Value,
   }
   ```
   NO `#[serde(deny_unknown_fields)]`. The `router` field is
   `serde_json::Value`, so any sub-field of `router` (including the new
   `transport` block) is accepted. Even an extra top-level key in the
   request body would be silently dropped (serde's default behavior without
   `deny_unknown_fields`).

### Important caveat (NOT the E1 question, but the user's actual goal)
Although E1 itself is SAFE, the TLS-mode push will STILL FAIL server-side at a
DIFFERENT check — see ESCALATE #1 in §10. This is a content-validation
rejection, not a parse rejection; E1 is technically SAFE but the frontend
change is not deployable as-is.

## 8. Q6 — Option A verdict: NOT-IMPLEMENTED

**Verdict: NOT-IMPLEMENTED** — the server does NOT translate the
`transport.link.tls` block (or any TLS signal) into writes to
`/etc/argo-gateway/env`. No env-file deltas D4–D14 are derived from the
received config. The gateway's own TLS state is controlled entirely by the
out-of-band `install_cluster.sh --tlsdeploy` step.

### Evidence
1. **argodds-tools writes only zenohd files**. `manager.rs:reset()` (lines
   173–326) performs these filesystem side effects:
   - `atomic_write(&normalized)` at line 279 → writes
     `/etc/argo-zenoh/zenohd-global.json5` (`atomic_write` at lines 435–443
     uses `fs::rename` over a `.tmp` file).
   - `self.write_meta(&new_meta)` at line 313 → writes
     `/etc/argo-zenoh/.config_meta.json`.
   - `self.write_history(entry)` at line 274 → writes
     `/etc/argo-zenoh/history/<v>__<src>__<ts>.json5`.
   None of these is `/etc/argo-gateway/env`.

2. **argodds-tools reads `/etc/argo-gateway/env` but never writes it**.
   `env.rs:30-34`:
   ```rust
   pub fn gateway_env_file() -> PathBuf {
       std::env::var("ARGO_GATEWAY_ENV_FILE")
           .map(PathBuf::from)
           .unwrap_or_else(|_| PathBuf::from(DEFAULT_GATEWAY_ENV_FILE))
   }
   ```
   `DEFAULT_GATEWAY_ENV_FILE = "/etc/argo-gateway/env"` (env.rs:5). The
   `env_file` field is plumbed into `ConfigManager` (manager.rs:128, 137,
   145, 151) but only ever used in `report()`:
   ```rust
   // manager.rs:355-356
   let bot_name = env::read_env_file(&self.env_file, "BOT_NAME").unwrap_or_else(env::hostname);
   let fleet_id = env::read_env_file(&self.env_file, "FLEET_ID").unwrap_or_default();
   ```
   `env::read_env_file` (env.rs:43-57) is a pure READ function. There is no
   `write_env_file` anywhere in the argodds-tools module.

3. **grep for TLS env var writes**:
   `grep -rn "GATEWAY_TLS_ENABLE|GATEWAY_TLS_PORT|GATEWAY_TLS_CERT_PATH|GATEWAY_TLS_KEY_PATH|GATEWAY_TLS_ROOT_CA_PATH|GATEWAY_TLS_CA_CERT_PATH|GATEWAY_TLS_DOMAIN|GATEWAY_GRPC_ENABLE|GATEWAY_URL|ZENOH_ENDPOINT|ZENOH_GLOBAL_ENDPOINT"` across
   `code/ArgoGateway/src/` and `code/ArgoWatch/demo_app_service/crates/demo-app-backend/src/argodds_tools/` returns ONLY read sites (`std::env::var(...)` at gateway-server startup, `env::read_env_file(...)` in `report()`). No write sites.

4. **argodds-tools restarts the wrong unit for Option A**. `manager.rs:538-563`:
   ```rust
   fn restart_and_healthcheck(&self) -> Result<(), String> {
       let status = std::process::Command::new("systemctl")
           .args(["restart", "argo-zenoh-global.service"])
           .output()
           ...
   ```
   It restarts `argo-zenoh-global.service`, NOT `argogateway.target`. Even
   if it wrote the env deltas, the gateway would not pick them up without a
   restart of `argogateway.target`.

5. **The gateway server reads TLS env once at startup**. `main.rs:268-320`:
   `GATEWAY_TLS_ENABLE` is read into `config.gateway_tls_enable` at startup
   (via envy + systemd `EnvironmentFile=`). The TLS listener is spawned
   conditionally on this value. There is no code path that re-reads the env
   file when a `PushZenohRouterConfig` RPC arrives. So even if argodds-tools
   were to write the env file, the gateway would not pick up the change until
   `argogateway.target` is restarted.

6. **No other writer**. The SPEC's list of 11 env deltas (D4–D14) has
   exactly ONE writer across all searched roots: `install_cluster.sh` (lines
   126–150). No other script, postinst, generator, or runtime code writes
   these variables.

### Confirmation that the handler just writes config to disk
The handler at `robot_control.rs:462-511` does NOT write to disk itself —
it forwards the config to argodds-tools, which writes
`/etc/argo-zenoh/zenohd-global.json5` (NOT `/etc/argo-gateway/env`). So the
SPEC's NOT-IMPLEMENTED criterion ("the handler just writes config_json5 to
disk without deriving env") is satisfied by the forwarding chain: the only
disk write is the zenohd config, not the env file.

## 9. Recommendations

### For E1 (no server-side change needed for the parser itself)
No change needed. The parser is `serde_json::Value` at both layers. The
`transport` block is accepted.

### For the BLOCKING issue (ESCALATE #1: `validate_router` rejects TLS config)
Even though E1 is SAFE, the frontend change is NOT deployable as-is because
`argodds-tools`'s `validate_router` (manager.rs:607-667) hard-requires
`listen.endpoints` to contain `"tcp/0.0.0.0:57447"`:

```rust
// manager.rs:616-631
let listen = obj.get("listen").and_then(|v| v.as_object())
    .ok_or_else(|| "router.listen missing or not object".to_string())?;
let endpoints = listen.get("endpoints").and_then(|v| v.as_array())
    .ok_or_else(|| "router.listen.endpoints must be array".to_string())?;
let target = format!("tcp/{ROUTER_PORT_STR}");
let has_port = endpoints.iter().any(|e| e.as_str() == Some(target.as_str()));
if !has_port {
    return Err(format!(
        "router.listen.endpoints must contain \"tcp/{ROUTER_PORT_STR}\""
    ));
}
```

where `ROUTER_PORT_STR = "0.0.0.0:57447"` (manager.rs:36). The frontend's
TLS branch emits `["tcp/127.0.0.1:57449", "tls/0.0.0.0:57448"]` (per the
prior impl REPORT and confirmed at
`zenohRouterConfig.ts:276`), which does NOT contain `tcp/0.0.0.0:57447`. So
`validate_router` returns `Err("router.listen.endpoints must contain
\"tcp/0.0.0.0:57447\"")`, the daemon returns HTTP 400 with
`reason: "invalid_config"`, and the gateway server maps this to
`applied=false, detail="invalid_config: router.listen.endpoints must
contain \"tcp/0.0.0.0:57447\""` (argodds_tools_client.rs:78-92). The
frontend's `PushZenohRouterConfigResponse` will have `applied=false`.

**Server-side change needed (prose, not implemented):**
1. Relax `validate_router` to accept EITHER `tcp/0.0.0.0:57447` (plaintext)
   OR `tls/0.0.0.0:57448` + `tcp/127.0.0.1:57449` (TLS) in
   `listen.endpoints`. The TLS branch should additionally require the
   `transport.link.tls` block with `listen_certificate`,
   `listen_private_key`, `root_ca_certificate` fields.
2. Relax `restart_and_healthcheck` (manager.rs:549-562) to poll for the
   appropriate port based on the applied config (57447 for plaintext, 57448
   for TLS). Currently it polls `ss -tln` for `0.0.0.0:57447` only — a TLS
   config would never match and the health check would time out, triggering
   rollback (manager.rs:287-294).

### For Option A (NOT-IMPLEMENTED)
**Server-side change needed (prose, not implemented):**
Add a new step in `argodds-tools`'s `reset()` flow (after the atomic write
succeeds, before/alongside `restart_and_healthcheck`) that detects a
`transport.link.tls` block in the received `router` JSON and, when present,
writes the 11 env deltas to `/etc/argo-gateway/env`:

- `GATEWAY_TLS_ENABLE=1`
- `GATEWAY_TLS_PORT=50053`
- `GATEWAY_TLS_CERT_PATH=/etc/argo-tls/node.crt`
- `GATEWAY_TLS_KEY_PATH=/etc/argo-tls/node.key`
- `GATEWAY_TLS_ROOT_CA_PATH=/etc/argo-tls/root.crt`
- `GATEWAY_TLS_CA_CERT_PATH=/etc/argo-tls/root.crt`
- `GATEWAY_TLS_DOMAIN=$HOSTNAME`
- `GATEWAY_GRPC_ENABLE=0`
- `GATEWAY_URL=https://127.0.0.1:50053`
- `ZENOH_ENDPOINT=tcp/127.0.0.1:57449`
- `ZENOH_GLOBAL_ENDPOINT=tcp/127.0.0.1:57449`

…and then restarts `argogateway.target` (in addition to the existing
`argo-zenoh-global.service` restart). When the TLS block is ABSENT, the
inverse deltas should be written (back to plaintext defaults) and
`argogateway.target` restarted.

Alternatively (simpler, fewer moving parts), keep `argodds-tools` ONLY
responsible for the zenohd config and create a NEW out-of-band operator
step (analogous to `install_cluster.sh --tlsdeploy`) that the frontend
triggers via a separate RPC. This is the Option B from the prior audit's
§7. The trade-off: more frontend surface, but cleaner separation of
concerns (config-management daemon should not be writing another service's
env file).

### For the metadata `tls_mode` key (ESCALATE #2)
The frontend's new `tls_mode` metadata key is currently ignored by both the
gateway server and the argodds-tools daemon. If the user wants the server to
branch on TLS mode explicitly (rather than inferring from the presence of
`transport.link.tls`), the handler at `robot_control.rs:469-473` should
also read `metadata["tls_mode"]` and pass it through to argodds-tools
(e.g., as a new field in `ResetRequest`). Otherwise the `tls_mode` key is
dead data.

### If E1 is UNKNOWN or server source not found
Not applicable — server source was found and E1 is definitively SAFE.

## 10. ESCALATEs

Judgment calls W1 made alone:

1. **CRITICAL — TLS-mode push will FAIL at `validate_router` even though E1
   is SAFE.** `argodds-tools/manager.rs:616-631` hard-requires
   `tcp/0.0.0.0:57447` in `listen.endpoints`. The frontend's TLS config
   emits `["tcp/127.0.0.1:57449", "tls/0.0.0.0:57448"]` (no 57447). The
   daemon returns HTTP 400 `invalid_config`; the frontend sees
   `applied=false`. This is NOT the E1 risk (E1 is about
   `deny_unknown_fields`), but it has the same user-visible symptom (TLS-mode
   push fails server-side). User must decide: relax `validate_router`
   server-side, or change the frontend's TLS branch to keep
   `tcp/0.0.0.0:57447` in the listen list (which would NOT match
   `install_cluster.sh:80-91`'s shape and would break the install-script
   parity the prior impl was trying to maintain).

2. **CRITICAL — Even if `validate_router` were relaxed, the
   `restart_and_healthcheck` at `manager.rs:549-562` polls `ss -tln` for
   `0.0.0.0:57447 LISTEN`.** A TLS config has 57448/57449, so the health
   check times out (5s budget, 500ms poll), the daemon rolls back the
   config (manager.rs:287-294), and returns `reason: "restart_failed"`.
   Frontend sees `applied=false` with detail
   `"restart_failed: health check timeout: 0.0.0.0:57447 not LISTEN after
   restart"`. Server-side fix needed: poll for the port actually in
   `listen.endpoints`.

3. **`argodds-tools` source is on `origin/main`, NOT on the currently
   checked-out branch `feat/lifecycle-robot-takeover`.** W1 read the source
   via `git show origin/main:<path>`. The deployed
   `demo-app-backend_0.1.0-1_amd64.deb` in `code/ArgoDeploy/packages/` must
   be verified to have been built from a `main`-branch commit that includes
   the argodds-tools merge (`9252dda` or descendant). If the deb was built
   from an older `main` snapshot BEFORE 2026-08-12, the daemon is NOT
   running on production robots, and `PushZenohRouterConfig` would fail at
   the gateway server with `Status::internal("failed to reach argodds-tools")`
   (robot_control.rs:494) because the Unix socket
   `/run/argodds-tools/admin.sock` does not exist. V1 should verify by
   running `strings /home/wangdang/work/ai-stack/code/ArgoDeploy/packages/demo-app-backend_0.1.0-1_amd64.deb
   | grep -c "reset/argodds_config"` (expect > 0) or by extracting the deb
   and running `demo-app-backend --help` to confirm the argodds-tools
   module is compiled in.

4. **The `tls_mode` metadata key added by the prior frontend impl is dead
   data at the server side.** Neither `robot_control.rs:469-473` (gateway
   server) nor `argodds_tools/models.rs:21-25` (daemon) reads `tls_mode`.
   The gateway server only reads `metadata["operator"]`. The daemon's
   `Metadata` struct only has `config_version` and `generated_at`. If the
   user intended `tls_mode` to drive server-side branching, the handler
   and the daemon's `ResetRequest` schema must be extended. If the user
   intended `tls_mode` only as a human-readable audit hint (recorded in
   history entries via `metadata`), no server change is needed but the
   history entry schema in `argodds-tools` does not currently preserve
   arbitrary metadata keys either — `ConfigMeta` (manager.rs:111-121) has
   only `config_version`, `generated_at`, `source`, `operator`,
   `applied_at`, `config_hash`, `mode`. `tls_mode` would be silently
   dropped.

5. **The daemon's `argo-zenoh-global.service` restart target name assumes a
   specific systemd unit layout.** `manager.rs:540` runs `systemctl restart
   argo-zenoh-global.service`. The deploy script's `argo-zenoh.target`
   (`install_cluster.sh:118-119`) is the unit that `install_cluster.sh`
   restarts. These may be different units — `argo-zenoh.target` is a
   group/sentinel that pulls in `argo-zenoh-local.service` AND
   `argo-zenoh-global.service`, but the daemon only restarts the global
   one. If the daemon's restart leaves the local service untouched, that is
   probably correct (TLS only affects global), but V1 should confirm the
   unit name `argo-zenoh-global.service` actually exists in the deployed
   deb's systemd units. W1 did not verify this.

6. **The argodds-tools daemon is co-resident with `demo-app-backend`'s other
   responsibilities** (chat action dispatcher, lifecycle runtime observer).
   If `demo-app-backend` crashes, the argodds-tools Unix-socket server
   dies too. There is no supervisor that respawns just the
   argodds-tools listener. The systemd unit `demo-app-backend.service`
   has `Restart=on-failure; RestartSec=5` so the whole binary restarts,
   but during the 5 s window the socket is gone and
   `PushZenohRouterConfig` will fail with `Status::internal`. This is
   a reliability concern, not a correctness concern.

7. **W1 did not exhaustively verify that no OTHER service on the robot
   writes `/etc/argo-gateway/env` from the zenohd config.** The search
   covered `code/ArgoGateway/`, `code/ArgoWatch/`, `code/ArgoDeploy/`,
   `packaging/`, and the three SPEC search roots. It did NOT cover the
   `argopilot` container, `roboskillserver`, `sentinel`, `fluent-bit`, or
   any other deb-installed service that might run on the robot. These are
   unlikely to touch the gateway env file (their roles are robot control /
   logging / monitoring, not gateway config), but if V1 finds a writer W1
   missed, the Option A verdict may need revision.
