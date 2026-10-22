# V1-VERDICT — Adversarial verification of W1-REPORT (argogateway-tls-config-audit)

## 1. Overall verdict

**CONFIRM.** W1's `GAP` verdict holds. Every key claim, every Q1 delta, and every Q3 `NO` was re-checked against the source; none overturned. One minor wording nuance on claim 4 (validator "actively rejects" TLS) does not change the conclusion.

## 2. Per-claim verdicts

### Key claim 1 — `buildZenohRouterConfig()` always emits plaintext (demo + skyline twin)

| | |
|---|---|
| verdict | **UPHOLD** |
| evidence | `apps/demo/src/components/manage-robot/zenohRouterConfig.ts:187-241` — function signature `(targetRobotIp, peerRobots, manualEndpoints)` has no TLS flag; line 230 `listen: { endpoints: [ZENOH_ROUTER_LISTEN_ENDPOINT] }` where `ZENOH_ROUTER_LISTEN_ENDPOINT = \`tcp/0.0.0.0:${ZENOH_ROUTER_PORT}\`` (line 9) and `ZENOH_ROUTER_PORT = 57447` (line 8). Return type `ZenohRouterConfig` (lines 15-27) has fields `mode, listen, connect, scouting` — no `transport`. |
| notes | Skyline twin `apps/skyline/src/features/projects/workspace/networkConfig/zenohRouterConfig.ts:187-241` is byte-identical to demo's (verified by `diff`). No alternative TLS-producing call site found (grep for `buildZenohRouterConfig` returns only NetworkConfigDialog.tsx + tests). |

### Key claim 2 — "使用 TLS 加密" checkbox only flips CLIENT-side HTTPS URLs

| | |
|---|---|
| verdict | **UPHOLD** |
| evidence | `apps/demo/src/components/manage-robot/AddRobotDialog.tsx:418-495` — `<Field>` contains the FieldLabel "使用 TLS 加密" (line 423) + a `<Checkbox>` (lines 455-469) whose `onCheckedChange` calls `onUseTlsChange(Boolean(checked))`. `onUseTlsChange` is wired to `setUseTls` (line 687). On submit, `buildManualSubmitPayload` (lines 507-529) returns `{gatewayBaseUrl: \`https://${host}:50053\`, plaintextGatewayUrl: \`http://${host}:50051\`, tlsStatus: ...}` — no env, no cert, no server config field. |
| notes | Traced the parent: `apps/demo/src/routes/manage-robot.tsx:435-549` `handleAddRobot` consumes the payload only to call `RobotSDK.connect(robotIp, undefined, undefined, robotName, gatewayBaseUrl)` — a CLIENT-side connection. No `pushZenohRouterConfig` is invoked from this path. `RobotSDK.connect` (verified by grep) contains no `argo-gateway`/`install_cluster`/`push`/`tls_config` references. |

### Key claim 3 — Frontend never writes `/etc/argo-gateway/env`

| | |
|---|---|
| verdict | **UPHOLD** |
| evidence | `grep -rln "argo-gateway/env\|/etc/argo-gateway\|/etc/argo-tls\|/etc/argo-zenoh" .` (excluding node_modules) returned **zero** matches. `grep -rln "PushGatewayEnv\|InstallCluster\|install_cluster\|PushArgoTls\|argo-zenoh-target\|argo-gateway-target" .` (excluding node_modules) also returned **zero** matches. The `FrontendRobotControlService` proto (verified at `code/ArgoGateway/src/argo-gateway-direct-proto/proto/gateway/v1/robot_control.proto:19-64`) defines 11 RPCs: `SubmitTask, CancelTask, GetTask, ListTasks, GetRobotStatus, GetLatestRobotState, RestartBot, SetSceneData, DebugQuery, Chat, PushZenohRouterConfig` — no env-writer or install-cluster RPC. |
| notes | One grep hit for `GATEWAY_TLS_CERT_PATH` etc. exists at `crates/robot-sdk/src/client.rs:607-609`, but that is a *test fixture comment* describing how to run the live mTLS test against a real `argo-gateway-server`. It is not production code that writes the env file. |

### Key claim 4 — Validator actively rejects TLS-shaped configs

