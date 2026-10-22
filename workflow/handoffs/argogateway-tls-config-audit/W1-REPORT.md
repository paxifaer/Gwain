# W1-REPORT — ArgoGateway TLS-mode config audit (robot-app-platform vs install_cluster.sh)

## 1. Summary

**Verdict: GAP.** When the user enables TLS in the `robot-app-platform` frontend (the "使用 TLS 加密" checkbox in `AddRobotDialog.tsx`), the only thing that changes is the CLIENT-side HTTP transport URL between the Tauri app and the gateway (`https://<host>:50053` vs `http://<host>:50051`). No ArgoDDS or ArgoGateway SERVER configuration is generated differently in TLS mode. The sole ArgoDDS config-generation surface — `buildZenohRouterConfig()` in `zenohRouterConfig.ts` (demo + skyline) — always emits a fixed plaintext-shaped `zenohd-global` config (`tcp/0.0.0.0:57447` listen, no `transport.link.tls` block, no TLS endpoints, no cert paths). The frontend has no code path that writes `/etc/argo-gateway/env` at all, so every env-file TLS delta from `install_cluster.sh` is structurally unmirrored. 14 deltas identified, 0 mirrored, 14 gaps, 0 partial.

## 2. Method

### Files read end-to-end
- `/home/wangdang/work/ai-stack/code/ArgoDeploy/real/install_cluster.sh` (1–190, full)
- `/home/wangdang/work/ai-stack/code/ArgoDeploy/real/env.sh` (full, for variable defaults)
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/AGENTS.md` (full)
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/CLAUDE.md` (full)
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src/components/manage-robot/zenohRouterConfig.ts` (1–355, full)
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src/components/manage-robot/NetworkConfigDialog.tsx` (1–778, full)
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src/queries/networkConfig.ts` (1–48, full)
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src/services/robot-endpoint.ts` (1–56, full)
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src/components/manage-robot/AddRobotDialog.tsx` (1–558, partial; 320–558 fully)
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src/components/manage-robot/TlsFailDialog.tsx` (1–90)
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src/components/manage-robot/TlsStatusIcon.tsx` (1–60)
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/demo/src-tauri/src/argo_tls.rs` (1–100)
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src/features/projects/workspace/networkConfig/zenohRouterConfig.ts` (1–355, full)
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src/features/projects/workspace/networkConfig/NetworkConfigDialog.tsx` (1–100)
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src/features/projects/workspace/RealGatewayServerAddressField.tsx` (TLS hint lines only via grep)
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src/features/dev/DevTlsStatusPage.tsx` (1–60)
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/apps/skyline/src/routes/dev/tls-status.tsx` (1–12, full)
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/packages/gateway-client/src/proto/gateway/v1/robot_control_pb.ts` (1300–1362, `PushZenohRouterConfigRequest/Response`)
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/docs/guides/demo-tls-fix-2026-08-18.md` (1–172, full — for prior-session context)

### Grep patterns run (all from robot-app-platform root, excluding node_modules)
- `grep -rli "argogateway|argodds|argo_tls|argo-gateway"` (RS/TS/TSX/JSON/TOML/MD)
- `grep -rli "tls"` (RS/TS/TSX)
- `grep -rli "GATEWAY_TLS_ENABLE|57449|57448|57447|zenohd-global|zenohd_local|argo-zenoh|install_cluster|argo-gateway/env|GATEWAY_TLS_PORT|GATEWAY_TLS_CERT_PATH"`
- `grep -rli "deploy|install_cluster|argo-deploy|argodeploy|ArgoDeploy"`
- `grep -rn "use_tls|useTls|enable.*tls|tls.*enable|tlsMode|tls_mode|plaintext|TlsToggle|toggleTls|TLS_ENABLE"`
- `grep -rn "PushZenohRouterConfig|push_zenoh_router|pushZenohRouter|argo_zenoh|zenohd"`
- `grep -rn "fn .*tls|tls_config|tls_deploy|GATEWAY_TLS|gateway_tls|install_cluster|argo-gateway"` (RS)
- `grep -n "tls|Tls|TLS"` on `RealGatewayServerDialog.tsx` and `RealGatewayServerAddressField.tsx`
- `grep -rln "PushZenohRouterConfig|PushArgoTls|PushGatewayEnv|InstallCluster|install_cluster|argo-zenoh-target|argo-gateway-target"`

### Line ranges examined for the gap conclusion
- `install_cluster.sh` lines 19–23 (master `--tlsdeploy` switch), 78–102 (zenohd-global.json5 branch), 106–115 (cert perms), 124–170 (`/etc/argo-gateway/env` branch).
- `apps/demo/src/components/manage-robot/zenohRouterConfig.ts` lines 8–27 (constants + type), 187–241 (builder), 275–346 (validator).
- `apps/demo/src/components/manage-robot/AddRobotDialog.tsx` lines 418–495 (TLS checkbox + payload builder), 504–529 (`buildManualSubmitPayload`).
- `packages/gateway-client/src/proto/gateway/v1/robot_control_pb.ts` lines 1300–1322 (request schema).

## 3. Q1 — install_cluster.sh TLS branches

Master switch: `--tlsdeploy` CLI flag at lines 10–23 sets `GATEWAY_TLS_ENABLE=1` (TLS mode) or `0` (plaintext mode). All branches below key off `GATEWAY_TLS_ENABLE`.

| delta_id | file:line | TLS-mode value | plaintext-mode value |
|---|---|---|---|
| D1 | install_cluster.sh:83 vs 98 | `listen.endpoints: ["${ZENOH_GLOBAL_ENDPOINT_LOOPBACK}", "${ZENOH_GLOBAL_ENDPOINT_TLS}"]` → `["tcp/127.0.0.1:57449", "tls/0.0.0.0:57448"]` | `listen.endpoints: ["${ZENOH_GLOBAL_ENDPOINT_PLAINTEXT:-tcp/0.0.0.0:57447}"]` → `["tcp/0.0.0.0:57447"]` |
| D2 | install_cluster.sh:85–90 | `transport: { link: { tls: { listen_certificate: "/etc/argo-tls/node.crt", listen_private_key: "/etc/argo-tls/node.key", root_ca_certificate: "/etc/argo-tls/root.crt", enable_mtls: false }}}` present in zenohd-global.json5 | `transport` block absent from zenohd-global.json5 |
| D3 | install_cluster.sh:106–115 | `chgrp argo-zenoh /etc/argo-tls/node.key; chmod 640 /etc/argo-tls/node.key; chmod 644 /etc/argo-tls/node.crt; chmod 644 /etc/argo-tls/root.crt` (runs when cert files exist, which is the TLS-deployed state) | Same `if -f` blocks are no-ops because cert files are not deployed in plaintext mode |
| D4 | install_cluster.sh:128 vs 155 | `ZENOH_ENDPOINT=${ZENOH_ENDPOINT:-tcp/127.0.0.1:57449}` | `ZENOH_ENDPOINT=${ZENOH_ENDPOINT:-tcp/127.0.0.1:7447}` |
| D5 | install_cluster.sh:130 vs 157 | `ZENOH_GLOBAL_ENDPOINT=${ZENOH_GLOBAL_ENDPOINT_LOOPBACK}` → `tcp/127.0.0.1:57449` | `ZENOH_GLOBAL_ENDPOINT=${ZENOH_GLOBAL_ENDPOINT_PLAINTEXT:-tcp/0.0.0.0:57447}` |
| D6 | install_cluster.sh:137 | `GATEWAY_GRPC_ENABLE=0` (closes 50051) | line absent (50051 stays open) |
| D7 | install_cluster.sh:142 | `GATEWAY_TLS_ENABLE=1` | line absent |
| D8 | install_cluster.sh:143 | `GATEWAY_TLS_PORT=${GATEWAY_TLS_PORT:-50053}` | line absent |
| D9 | install_cluster.sh:144 | `GATEWAY_TLS_CERT_PATH=${GATEWAY_TLS_CERT_PATH:-/etc/argo-tls/node.crt}` | line absent |
| D10 | install_cluster.sh:145 | `GATEWAY_TLS_KEY_PATH=${GATEWAY_TLS_KEY_PATH:-/etc/argo-tls/node.key}` | line absent |
| D11 | install_cluster.sh:146 | `GATEWAY_TLS_ROOT_CA_PATH=${GATEWAY_TLS_ROOT_CA_PATH:-/etc/argo-tls/root.crt}` | line absent |
| D12 | install_cluster.sh:147 vs 168 | `GATEWAY_URL=${GATEWAY_URL:-https://127.0.0.1:50053}` | `GATEWAY_URL=${GATEWAY_URL:-http://127.0.0.1:50051}` |
| D13 | install_cluster.sh:148 | `GATEWAY_TLS_CA_CERT_PATH=${GATEWAY_TLS_CA_CERT_PATH:-/etc/argo-tls/root.crt}` | line absent |
| D14 | install_cluster.sh:149 | `GATEWAY_TLS_DOMAIN=${GATEWAY_TLS_DOMAIN:-${HOSTNAME}}` | line absent |

Notes:
- D3 is technically unconditional in the script (the `if -f` blocks run in both modes), but the cert files only exist in TLS mode (deployed separately via scp per the script's own comment at lines 104–105). It is therefore a de facto TLS-only delta.
- env.sh (sourced at install_cluster.sh:7) defines `ZENOH_GLOBAL_ENDPOINT_TLS=tls/0.0.0.0:57448`, `ZENOH_GLOBAL_ENDPOINT_LOOPBACK=tcp/127.0.0.1:57449`, `ZENOH_GLOBAL_ENDPOINT_PLAINTEXT=tcp/0.0.0.0:57447`, `GATEWAY_TLS_ENABLE=1`, `GATEWAY_TLS_PORT=50053`, `GATEWAY_TLS_CERT_PATH=/etc/argo-tls/node.crt`, `GATEWAY_TLS_KEY_PATH=/etc/argo-tls/node.key`. These are the values the script's `${VAR:-default}` expansions resolve to.

## 4. Q2 — robot-app-platform config-generation surface

Code locations where ArgoDDS / ArgoGateway config is built, sent, or persisted (with TLS reference status):

1. `apps/demo/src/components/manage-robot/zenohRouterConfig.ts:187–241` — `buildZenohRouterConfig()` builds the zenohd-global JSON5 text. **Does NOT reference TLS at all.** Hardcodes `listen.endpoints: ["tcp/0.0.0.0:57447"]` (line 230) and never emits a `transport.link.tls` block. The `ZenohRouterConfig` type (lines 15–27) has no `transport` field.
2. `apps/demo/src/components/manage-robot/zenohRouterConfig.ts:275–346` — `validateZenohRouterConfig()` actively rejects any config that does NOT include `tcp/0.0.0.0:57447` in `listen.endpoints` (line 299–301 pushes `router.listen.endpoints.mustInclude0.0.0.0:57447`). This validator blocks TLS-shaped configs even via raw-JSON edit.
3. `apps/demo/src/components/manage-robot/NetworkConfigDialog.tsx:280–286` — calls `buildZenohRouterConfig` to generate `rawText`. No TLS toggle in dialog UI; only peer-robot checkboxes and manual endpoints.
4. `apps/demo/src/queries/networkConfig.ts:23–41` — `pushZenohRouterConfig()` invokes gRPC `PushZenohRouterConfig`. Request carries only `configJson5`, `metadata`, `requestId`, `sessionId`. No TLS field; `metadata` is set to `{operator: "demoapp"}` only (NetworkConfigDialog.tsx:354).
5. `apps/skyline/src/features/projects/workspace/networkConfig/zenohRouterConfig.ts:187–241` — skyline equivalent, byte-identical to demo's `zenohRouterConfig.ts`. Same plaintext-only builder. Same `validateZenohRouterConfig` rejection at lines 299–301.
6. `apps/skyline/src/features/projects/workspace/networkConfig/NetworkConfigDialog.tsx` — skyline equivalent dialog. Has a "TLS fallback to plaintext" branch at lines 421–479, but that only re-runs the same push over a plaintext CLIENT-side HTTP transport when the TLS handshake to the gateway fails — it does NOT change the config payload.
7. `apps/skyline/src/features/projects/workspace/networkConfig/networkConfigQuery.ts:23–45` — skyline mutation, same shape as demo.
8. `packages/gateway-client/src/proto/gateway/v1/robot_control_pb.ts:1300–1322` — `PushZenohRouterConfigRequest` proto schema: fields are `request_id`, `session_id`, `config_json5`, `metadata`. No TLS field. No `PushGatewayEnv` or `InstallCluster` RPC exists in the proto file.
9. `apps/demo/src/components/manage-robot/AddRobotDialog.tsx:418–495` — the "使用 TLS 加密" checkbox (this is what the user's "click TLS" refers to). Flips `useTls` state, changes IP placeholder to `:50053`, calls `buildManualSubmitPayload` (lines 507–529) which produces `gatewayBaseUrl: https://<host>:50053` + `plaintextGatewayUrl: http://<host>:50051`. This is CLIENT-side HTTP transport only; it does NOT trigger any ArgoDDS / ArgoGateway config generation.
10. `apps/demo/src-tauri/src/argo_tls.rs` (and `apps/skyline/src-tauri/src/argo_tls.rs`) — CLIENT-side mTLS: `tls_log` (line 17), `load_root_cert` (line 84), `has_root_cert` (line 89), `apply_mtls` (line 284), `build_http_client` (line 349), `gateway_mtls_proxy` (line 502). Reads certs from `~/.argo-tls/` on the CLIENT machine. Does NOT generate or push any server config.
11. `apps/demo/src/services/robot-endpoint.ts:27–55` — `resolveEndpoint()` derives `tlsStatus` from `robot.tlsPort` + `hasRootCert`. Auto-decided, not user-toggled. Only affects the CLIENT's HTTPS URL.
12. `apps/skyline/src/features/projects/workspace/RealGatewayServerAddressField.tsx:26,87,124–142` — `:50053` suffix detection + TLS hint UI. CLIENT-side URL concern only.

No code path in `robot-app-platform` writes `/etc/argo-gateway/env`, `/etc/argo-zenoh/zenohd-local.json5`, or any cert file under `/etc/argo-tls/` on the robot host. The only config the frontend can push to the robot is the `zenohd-global.json5` text via `PushZenohRouterConfig`, and that path is structurally plaintext-only.

## 5. Q3 — Gap matrix

| delta_id (from Q1) | mirrored? | location (file:line) | evidence (≤3 lines) |
|---|---|---|---|
| D1 (zenohd-global listen endpoints) | NO | apps/demo/.../zenohRouterConfig.ts:230 | `listen: { endpoints: [ZENOH_ROUTER_LISTEN_ENDPOINT] },` (line 230) where `ZENOH_ROUTER_LISTEN_ENDPOINT = "tcp/0.0.0.0:57447"` (line 9). No `tls/0.0.0.0:57448` and no `tcp/127.0.0.1:57449` loopback are ever emitted. |
| D2 (transport.link.tls block) | NO | apps/demo/.../zenohRouterConfig.ts:15–27, 228–240 | `ZenohRouterConfig` type has no `transport` field; builder returns `{mode, listen, connect, scouting}` only — no `transport.link.tls` block ever produced. |
| D3 (cert file perms on /etc/argo-tls/*) | NO | (no frontend location) | Frontend has no code path that touches `/etc/argo-tls/` on the robot host. `argo_tls.rs` reads `~/.argo-tls/` on the CLIENT machine (different concern). |
| D4 (ZENOH_ENDPOINT default) | NO | (no frontend location) | Frontend never writes `/etc/argo-gateway/env`. No `PushGatewayEnv` RPC exists in the proto. |
| D5 (ZENOH_GLOBAL_ENDPOINT) | NO | (no frontend location) | Frontend never writes `/etc/argo-gateway/env`. The zenohd-global config at zenohRouterConfig.ts:230 uses the plaintext `tcp/0.0.0.0:57447` value with no TLS alternative. |
| D6 (GATEWAY_GRPC_ENABLE=0) | NO | (no frontend location) | Frontend never writes `/etc/argo-gateway/env`. |
| D7 (GATEWAY_TLS_ENABLE=1) | NO | (no frontend location) | Frontend never writes `/etc/argo-gateway/env`. |
| D8 (GATEWAY_TLS_PORT=50053) | NO | (no frontend location) | Frontend never writes `/etc/argo-gateway/env`. Note: `AddRobotDialog.tsx:504,523` references port 50053, but only for the CLIENT-side HTTPS URL, not the gateway's own env var. |
| D9 (GATEWAY_TLS_CERT_PATH) | NO | (no frontend location) | Frontend never writes `/etc/argo-gateway/env`. |
| D10 (GATEWAY_TLS_KEY_PATH) | NO | (no frontend location) | Frontend never writes `/etc/argo-gateway/env`. |
| D11 (GATEWAY_TLS_ROOT_CA_PATH) | NO | (no frontend location) | Frontend never writes `/etc/argo-gateway/env`. |
| D12 (GATEWAY_URL https vs http) | NO | (no frontend location) | Frontend never writes `/etc/argo-gateway/env`. Note: `AddRobotDialog.tsx:523,526` builds `https://<host>:50053` and `http://<host>:50051` as CLIENT-side URLs, not the gateway's own `GATEWAY_URL` env var. |
| D13 (GATEWAY_TLS_CA_CERT_PATH) | NO | (no frontend location) | Frontend never writes `/etc/argo-gateway/env`. |
| D14 (GATEWAY_TLS_DOMAIN) | NO | (no frontend location) | Frontend never writes `/etc/argo-gateway/env`. |

Summary: 14 deltas, 0 YES, 14 NO, 0 PARTIAL.

## 6. Q4 — Symmetric gaps

TLS-mode concerns that `robot-app-platform` handles but `install_cluster.sh` does not:

- **CLIENT-side mTLS plumbing** — `apps/demo/src-tauri/src/argo_tls.rs` and `apps/skyline/src-tauri/src/argo_tls.rs` implement client-cert loading, root-CA loading, reqwest mTLS client builder, and an HTTP/2 mTLS proxy to the gateway at port 50053. `install_cluster.sh` is a server-side deploy script and contains no client-runtime code; this is an orthogonal concern, not a config-generation gap. Listed for completeness; it does not close any Q3 gap.
- **Cross-platform cert-path resolution** — `argo_tls.rs` resolves `~/.argo-tls/` via `USERPROFILE` (Windows) then `HOME` (Linux) then `.` (per the W5 fix in `docs/guides/demo-tls-fix-2026-08-18.md`). `install_cluster.sh` does not run on Windows and has no equivalent.
- **TLS debug log** — `argo_tls.rs:17` writes `~/.argo-tls/argo-tls-debug.log` for TLS decision-point tracing. `install_cluster.sh` has no equivalent.
- **TLS status auto-detection** — `apps/demo/src/services/robot-endpoint.ts:27–55` derives `tlsStatus: "encrypted" | "ca-missing" | "tls-failed" | "plain"` from `robot.tlsPort` and local `hasRootCert`. `install_cluster.sh` has no equivalent (it is a push-mode script, not a connection-mode runtime).

None of these symmetric concerns affect the primary question: they are all CLIENT-side runtime concerns, not SERVER-side config generation.

## 7. Recommendations

The user decides whether to dispatch a Develop worker. The recommendations below describe, in prose, what would need to change in `robot-app-platform` to close each gap. They are NOT implemented here.

### For D1 and D2 (zenohd-global.json5 TLS config generation)

The `ZenohRouterConfig` type at `apps/demo/src/components/manage-robot/zenohRouterConfig.ts:15–27` and the skyline twin at the same relative path need a TLS mode. The builder `buildZenohRouterConfig` at line 187 should accept a TLS flag (e.g. `enableTls: boolean`) and, when true, emit a config shape that matches `install_cluster.sh` lines 80–91: `listen.endpoints: ["tcp/127.0.0.1:57449", "tls/0.0.0.0:57448"]` plus a `transport: { link: { tls: { listen_certificate: "/etc/argo-tls/node.crt", listen_private_key: "/etc/argo-tls/node.key", root_ca_certificate: "/etc/argo-tls/root.crt", enable_mtls: false }}}` block. The plaintext branch should keep the current `["tcp/0.0.0.0:57447"]` listen endpoint and omit the `transport` block. New constants (`ZENOH_ROUTER_TLS_PORT = 57448`, `ZENOH_ROUTER_LOOPBACK_ENDPOINT = "tcp/127.0.0.1:57449"`, cert-path constants) should live alongside `ZENOH_ROUTER_PORT` at line 8.

The `NetworkConfigDialog.tsx` (demo line 238+, skyline equivalent) needs a TLS toggle in the dialog UI — either a checkbox or a value derived from the target robot's `tlsStatus`. The toggle's state must flow into `buildZenohRouterConfig` via a new parameter and into `usePushZenohRouterConfigMutation`'s metadata (or a new field) so the server can disambiguate.

The validator `validateZenohRouterConfig` at lines 275–346 must be relaxed for TLS mode: the `router.listen.endpoints.mustInclude0.0.0.0:57447` check at line 299–301 must NOT fire when the config is TLS-shaped, otherwise even hand-edited TLS configs will be rejected by the frontend before push. The same validator must also accept the new `transport.link.tls` block shape.

### For D3 (cert file permissions)

The frontend cannot directly `chgrp`/`chmod` files on the robot host — `PushZenohRouterConfig` is a gRPC RPC, not an SSH shell. Two options the user can choose between: (a) add a new server-side RPC `PushArgoTlsCertPermissions` that the gateway server applies on the robot host (requires gateway-server changes, not just frontend); (b) document that cert deploy + perms remain an out-of-band SSH/SCP step (as `install_cluster.sh:104–105` comment already suggests) and the frontend does not attempt to mirror D3. Option (b) is the smaller change. Either way, the frontend itself does not need new code if (b) is chosen.

### For D4 through D14 (env file deltas)

The frontend has no `/etc/argo-gateway/env` writer at all. To mirror D4–D14 the user has two design options:

Option A (server-side derivation): the gateway server derives the env-file TLS deltas from the zenohd-global config it receives via `PushZenohRouterConfig`. If the config contains a `transport.link.tls` block, the gateway server writes `GATEWAY_TLS_ENABLE=1`, `GATEWAY_TLS_PORT=50053`, `GATEWAY_TLS_CERT_PATH=/etc/argo-tls/node.crt`, `GATEWAY_TLS_KEY_PATH=/etc/argo-tls/node.key`, `GATEWAY_TLS_ROOT_CA_PATH=/etc/argo-tls/root.crt`, `GATEWAY_TLS_CA_CERT_PATH=/etc/argo-tls/root.crt`, `GATEWAY_TLS_DOMAIN=$HOSTNAME`, `GATEWAY_GRPC_ENABLE=0`, `GATEWAY_URL=https://127.0.0.1:50053`, `ZENOH_ENDPOINT=tcp/127.0.0.1:57449`, `ZENOH_GLOBAL_ENDPOINT=tcp/127.0.0.1:57449` to `/etc/argo-gateway/env` and restarts `argogateway.target`. This requires NO frontend changes beyond D1+D2 — the env-file deltas become a server-side consequence of the TLS block in the zenohd config.

Option B (new frontend RPC): add a new `PushGatewayEnvConfig` RPC to `packages/gateway-client` and a corresponding Tauri command + UI dialog. The frontend explicitly writes the env file. This duplicates `install_cluster.sh` lines 124–170 in TypeScript, which is a larger surface and harder to keep in sync with the script.

Option A is the smaller and more maintainable change. The frontend's only job under Option A is to emit the correct zenohd-global config (D1+D2); the server-side translation closes D4–D14.

### Recommendation summary

The minimal change that closes the most gaps with the least new surface area is: implement D1+D2 in the frontend (extend `buildZenohRouterConfig` + `ZenohRouterConfig` type + `NetworkConfigDialog` UI + `validateZenohRouterConfig`), and let the gateway server derive D4–D14 from the TLS block. D3 stays an out-of-band SSH/SCP step (documented, not automated by the frontend). This makes the frontend's "click TLS" actually produce a different ArgoDDS config in the places where `install_cluster.sh` also branches.

## 8. ESCALATEs

Judgment calls W1 made alone:

1. **"Click TLS" was interpreted as the "使用 TLS 加密" checkbox in `apps/demo/src/components/manage-robot/AddRobotDialog.tsx:418–495`.** This is the only TLS toggle in the demo UI. Skyline's equivalent is the `:50053` suffix detection in `RealGatewayServerAddressField.tsx` plus `DevTlsStatusPage`. If the user meant a future/planned TLS toggle in `NetworkConfigDialog` that does not yet exist, the verdict is still GAP because there is no toggle there today.

2. **"ArgoDDS / ArgoGateway configuration" was interpreted as the two artifacts `install_cluster.sh` itself branches on: `zenohd-global.json5` (and `zenohd-local.json5`) for ArgoDDS, and `/etc/argo-gateway/env` for ArgoGateway.** If the user's definition of "ArgoGateway config" includes other artifacts (e.g., systemd unit files, argogateway deb postinst), those are not in `install_cluster.sh`'s branch surface and were not enumerated.

3. **The frontend's `argo_tls.rs` and `AddRobotDialog` "use TLS" checkbox were classified as CLIENT-side mTLS plumbing, NOT ArgoDDS/ArgoGateway config generation.** They produce HTTPS URLs and load client certs; they do not push any server config. If the user considers these as "the TLS click that should produce different server config," the answer is still GAP — these paths produce no server config at all.

4. **`install_cluster.sh` lines 106–115 (cert perms) are technically unconditional `if -f` blocks that run in both modes.** They are no-ops in plaintext mode only because the cert files do not exist. I recorded this as delta D3 with a note that it is a de facto TLS-only delta. A stricter reading would omit D3 from Q1 entirely; under that reading the Q1 count would be 13 and the gap count 13, but the verdict remains GAP.

5. **`metadata` field in `PushZenohRouterConfigRequest` (line 1321 of `robot_control_pb.ts`) is a free-form `map<string, string>`.** I checked the only call site in `NetworkConfigDialog.tsx:354` and it sets only `{operator: "demoapp"}`. I did not exhaustively search every potential future call site for a hidden TLS metadata key. If such a call site exists that I missed, the gateway server may already be deriving TLS state from metadata — but no such code path is visible in the frontend today.

6. **Skyline's `NetworkConfigDialog.tsx` has a "TLS fallback to plaintext" branch at lines 421–479** that re-runs the push with a plaintext gateway URL when the TLS handshake fails. I confirmed this only changes the CLIENT-side HTTP transport (TLS → plaintext for the RPC itself), not the config payload. If the user interprets this branch as a "TLS toggle," the verdict is still GAP — the config payload is unchanged.

7. **The gateway server-side handling of `PushZenohRouterConfig` is out of scope for this audit** (the SPEC restricts the read set to `install_cluster.sh` + `robot-app-platform`). Whether the gateway server translates a `transport.link.tls` block in the received config into env-file changes (Option A in §7) cannot be verified from the frontend codebase alone. The frontend's gap exists regardless of server-side behavior because the frontend never emits the TLS block in the first place.
