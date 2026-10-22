# SPEC-01 — Implement TLS-mode zenoh-router config generation in demo + skyline

## Task type
Code implementation. **Edits allowed within the declared write-set.** Builds and
tests must be run by the worker to verify.

## Background
Prior audit task `handoffs/argogateway-tls-config-audit/` (W1-REPORT.md, V1
CONFIRM, orchestrator ACCEPT) established:
- `install_cluster.sh` has 14 TLS-mode deltas (D1–D14).
- `robot-app-platform` mirrors **0** of 14 today; the frontend's "使用 TLS 加密"
  checkbox only flips CLIENT-side HTTP URL, not SERVER config.
- The minimal frontend fix is **D1 + D2**: extend `buildZenohRouterConfig()` to
  emit a TLS-shaped zenohd-global.json5 when TLS is on, relax the validator to
  accept it, and add a TLS toggle in `NetworkConfigDialog`.

The user accepted the audit and directed: implement D1+D2 in **both** `demo`
and `skyline` apps. Server-side env-file derivation (Option A) and cert-perms
(D3) are **out of scope for this task** — they will be a separate task if the
user commissions one.

## Scope
- **In scope**: frontend D1 + D2 in `apps/demo` and `apps/skyline`.
- **Out of scope**: server-side `PushZenohRouterConfig` handler changes,
  `/etc/argo-gateway/env` writes, cert file perms, systemd unit changes, any
  Rust crate changes (incl. `argo_tls.rs`), gateway-client proto schema changes
  (the existing `metadata: map<string,string>` field is sufficient).
- **No git operations**: no `git add`, no `git commit`, no `git push`, no branch
  creation. Leave changes in working tree.

## What changes (4 files, exactly)

### File 1 — `apps/demo/src/components/manage-robot/zenohRouterConfig.ts`
- Extend the `ZenohRouterConfig` type (lines 15–27 per audit) to include an
  optional `transport` field with shape `{ link: { tls: { listen_certificate:
  string; listen_private_key: string; root_ca_certificate: string;
  enable_mtls: boolean } } }`. Optional so plaintext configs continue to
  serialize without it.
- Add new constants alongside `ZENOH_ROUTER_PORT` (line 8):
  - `ZENOH_ROUTER_TLS_PORT = 57448`
  - `ZENOH_ROUTER_LOOPBACK_ENDPOINT = "tcp/127.0.0.1:57449"`
  - `ZENOH_ROUTER_TLS_CERT_PATH = "/etc/argo-tls/node.crt"`
  - `ZENOH_ROUTER_TLS_KEY_PATH = "/etc/argo-tls/node.key"`
  - `ZENOH_ROUTER_TLS_ROOT_CA_PATH = "/etc/argo-tls/root.crt"`
- Modify `buildZenohRouterConfig()` (lines 187–241 per audit) to accept an
  options object `{ enableTls?: boolean }` (default `false` — preserves
  existing behavior at all existing call sites that pass no argument).
  - When `enableTls === true`: emit
    `listen.endpoints: ["tcp/127.0.0.1:57449", "tls/0.0.0.0:57448"]` and
    include the `transport.link.tls` block with `enable_mtls: false` and the
    cert paths above. The shape MUST match `install_cluster.sh` lines 80–91
    exactly (field names, nesting, values).
  - When `enableTls === false` or undefined: emit the current plaintext shape
    `listen.endpoints: ["tcp/0.0.0.0:57447"]` with no `transport` block.
    Identical to today's output.
- Modify `validateZenohRouterConfig()` (lines 275–346 per audit):
  - The current `router.listen.endpoints.mustInclude0.0.0.0:57447` check at
    lines 299–301 must NOT fire when the config has a `transport.link.tls`
    block (i.e., is TLS-shaped).
  - Add a parallel check for TLS-shaped configs: must include
    `tls/0.0.0.0:57448` in `listen.endpoints`, must have
    `transport.link.tls.listen_certificate`, `listen_private_key`,
    `root_ca_certificate`, and `enable_mtls === false`. If any missing, push
    an error like `router.listen.endpoints.mustIncludeTls57448` or
    `router.transport.link.tls.missingFields`.
  - Keep all other existing validator checks (scouting, mode, etc.) unchanged.

### File 2 — `apps/demo/src/components/manage-robot/NetworkConfigDialog.tsx`
- Add a TLS toggle UI element (checkbox or switch — match existing dialog's
  visual idiom). Label: "启用 TLS 加密" (or matching English if dialog is
  English). Default **unchecked** (OFF).