| | |
|---|---|
| verdict | **NUANCE** (effect correct, wording slightly imprecise) |
| evidence | `apps/demo/src/components/manage-robot/zenohRouterConfig.ts:299-301`: `} else if (!endpoints.includes(ZENOH_ROUTER_LISTEN_ENDPOINT)) { errors.push("router.listen.endpoints.mustInclude0.0.0.0:57447"); }`. The check is "must include `tcp/0.0.0.0:57447`" — not "must not include TLS". The install_cluster.sh TLS shape (lines 80-92) emits `["tcp/127.0.0.1:57449", "tls/0.0.0.0:57448"]` and therefore trips this check as a *side effect*, not via a dedicated TLS-rejection branch. |
| notes | Test file `apps/demo/src/components/manage-robot/zenohRouterConfig.test.ts:316-321` confirms the rejection: setting `listen.endpoints = ["tcp/127.0.0.1:57447"]` produces the `"router.listen.endpoints.mustInclude0.0.0.0:57447"` error. The validator does NOT explicitly inspect a `transport.link.tls` block — that block would simply be ignored (not rejected) by the current rules. W1's phrasing "actively rejects TLS-shaped configs" is somewhat strong; a more precise statement is "the validator rejects any config whose `listen.endpoints` lacks `tcp/0.0.0.0:57447`, which incidentally excludes the install_cluster.sh TLS shape". The gap conclusion is unaffected. |

### Key claim 5 — `install_cluster.sh` has exactly 14 TLS-mode branches (D1-D14)

| | |
|---|---|
| verdict | **UPHOLD** |
| evidence | Read `/home/wangdang/work/ai-stack/code/ArgoDeploy/real/install_cluster.sh` end-to-end (190 lines). TLS-branching surfaces are exactly: (a) lines 78-102 zenohd-global.json5 — `D1, D2`; (b) lines 106-115 cert perms — `D3` (technically unconditional `if -f` blocks, but no-op in plaintext because cert files are not deployed); (c) lines 124-170 env file — `D4-D14`. All other lines (firewall 25-55, zenohd-local 70-76, dpkg installs, systemctl, argowatch, sentinel) are TLS-invariant. |
| notes | `env.sh` defines `ZENOH_GLOBAL_ENDPOINT_TLS=57448`, `ZENOH_GLOBAL_ENDPOINT_LOOPBACK=57449`, `ZENOH_GLOBAL_ENDPOINT_PLAINTEXT=57447`, `GATEWAY_TLS_ENABLE=1`, `GATEWAY_TLS_PORT=50053`, `GATEWAY_TLS_CERT_PATH=/etc/argo-tls/node.crt`, `GATEWAY_TLS_KEY_PATH=/etc/argo-tls/node.key` (lines 15-26) — these are *variable definitions*, not separate install-time deltas, so W1 correctly listed them in the Q1 Notes rather than as separate D-rows. `ZENOH_LOCAL_ENDPOINT` (line 11 of env.sh, `tcp/127.0.0.1:17448`) is identical in both branches (install_cluster.sh:73, 129, 156), so it is correctly NOT a delta. |

### Key claim 6 — 0 of 14 deltas mirrored in `robot-app-platform`

| | |
|---|---|
| verdict | **UPHOLD** |
| evidence | For D1/D2: only zenohd-global builder is `buildZenohRouterConfig` — verified plaintext-only (claim 1). For D3: no frontend code touches `/etc/argo-tls/` on the robot (claim 3 grep). For D4-D14: no frontend code writes `/etc/argo-gateway/env` (claim 3 grep) and no `PushGatewayEnv`/`InstallCluster`/`PushArgoTls` RPC exists in the proto. The only server-pushing surface (`PushZenohRouterConfig` proto at robot_control.proto:63; demo `networkConfig.ts:23-41`; skyline `networkConfigQuery.ts:23-45`) carries only `{request_id, session_id, config_json5, metadata}` — no TLS field. |
| notes | `metadata` is `map<string,string>` (robot_control_pb.ts:1319-1321). The only observed call site (demo `NetworkConfigDialog.tsx:354`, skyline `NetworkConfigDialog.tsx:444`) sets `{operator: "demoapp"}` / `{operator: "skyline"}`. No hidden TLS key. Even if a future call site set a TLS key, the gateway server side is out of scope per SPEC and W1 ESCALATE #7. |

