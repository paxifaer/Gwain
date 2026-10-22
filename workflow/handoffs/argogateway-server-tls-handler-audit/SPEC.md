# SPEC — Audit gateway server `PushZenohRouterConfig` handler (E1 + Option A)

## Task type
Code investigation / risk audit. **No code edits.** Output is a written report only.

## Background
The prior impl task `handoffs/argogateway-tls-config-impl/` (W1 + V1 ACCEPT)
extended `robot-app-platform`'s `buildZenohRouterConfig` to emit a TLS-shaped
zenohd-global.json5 with a new top-level `transport.link.tls` block when
`enableTls: true`. The frontend change is in the working tree, not yet
deployed.

Two risks were ESCALATE'd forward and the user chose to de-risk before
proceeding:

- **E1 (highest risk)**: if the gateway server parses the received
  `config_json5` string with `#[serde(deny_unknown_fields)]`, the new
  `transport` block will cause TLS-mode pushes to fail server-side. The
  frontend change is then half-broken.
- **Option A verification**: the prior audit's recommendation was that the
  gateway server SHOULD derive the env-file TLS deltas (D4–D14 in the
  prior audit) from the `transport.link.tls` block — i.e. when the
  received config has the block, the server writes `GATEWAY_TLS_ENABLE=1`,
  `GATEWAY_TLS_PORT=50053`, `GATEWAY_TLS_CERT_PATH=...`,
  `GATEWAY_TLS_KEY_PATH=...`, `GATEWAY_TLS_ROOT_CA_PATH=...`,
  `GATEWAY_TLS_CA_CERT_PATH=...`, `GATEWAY_TLS_DOMAIN=$HOSTNAME`,
  `GATEWAY_GRPC_ENABLE=0`, `GATEWAY_URL=https://127.0.0.1:50053`,
  `ZENOH_ENDPOINT=tcp/127.0.0.1:57449`, `ZENOH_GLOBAL_ENDPOINT=tcp/127.0.0.1:57449`
  to `/etc/argo-gateway/env` and restarts `argogateway.target`. Whether
  the server already does this is unknown — the prior audit's read set
  did not include server-side code.

## Question to answer (the only question)
**What does the gateway server do when it receives a `PushZenohRouterConfig`
RPC, and does that behavior either (a) reject the new `transport` block
(E1 risk) or (b) translate the block into the env-file TLS deltas (Option A
already implemented)?**

Sub-questions:
- Q1. Where is the gateway server source code? (Path(s), language, build
  system. May be Rust / Go / something else. The deploy script
  `/home/wangdang/work/ai-stack/code/ArgoDeploy/real/install_cluster.sh`
  manages `/etc/argo-gateway/env` and `argogateway.target` — the source
  must exist somewhere.)
- Q2. What is the `PushZenohRouterConfig` handler? (file:line. The RPC is
  declared in `robot_control.proto` and implemented somewhere on the server
  side. Find the implementation.)
- Q3. What does the handler do with the received `config_json5` string?
  - Parse it? With what parser / struct? Does the struct use
    `#[serde(deny_unknown_fields)]`? Would a `transport` top-level field
    cause a parse failure?
  - Write it to disk? Where? (`/etc/argo-zenoh/zenohd-global.json5`?
    somewhere else?)
  - Derive env-file deltas from it? (Option A) — if yes, where's the
    translation code?
  - Restart any services? `argogateway.target`? `zenohd-global.service`?
  - Read the `metadata` field? Does it look at `tls_mode` (the key the
    frontend now sets) or any other key?
- Q4. Are there OTHER code paths that handle the zenohd-global config or
  the env file? (e.g. a separate systemd generator, a startup script that
  reads the config and emits env, a watcher that re-derives env on file
  change.)
- Q5. **Verdict on E1**: will the frontend's TLS-mode push succeed
  server-side? If yes, what's the exact code path that handles the new
  `transport` block? If no, what's the exact error the server will produce?
- Q6. **Verdict on Option A**: does the server already implement Option A
  (translate `transport.link.tls` block → env file deltas)? Or is Option A
  unimplemented (frontend change alone is insufficient to fully enable TLS
  mode on the gateway)?

## Inputs (read-only — search these locations)
The gateway server source location is unknown a priori. Search in this order:

1. `/home/wangdang/work/ai-stack/` — the docs/code monorepo (current cwd's
   parent). Look for a `crates/` or `apps/` directory with names like
   `argogateway`, `argo-gateway`, `gateway`, `gateway-server`.
2. `/home/wangdang/work/ai-stack-monitor/` — per user memory, "all service
   code (demo_app_service collector, argofleet) lives under
   /home/wangdang/work/ai-stack-monitor/". The argogateway service may be
   here.
3. `/home/wangdang/work/agent_muti/` — per user memory, `ArgoDDS/` lives
   here; may contain argogateway.
4. `/home/wangdang/work/zenoh-1.7.2` and `/home/wangdang/work/zenoh-1.9.0` —
   zenoh source trees (probably NOT where the argogateway server lives,
   but zenohd itself is here if relevant).

Also read for context:
- `/home/wangdang/work/ai-stack/code/ArgoDeploy/real/install_cluster.sh` —
  the deploy script. Tells you what the server's expected filesystem
  footprint looks like (env file, cert paths, systemd unit).