- Wire the toggle state into the `buildZenohRouterConfig({ enableTls })` call
  at lines 280–286 per audit.
- Pass the toggle state into the push mutation's `metadata` field at line 354
  per audit. Current metadata is `{operator: "demoapp"}`. Extend to
  `{operator: "demoapp", tls_mode: enableTls ? "tls" : "plaintext"}`.
  - **Metadata key name**: use `tls_mode` (string `"tls"` | `"plaintext"`).
    This is a worker judgment call — record as an ESCALATE in the final
    message in case the user wants a different key name.
- If the dialog already has a "raw JSON edit" mode, the toggle should also
  reflect/be-derivable from the raw JSON's `transport.link.tls` presence, so
  the toggle and raw text stay in sync. Use the simpler approach if both are
  complex: when user toggles, regenerate raw text; when user edits raw text,
  detect `transport.link.tls` and update toggle. If this is too invasive,
  just have the toggle regenerate raw text on change and skip the reverse
  sync — record an ESCALATE.

### File 3 — `apps/skyline/src/features/projects/workspace/networkConfig/zenohRouterConfig.ts`
- Apply the exact same changes as File 1. The audit said the demo and
  skyline versions of this file are byte-identical except path. If during
  implementation the worker finds they are NOT identical, ESCALATE — the
  parity assumption from the audit may be wrong.

### File 4 — `apps/skyline/src/features/projects/workspace/networkConfig/NetworkConfigDialog.tsx`
- Apply the equivalent changes as File 2. Skyline's dialog may have a
  different structure (it has a "TLS fallback to plaintext" branch at lines
  421–479 per audit) — that branch is CLIENT-side transport fallback, NOT
  the server config toggle. Do not conflate. The new TLS toggle is a separate
  UI control that controls server config generation.

## Constraints

### Write-set (the ONLY files W1 may create/modify)
1. `apps/demo/src/components/manage-robot/zenohRouterConfig.ts`
2. `apps/demo/src/components/manage-robot/NetworkConfigDialog.tsx`
3. `apps/skyline/src/features/projects/workspace/networkConfig/zenohRouterConfig.ts`
4. `apps/skyline/src/features/projects/workspace/networkConfig/NetworkConfigDialog.tsx`

Plus any new files required for tests of the new logic — but only inside the
same directories. No new files elsewhere. No changes to `packages/`, `crates/`,
`apps/demo/src-tauri/`, `apps/skyline/src-tauri/`, or any `*.proto`.

### No git operations
- No `git add`, no `git commit`, no `git push`, no `git reset`, no branch.
- HEAD-guard before any git touchpoint (none expected): `git log --oneline -1 && git status --short`.
- Leave changes in working tree for user review.

### Network installs through proxy
- The user is in mainland China. Any `bun install`, `cargo build` that pulls
  crates, `npm install`, `curl`, `pip install`, `uv` — prefix with proxy
  `http://127.0.0.1:7897`. Specifically:
  - `cargo` — set `HTTPS_PROXY=http://127.0.0.1:7897 HTTP_PROXY=http://127.0.0.1:7897`
  - `bun` — set `BUN_CONFIG_HTTPS_PROXY=http://127.0.0.1:7897`
  - `npm` — `--proxy=http://127.0.0.1:7897 --https-proxy=http://127.0.0.1:7897`
- Avoid installs if possible — only run if `node_modules` / `Cargo.lock` would
  otherwise block build. The repo is already bootstrapped per audit (Cargo.lock
  + bun.lock present, 8月 18 timestamps).

### Integration Traceability Contract (Q4 — cross-boundary integration code)
This task writes code that participates in a cross-boundary integration
(frontend UI → gRPC `PushZenohRouterConfig` → server-side config write). The
new TLS toggle wiring MUST satisfy the Integration Traceability Contract at
`/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/README.md`.

Before writing any logging call, W1 MUST load:
- `agentflow/observability/README.md`
- `agentflow/observability/context.md`
- `agentflow/observability/events.md`
- `agentflow/observability/propagation.md`

The TLS toggle code MUST emit:
- A **STATE** event when the toggle state changes (user clicks ON or OFF) —
  includes `tls_mode: "tls" | "plaintext"` and the resulting config shape
  selected. This is a decision point that future cross-boundary debugging
  will need.
- A **STATE** event when `buildZenohRouterConfig` is called with
  `enableTls: true` (so the resulting push can be correlated to a TLS-mode
  config decision).
- A **FAIL** event when `validateZenohRouterConfig` rejects a TLS-shaped
  config (so a failed push is traceable to validator rejection, not server
  rejection).