### Key claim 7 (W1 ESCALATEs) — 7 judgment calls, all reasonable

| ESCALATE | verdict | notes |
|---|---|---|
| #1 "Click TLS" = "使用 TLS 加密" checkbox in AddRobotDialog | **UPHOLD** | Verified — this is the only TLS toggle in the demo UI. Skyline uses `:50053` suffix detection in `RealGatewayServerAddressField.tsx:26,87` (TLS_PORT_SUFFIX). Both are CLIENT-side. |
| #2 "ArgoGateway config" interpreted as `zenohd-global.json5` + `/etc/argo-gateway/env` | **UPHOLD** | Matches `install_cluster.sh`'s actual branch surface (lines 78-102 + 124-170). No other artifacts in `install_cluster.sh` branch on TLS. |
| #3 `argo_tls.rs` + AddRobotDialog classified as CLIENT-side mTLS plumbing | **UPHOLD** | Verified `argo_tls.rs` (demo 1425 lines, skyline 784 lines): all pub fns (`tls_log`, `load_root_cert`, `has_root_cert`, `apply_mtls`, `build_http_client`, `gateway_mtls_proxy`) operate on `~/.argo-tls/` CLIENT-side certs and reqwest builders. No server-config push. |
| #4 D3 is technically unconditional `if -f` blocks | **UPHOLD** | Verified at lines 106-115. W1 correctly notes the de facto TLS-only nature and ESCALATE'd the judgment call. |
| #5 `metadata` field free-form; only call site sets `{operator: "demoapp"}` | **UPHOLD** | Verified — `metadata: {operator: "demoapp"}` at demo NetworkConfigDialog.tsx:354; `metadata: {operator: "skyline"}` at skyline NetworkConfigDialog.tsx:444. No TLS key observed. |
| #6 Skyline "TLS fallback to plaintext" only changes transport URL, not payload | **UPHOLD** | Verified at `apps/skyline/.../networkConfig/NetworkConfigDialog.tsx:421-480`. `plaintextGatewayBaseUrl` (lines 424-432) just swaps `https:` → `http:` keeping the same host:port. `runPush(gatewayUrl)` (lines 434-468) re-uses the same `rawText` state — payload unchanged. W1 cited "421-479" (off by one line; `handleTlsFallback` ends at 480) — trivial imprecision, not a falsification. |
| #7 Gateway server-side handling of `PushZenohRouterConfig` out of scope | **UPHOLD** | SPEC §Inputs restricts read set to `install_cluster.sh` + `robot-app-platform`. Server-side derivation is a SPEC scope boundary, not a W1 dodge. |

### Per-delta Q3 verdicts

All 14 of W1's `NO` verdicts for D1-D14 are **UPHELD**. None is actually `YES` or `PARTIAL`:

| delta | W1 says | V1 verdict | re-interpreted? |
|---|---|---|---|
| D1 (zenohd-global listen endpoints) | NO | NO | No. Builder emits only `["tcp/0.0.0.0:57447"]` (zenohRouterConfig.ts:230). No `tls/0.0.0.0:57448` or `tcp/127.0.0.1:57449` is ever emitted. |
| D2 (transport.link.tls block) | NO | NO | No. `ZenohRouterConfig` type (lines 15-27) has no `transport` field; builder (lines 228-240) returns only `{mode, listen, connect, scouting}`. |
| D3 (cert file perms on /etc/argo-tls/*) | NO | NO | No. Frontend has no code path touching `/etc/argo-tls/` on the robot. `argo_tls.rs` reads `~/.argo-tls/` on the CLIENT machine (different concern). |
| D4 (ZENOH_ENDPOINT default) | NO | NO | No. Frontend never writes `/etc/argo-gateway/env`. |
| D5 (ZENOH_GLOBAL_ENDPOINT) | NO | NO | No. Same as D4. zenohd-global builder uses plaintext `tcp/0.0.0.0:57447`. |
| D6 (GATEWAY_GRPC_ENABLE=0) | NO | NO | No. Frontend never writes `/etc/argo-gateway/env`. |
| D7 (GATEWAY_TLS_ENABLE=1) | NO | NO | No. Frontend never writes `/etc/argo-gateway/env`. |
| D8 (GATEWAY_TLS_PORT=50053) | NO | NO | No. `AddRobotDialog.tsx:504` references 50053 (MANUAL_TLS_PORT) but only for CLIENT-side HTTPS URL, not the gateway's env var. |
| D9 (GATEWAY_TLS_CERT_PATH) | NO | NO | No. Frontend never writes `/etc/argo-gateway/env`. |
| D10 (GATEWAY_TLS_KEY_PATH) | NO | NO | No. Frontend never writes `/etc/argo-gateway/env`. |
| D11 (GATEWAY_TLS_ROOT_CA_PATH) | NO | NO | No. Frontend never writes `/etc/argo-gateway/env`. |
| D12 (GATEWAY_URL https vs http) | NO | NO | No. `AddRobotDialog.tsx:523,526` builds `https://<host>:50053` / `http://<host>:50051` as CLIENT-side URLs, not the gateway's own `GATEWAY_URL` env var. |
| D13 (GATEWAY_TLS_CA_CERT_PATH) | NO | NO | No. Frontend never writes `/etc/argo-gateway/env`. |
| D14 (GATEWAY_TLS_DOMAIN) | NO | NO | No. Frontend never writes `/etc/argo-gateway/env`. |

## 3. Missing deltas

**None found.** I read `install_cluster.sh` end-to-end (lines 1-190) and enumerated every site that branches on `GATEWAY_TLS_ENABLE`:
- Line 78-102: zenohd-global.json5 (D1, D2)
- Line 106-115: cert perms (D3)
- Line 124-170: env file (D4-D14)

Other sections (firewall 25-55, zenohd-local 70-76, dpkg installs 56-59 + 122, systemctl 117-119 + 172-173, argowatch 178-181, sentinel 184-189) are TLS-invariant. `ZENOH_LOCAL_ENDPOINT` is identical in both modes (`tcp/127.0.0.1:17448` per env.sh:11, used at install_cluster.sh:73, 129, 156). W1's 14-delta enumeration is complete.

## 4. Fabricated or mis-attributed citations

**None found.** Every file:line W1 cited was opened and verified:

| W1 citation | V1 verification |
|---|---|
| `install_cluster.sh:83 vs 98` (D1) | MATCH — line 83 is the TLS-mode `listen.endpoints` array; line 98 is the plaintext-mode `listen.endpoints` array |
| `install_cluster.sh:85-90` (D2) | MATCH — `transport: { link: { tls: {...}}}` block |
| `install_cluster.sh:106-115` (D3) | MATCH — three `if -f` blocks for cert perms |
| `install_cluster.sh:128 vs 155` (D4) | MATCH — `ZENOH_ENDPOINT` defaults differ (`57449` vs `7447`) |
| `install_cluster.sh:130 vs 157` (D5) | MATCH — `ZENOH_GLOBAL_ENDPOINT` references `LOOPBACK` vs `PLAINTEXT` |
| `install_cluster.sh:137, 142, 143, 144, 145, 146, 147 vs 168, 148, 149` (D6-D14) | MATCH — all 9 env-file deltas present at the cited lines |
| `apps/demo/.../zenohRouterConfig.ts:187-241` (builder) | MATCH — function signature and body |
| `apps/demo/.../zenohRouterConfig.ts:230` (listen endpoint) | MATCH — `listen: { endpoints: [ZENOH_ROUTER_LISTEN_ENDPOINT] }` |
| `apps/demo/.../zenohRouterConfig.ts:15-27` (type) | MATCH — type has `mode, listen, connect, scouting`; no `transport` |
| `apps/demo/.../zenohRouterConfig.ts:275-346` (validator) | MATCH — function bounds |
| `apps/demo/.../zenohRouterConfig.ts:299-301` (mustInclude check) | MATCH — exact error key `"router.listen.endpoints.mustInclude0.0.0.0:57447"` |
| `apps/demo/.../AddRobotDialog.tsx:418-495` (TLS checkbox) | MATCH — Field contains FieldLabel "使用 TLS 加密" + Checkbox |
| `apps/demo/.../AddRobotDialog.tsx:507-529` (buildManualSubmitPayload) | MATCH — produces `https://...:50053` and `http://...:50051` |
| `apps/demo/.../NetworkConfigDialog.tsx:280-286` (builder call) | MATCH — `useEffect` calls `buildZenohRouterConfig` + `serializeZenohRouterConfig` |
| `apps/demo/.../NetworkConfigDialog.tsx:354` (metadata) | MATCH — `metadata: { operator: "demoapp" }` |
| `apps/demo/.../queries/networkConfig.ts:23-41` (push fn) | MATCH — `pushZenohRouterConfig` creates request with 4 fields |
| `apps/demo/src-tauri/src/argo_tls.rs:17, 84, 89, 284, 349, 502` (CLIENT-side fns) | MATCH — all 6 pub fns at the cited lines |
| `apps/skyline/.../zenohRouterConfig.ts:187-241` (skyline twin) | MATCH — byte-identical to demo |
| `apps/skyline/.../NetworkConfigDialog.tsx:421-479` (TLS fallback) | APPROXIMATE — actual range is 421-480; off by one line. Not a falsification. |
| `apps/skyline/.../RealGatewayServerAddressField.tsx:26, 87, 124-142` | MATCH — `:50053` suffix detection + TLS hint UI at the cited lines |
| `packages/gateway-client/src/proto/gateway/v1/robot_control_pb.ts:1300-1322` (PushZenohRouterConfigRequest schema) | MATCH — fields `requestId, sessionId, configJson5, metadata` |
| `apps/demo/src/services/robot-endpoint.ts:27-55` (resolveEndpoint) | MATCH — derives `tlsStatus` from `robot.tlsPort + hasRootCert` |

## 5. Re-interpreted `NO`s that are actually `YES`/`PARTIAL`

**None found.** All 14 Q3 `NO` verdicts withstand re-reading. In particular I checked the highest-risk candidates:

- **D8 (GATEWAY_TLS_PORT=50053)** — `AddRobotDialog.tsx:504` defines `MANUAL_TLS_PORT = 50053` and `buildManualSubmitPayload` (line 523) emits `https://${host}:${MANUAL_TLS_PORT}`. Read superficially, this *looks* like a mirror of `GATEWAY_TLS_PORT=50053` from install_cluster.sh:143. But the W1 verdict correctly distinguishes: `MANUAL_TLS_PORT` is the CLIENT-side HTTPS port (used to construct the URL the *Tauri app* dials), not the gateway's own `GATEWAY_TLS_PORT` env var (which controls what port the *gateway server* listens on). They happen to be the same number because the gateway server's TLS port is the port the client connects to, but the frontend is NOT writing the env var — it's just using the well-known port number in a URL. W1's `NO` is correct.

- **D12 (GATEWAY_URL https vs http)** — Same pattern: `AddRobotDialog.tsx:523,526` builds `https://<host>:50053` and `http://<host>:50051` as CLIENT-side URLs. These are NOT the gateway's own `GATEWAY_URL` env var (which the gateway uses internally to know its own advertised URL). W1's `NO` is correct.

- **D1, D2 (zenohd-global TLS config)** — Could `metadata: {operator: "demoapp"}` or any other side-channel tell the gateway server to derive a TLS block? No: the server-side derivation is out of scope per SPEC, and even if it existed, the frontend would still need to emit a TLS signal somehow. The frontend emits no TLS signal anywhere. W1's `NO` is correct.

No `NO` flips to `YES` or `PARTIAL` under closer reading.

## 6. Final recommendation to orchestrator

**ACCEPT W1.** Every claim, citation, and `NO` verdict was adversarially re-checked against source; none overturned, none fabricated, none re-interpreted as `YES`. The single nuance (claim 4 wording: "actively rejects" vs "passively rejects via missing-plaintext-endpoint check") does not affect the GAP conclusion. W1's report is fit to drive a follow-up Develop worker for D1+D2 (the only frontend change needed under W1's Option A recommendation).