- `/home/wangdang/work/ai-stack/code/ArgoDeploy/real/env.sh` — variable
  defaults.
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/packages/gateway-client/src/proto/gateway/v1/robot_control_pb.ts`
  — the proto schema. Tells you the RPC signature.
- Prior audit: `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/argogateway-tls-config-audit/W1-REPORT.md`
- Prior impl REPORT: `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/argogateway-tls-config-impl/REPORT.md`

## Write-set (the ONLY file W1 may create/modify)
`/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/argogateway-server-tls-handler-audit/W1-REPORT.md`

No other file writes. No code edits. No `git`. No network. No tests run
(you may compile-check a single Rust file with `cargo check --offline` if
needed to verify a struct's serde attrs, but do NOT run full builds).

## Output contract — W1-REPORT.md structure
1. **Summary** — 3–5 sentences. Two one-line verdicts: `E1: <SAFE | UNSAFE | UNKNOWN>`
   and `Option A: <ALREADY-IMPLEMENTED | PARTIAL | NOT-IMPLEMENTED | UNKNOWN>`.
2. **Method** — exact paths searched, exact grep patterns used, exact files
   read. V1 must be able to reproduce by following these steps.
3. **Q1 — Server source location** — path(s), language, build system, how
   you found it.
4. **Q2 — `PushZenohRouterConfig` handler** — `file:line` of the
   implementation, function signature, what it does at a high level.
5. **Q3 — Handler behavior on received config** — table with rows:
   - Parser used (serde_json? serde_json5? custom? what struct?)
   - Struct's serde attributes (`deny_unknown_fields`? `default`?)
   - Would `transport` top-level field be accepted or rejected? Evidence
     (actual code snippet, ≤5 lines).
   - Where (if anywhere) is the config written to disk?
   - Where (if anywhere) is env file derived from config?
   - Where (if anywhere) is a service restarted?
   - Where (if anywhere) is `metadata` field read?
6. **Q4 — Other config-handling paths** — bullet list of any other code
   that handles zenohd-global config or `/etc/argo-gateway/env`. May be
   empty if none found.
7. **Q5 — E1 verdict** — `SAFE` / `UNSAFE` / `UNKNOWN` with evidence.
   - If `UNSAFE`: the exact error message the server will produce, the
     exact `file:line` that rejects, the exact field that triggers.
   - If `SAFE`: the exact `file:line` that accepts the new field, why
     (e.g. no `deny_unknown_fields`, or `transport` is already a known
     field).
   - If `UNKNOWN`: what's blocking the determination (e.g. server source
     not found, or parser is dynamic).
8. **Q6 — Option A verdict** — `ALREADY-IMPLEMENTED` / `PARTIAL` /
   `NOT-IMPLEMENTED` / `UNKNOWN` with evidence.
   - If `ALREADY-IMPLEMENTED`: cite the `file:line` of the translation
     code. Show it writes all 11 env-file deltas (D4–D14).
   - If `PARTIAL`: which deltas are translated, which are missing.
   - If `NOT-IMPLEMENTED`: confirm the handler just writes config_json5
     to disk (or similar) without deriving env. Cite evidence.
   - If `UNKNOWN`: what's blocking.
9. **Recommendations** — based on Q5 + Q6:
   - If E1 is `UNSAFE`: what server-side change is needed to accept the
     `transport` block? (e.g. remove `deny_unknown_fields`, or add
     `transport` field to the struct.)
   - If Option A is `NOT-IMPLEMENTED`: what server-side change is needed
     to translate the block into env deltas? Describe in prose, do not
     implement.
   - If Option A is `PARTIAL`: which deltas need adding.
   - If E1 is `UNKNOWN` or server source not found: what's the next step
     (ask user for the path? search elsewhere?).
10. **ESCALATEs** — judgment calls W1 made alone. One line each. Specifically:
    - whether the server source location is correct (may be multiple
      argogateway-related crates/services; user must confirm which one is
      the live production server)
    - any ambiguous code path that could be read two ways
    - any toolchain issue preventing verification (e.g. server source
      requires a specific Rust toolchain that's not installed)

The report is the entire deliverable. W1's final message to the orchestrator
must be ≤200 words and point to the report file.

## Acceptance criteria (how V1 will judge W1)
V1 will adversarially check:
- For each `file:line` W1 cites, the line exists and the snippet matches.
- The server source location is correct (V1 re-runs the search to confirm).
- The E1 verdict is supported by actual code (V1 reads the parser struct's
  serde attrs directly).
- The Option A verdict is supported by actual code (V1 looks for env-write
  calls near the handler).
- V1 will look for OTHER config-handling paths W1 might have missed
  (systemd generators, watchers, postinst scripts).

Any fabricated `file:line`, any wrong verdict that the actual code
contradicts — V1 returns FAIL and the orchestrator re-dispatches W1.

## Risk classification
- **Risk: low.** Investigation only; no code edits; no algorithms.
- **High-Risk Reasoning Gate:** not triggered.
- **Cross-boundary integration test code:** none written. Traceability
  contract not triggered.
- Convention: standard `SPEC.md` + `PROMPT-W*` (no task-state layout).

## Dispatch plan
- W1: audit worker (general-purpose Agent, foreground).
- V1: verifier worker (general-purpose Agent, adversarial mandate), dispatched after W1.
- Recursion floor: 2 free agents (W1, V1) + 1 judgment (orchestrator).