- **correlation_id** propagation: the existing push mutation likely already
  propagates `correlation_id` via gRPC metadata. The new TLS-toggle STATE
  events must use the same `correlation_id` so they chain with the push
  result. If the existing code does not have `correlation_id` infrastructure,
  ESCALATE — do not invent a new one.

If the existing `zenohRouterConfig.ts` and `NetworkConfigDialog.tsx` have
**no logging infrastructure at all**, ESCALATE — the contract requires
logging, but adding new logging infrastructure is beyond the declared
write-set and the user must decide.

### Backward compatibility
- Existing robots with plaintext config MUST continue to work unchanged.
- The TLS toggle default is OFF — no behavior change unless user explicitly
  enables TLS.
- The `metadata` field's existing `{operator: "demoapp"}` key MUST be
  preserved; only add `tls_mode` alongside it.

## Verification (W1 MUST run these)
1. `cd /home/wangdang/work/ai-stack/code/frontend/robot-app-platform && cargo build` — must succeed (with proxy env vars if any fetch needed).
2. `cd /home/wangdang/work/ai-stack/code/frontend/robot-app-platform && bun run build` (or whatever the workspace's build command is — check `package.json` `scripts`) — must succeed for both `apps/demo` and `apps/skyline`.
3. `cd /home/wangdang/work/ai-stack/code/frontend/robot-app-platform && bun run check` (biome / tsc) — must pass with zero new errors. Pre-existing errors are not W1's concern but must be listed in the final message.
4. Run any existing tests that touch `zenohRouterConfig.ts` or `NetworkConfigDialog.tsx`:
   - `cd /home/wangdang/work/ai-stack/code/frontend/robot-app-platform && bun test zenohRouterConfig` (or whatever the test invocation is — check `package.json`).
   - If no tests exist, ESCALATE — do not write new tests beyond the declared write-set.
5. **Manual sanity check**: open `zenohRouterConfig.ts` after the change, call `buildZenohRouterConfig({ enableTls: true })` and `buildZenohRouterConfig({ enableTls: false })` in a scratch computation (e.g. via `bun eval` or a temporary `console.log` that is removed before commit), and confirm the two outputs differ exactly as specified in §"What changes" File 1.

## Output contract — W1 final message (≤300 words)
W1's final message must contain:
1. **Files changed** — list each of the 4 files with line ranges modified.
2. **Build / check / test results** — per-step PASS/FAIL with actual command output snippets (≤5 lines each).
3. **TLS shape verification** — the exact JSON5 output of
   `buildZenohRouterConfig({ enableTls: true })` and `... false` (the actual
   output, not the spec).
4. **Metadata key chosen** — `tls_mode` (or whatever W1 used).
5. **Traceability events emitted** — list each new event (STATE/FAIL) with its
   `event_kind`, field set, and where it's emitted (file:line).
6. **ESCALATEs** — any judgment call W1 made alone. One line each. Specifically:
   - metadata key name choice
   - whether logging infrastructure existed or had to be added
   - any divergence between demo and skyline `zenohRouterConfig.ts` (audit said byte-identical; verify)
   - any test the worker couldn't run (missing toolchain, missing deps, etc.)
   - any back-compat risk the worker noticed but couldn't fully verify
7. **Elapsed time**.

## Risk classification
- **Risk: low.** Post-audit, mechanical implementation. No core algorithm
  changes. No derivations. Failures will be visible (config rejected, TLS
  handshake fails, build fails). Multi-worker pipeline but bounded.
- **High-Risk Reasoning Gate**: not triggered.
- **Cross-boundary integration test code: YES** — Integration Traceability
  Contract applies per above.
- Convention: standard `SPEC-*.md` + `PROMPT-W*`.

## Dispatch plan
- **W1**: implementation worker (general-purpose Agent, foreground). Touches
  all 4 files, runs builds + tests, writes W1-REPORT.md.
- **V1**: verifier worker (general-purpose Agent, adversarial mandate),
  dispatched after W1 returns. V1 will:
  - Re-open each modified file and check the changes match the SPEC.
  - Run `buildZenohRouterConfig({ enableTls: true })` and `... false`
    themselves and confirm output matches `install_cluster.sh:80–91`.
  - Confirm toggle defaults OFF.
  - Confirm demo and skyline have parity (same TLS shape, same validator
    relaxation, same metadata key).
  - Run the 8 traceability checks from `agentflow/observability/evidence.md`
    adversarially.
  - Run the build/check commands and confirm W1's PASS claims are not fake.
- **Orchestrator judgment**: ACCEPT / RE-DISPATCH W1 / ESCALATE.
