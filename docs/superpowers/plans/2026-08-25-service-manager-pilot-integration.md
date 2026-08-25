# Service Manager Real-Device Pilot Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exercise and prove one real `Restart` path from the Skyline Tauri UI through ArgoGateway and the lifecycle backend to `gawain-canary.service` on SP000065, producing a sealed Gawain evidence bundle.

**Architecture:** The existing Skyline mTLS transport remains the Tauri hop: unary requests use `gateway_mtls_proxy`, and state streaming uses `gateway_mtls_proxy_stream`. A W3C operation context is carried through the existing protocol into Gateway, Backend, systemd state, and the returning UI event. Gawain owns the canary fixture, permit-bound deployment/cleanup, independent systemd oracle, evidence collection, test matrix, and deterministic validation; application repositories never gain task-dispatch behavior.

**Tech Stack:** Python 3.11+, Rust/Tokio/Tonic, TypeScript/React/Tauri 2, ConnectRPC/Protobuf, Zenoh, user-systemd, SSH/rsync, JSONL/SHA-256

**Depends on:** `docs/superpowers/plans/2026-08-24-verification-evidence-p0.md` completed and green

**Design source:** `docs/superpowers/specs/2026-08-24-gawain-service-manager-pilot-design.md`

---

## Repository isolation and file map

The current shared frontend checkout contains unresolved merge conflicts and extensive unrelated changes; the ArgoGateway checkout also has unrelated local changes. Do not edit either shared checkout. At execution time create isolated worktrees from these committed baselines, then create dedicated branches:

| Repository | Baseline | New branch |
|---|---|---|
| Gawain | current `feat/verification-evidence-p0` after core completion | continue same feature branch |
| frontend/robot-app-platform | `7b46b093` | `feat/gawain-canary-verification-trace` |
| ArgoGateway | `3d512c9` | `feat/gawain-lifecycle-operation-trace` |
| ArgoWatch | current `origin/main` containing `84da96a8` | `feat/gawain-canary-lifecycle-trace` |

Never resolve or stage the conflicts in the shared frontend checkout as part of this work.

Key ownership:

| Repository/file | Responsibility |
|---|---|
| ArgoGateway `robot_control.proto` + generated bindings | Operation/trace context wire fields |
| ArgoGateway `robot_control.rs` | Validate context, forward it, emit Gateway span |
| ArgoWatch lifecycle envelope/state/reconcile | Preserve operation ID through actuation and terminal state |
| ArgoWatch deployed registry | Expose `gawain-canary` through user-systemd provider |
| frontend gateway client | Generate context, attach Connect headers, parse correlated state |
| Skyline Tauri `argo_tls.rs` | Emit safe Tauri client/server evidence for existing mTLS proxy |
| Skyline lifecycle panel | Keep Restart pending until the matching terminal state arrives |
| Gawain `fixtures/service-manager/` | Deterministic canary script and unit |
| Gawain `gawain_verification/pilot/` | Permit-bound deploy, fault setup, UI driver coordination, oracle and bundle collection |

### Task 1: Add an additive lifecycle operation context to the protocol and Gateway

**Files (ArgoGateway worktree):**
- Modify: `src/argo-gateway-direct-proto/proto/gateway/v1/robot_control.proto`
- Modify: `src/argo-gateway-server/src/robot_control.rs`
- Modify: `generated/rust/gateway-rust-proto/src/generated/gateway.v1.rs`
- Test: `src/argo-gateway-server/src/robot_control.rs` test module

- [ ] **Step 1: Write failing Gateway tests for preserved context**

Add a test around lifecycle payload construction with this exact public helper:

```rust
#[test]
fn lifecycle_payload_preserves_verification_context() {
    let req = LifecycleExecuteRequest {
        request_id: "req-1".into(),
        fleet_id: "sudoai".into(),
        bot_name: "SP000065".into(),
        op: "Restart".into(),
        service_id: "gawain-canary".into(),
        timeout_ms: 30_000,
        operation_id: "0123456789abcdef0123456789abcdef".into(),
        trace_id: "0123456789abcdef0123456789abcdef".into(),
        parent_span_id: "0123456789abcdef".into(),
        run_id: "run-pilot-001".into(),
        candidate_id: "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa".into(),
        contract_id: "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb".into(),
        test_case_id: "P-01".into(),
        attempt_id: "attempt-1".into(),
    };
    let payload = lifecycle_payload(&req).unwrap();
    assert_eq!(payload["operation_id"], req.operation_id);
    assert_eq!(payload["trace_id"], req.trace_id);
    assert_eq!(payload["run_id"], req.run_id);
}
```

Also reject non-32-hex trace/operation IDs, zero IDs, non-16-hex parent span IDs, and empty run/candidate/contract/test/attempt identity.

- [ ] **Step 2: Run the focused Gateway test and confirm RED**

Run: `cargo test -p argo-gateway-server lifecycle_payload -- --nocapture`

Expected: compile fails because the new proto fields and helper do not exist.

- [ ] **Step 3: Extend the protobuf additively**

Append fields 7–14 to `LifecycleExecuteRequest`; do not renumber existing fields:

```proto
string operation_id = 7;    // W3C trace-id form; stable business operation id
string trace_id = 8;        // equal to operation_id for this v1 operation
string parent_span_id = 9;  // renderer/Tauri parent span
string run_id = 10;
string candidate_id = 11;
string contract_id = 12;
string test_case_id = 13;
string attempt_id = 14;
```

Add `operation_id = 5` to `LifecycleExecuteResponse` so the caller can prove which provisional ACK it received.

- [ ] **Step 4: Regenerate the persisted Rust binding and compile the build-time binding**

Run `cargo build -p argo-gateway-rust-proto` so its existing build script regenerates `generated/rust/gateway-rust-proto/src/generated/gateway.v1.rs`. Then run `cargo build -p argo-gateway-direct-proto`; its binding exists only in Cargo `OUT_DIR` and is not a tracked file. Never hand-edit generated field tags. Compile the Gateway tests against the direct-proto crate and inspect the persisted binding to verify both consumers expose the same new fields.

- [ ] **Step 5: Implement Gateway validation, forwarding, and span events**

Extract a pure `lifecycle_payload(&LifecycleExecuteRequest) -> Result<Value, Status>`. Validate exact lowercase hex widths and identity prefixes, then publish:

```rust
json!({
    "op": req.op,
    "service_id": req.service_id,
    "operation_id": req.operation_id,
    "trace_id": req.trace_id,
    "parent_span_id": req.parent_span_id,
    "run_id": req.run_id,
    "candidate_id": req.candidate_id,
    "contract_id": req.contract_id,
    "test_case_id": req.test_case_id,
    "attempt_id": req.attempt_id,
})
```

Emit structured Gateway `SPAN_START` before publish and `SPAN_END` after publish using a fresh Gateway span ID and the incoming parent span. Never log request bodies, credentials, headers, certificates, or tokens.

- [ ] **Step 6: Run Gateway checks and commit**

Run:

```bash
cargo fmt --all -- --check
cargo test -p argo-gateway-server lifecycle_payload -- --nocapture
cargo check -p argo-gateway-server
git diff --check
```

Expected: all commands exit zero.

Commit: `git commit -am "feat(lifecycle): preserve verification operation context"` plus explicitly add regenerated files.

### Task 2: Bind Backend actuation and terminal state to the operation

**Files (ArgoWatch worktree):**
- Modify: `demo_app_service/crates/demo-app-lifecycle/src/envelope.rs`
- Modify: `demo_app_service/crates/demo-app-lifecycle/src/main.rs`
- Modify: `demo_app_service/crates/demo-app-lifecycle/src/runtime/state.rs`
- Modify: `demo_app_service/crates/demo-app-lifecycle/src/runtime/reconcile.rs`
- Modify: `demo_app_service/crates/demo-app-lifecycle/src/handlers.rs`
- Modify: `demo_app_service/crates/demo-app-lifecycle/src/runtime/snapshot.rs`
- Modify: `demo_app_service/crates/demo-app-backend/debian/registry-robot.yaml`
- Test: `demo_app_service/crates/demo-app-lifecycle/tests/operation_trace.rs`

- [ ] **Step 1: Write a failing end-to-end runtime test**

Create an in-process fake provider test that submits a raw Gateway payload for `Restart`, runs convergence, then inspects the state payload. Assert:

```rust
assert_eq!(state["operation_id"], "0123456789abcdef0123456789abcdef");
assert_eq!(state["trace_id"], state["operation_id"]);
assert_eq!(state["run_id"], "run-pilot-001");
assert_eq!(state["test_case_id"], "P-01");
assert_eq!(state["last_op"]["kind"], "Restart");
assert_eq!(state["phase"], "Running");
assert_eq!(state["converged"], true);
```

Add failure coverage proving a failed provider preserves the same operation context with `phase=Failed` and `converged=false`.

- [ ] **Step 2: Run the focused backend test and confirm RED**

Run from `demo_app_service`: `cargo test -p demo-app-lifecycle --test operation_trace -- --nocapture`

Expected: the state model has no operation context.

- [ ] **Step 3: Preserve Gateway context when wrapping raw JSON**

Add an optional `OperationContext` to `Envelope` rather than overloading the UUID header:

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OperationContext {
    pub operation_id: String,
    pub trace_id: String,
    pub parent_span_id: String,
    pub run_id: String,
    pub candidate_id: String,
    pub contract_id: String,
    pub test_case_id: String,
    pub attempt_id: String,
}
```

`Envelope::new_request_with_context()` extracts the eight fields from the raw Gateway payload. Missing context remains accepted for non-Gawain production calls but is explicitly logged as unverified and cannot produce Gawain evidence.

- [ ] **Step 4: Carry context through reconciliation and state publication**

Add `operation: Option<OperationContext>` to `ConvergeRequest` and `LastOp`. Copy it at desired-state write time, preserve it on provider success/failure, and expose it in `build_state_payload()` and snapshots under the exact top-level keys from the protocol. Do not use wall-clock proximity to associate a periodic state with a command.

For an immediate rejection that has no registered service state, such as N-01's missing service ID, publish one explicit terminal failure payload on `lifecycle/state/{requested_service_id}`. It carries the same operation context, `phase=Failed`, `converged=false`, and the structured error code/message. This closes the UI result path without inventing a second protocol event; periodic state remains the terminal source for registered services.

- [ ] **Step 5: Register the canary service without changing existing services**

Under the existing `robot-independent` group in `registry-robot.yaml`, add:

```yaml
  - id: gawain-canary
    display_name: "Gawain deterministic verification canary"
    group: robot-independent
    expose: [lifecycle, status]
    provider:
      instance: robot-systemd-user
      selector: { unit: gawain-canary.service }
```

No existing unit, selector, port, group, or ordering entry may change.

- [ ] **Step 6: Emit Backend causal spans**

Use the incoming trace ID and a new backend span ID for dispatch, provider control, and terminal publication. Emit JSON-compatible fields required by `gawain.trace-event.v1`; preserve the full cause chain but never serialize credentials or arbitrary request bodies.

- [ ] **Step 7: Run Backend checks and commit**

Run from `demo_app_service`:

```bash
cargo fmt --all -- --check
cargo test -p demo-app-lifecycle --test operation_trace -- --nocapture
cargo test -p demo-app-lifecycle
cargo check -p demo-app-backend
```

Expected: all commands exit zero.

Commit: `git commit -am "feat(lifecycle): correlate terminal state with operation"` and add the new test.

### Task 3: Correlate the existing Skyline Tauri mTLS hop and UI terminal state

**Files (clean frontend worktree):**
- Modify: `package.json`
- Modify: `bun.lock`
- Create: `scripts/generate-gateway-proto.sh`
- Modify: `packages/gateway-client/src/lib/observability.ts`
- Modify: `packages/gateway-client/src/lib/transport.ts`
- Modify: `packages/gateway-client/src/lib/demoRobotControl.ts`
- Modify: `packages/gateway-client/src/lib/demoLifecycleState.ts`
- Modify: `packages/gateway-client/src/proto/gateway/v1/robot_control_pb.ts` through generation tooling
- Modify: `apps/skyline/src/generated/proto/gateway/v1/robot_control_pb.ts` through the same generation tooling
- Test: `packages/gateway-client/src/lib/demoRobotControl.test.ts`
- Test: `packages/gateway-client/src/lib/demoLifecycleState.test.ts`
- Modify: `apps/skyline/src-tauri/src/argo_tls.rs`
- Modify: `apps/skyline/src/features/projects/workspace/lifecycle/useRobotLifecyclePanel.ts`
- Test: `apps/skyline/src/features/projects/workspace/lifecycle/useRobotLifecyclePanel.test.tsx`

- [ ] **Step 1: Write failing gateway-client correlation tests**

Inject a deterministic context generator and assert the request contains all protocol fields plus a valid `traceparent` header:

```ts
expect(captured.request.operationId).toBe(TRACE_ID);
expect(captured.request.traceId).toBe(TRACE_ID);
expect(captured.options.headers.get("traceparent")).toBe(
  `00-${TRACE_ID}-${RENDERER_SPAN_ID}-01`,
);
expect(result.operationId).toBe(TRACE_ID);
```

Add state parser tests for operation/run/candidate/contract/test/attempt IDs and reject a state whose operation ID is not 32 lowercase hex.

- [ ] **Step 2: Write a failing UI test for provisional ACK**

Mock ACK immediately and state later. After ACK, assert the Restart control remains busy and the panel does not synthesize a new `Running` state. After a matching `operationId` state with `phase=Running` and `converged=true`, assert busy clears. A stale state from another operation must not clear it; Failed clears busy into visible failure.

- [ ] **Step 3: Run focused frontend tests and confirm RED**

Run:

```bash
bun run --filter @robot/gateway-client test -- demoRobotControl demoLifecycleState
bunx vitest --run apps/skyline/src/features/projects/workspace/lifecycle/useRobotLifecyclePanel.test.tsx
```

Expected: new assertions fail because operation context and terminal matching are absent.

- [ ] **Step 4: Add one pinned TypeScript protobuf generation path**

Add exact root dev dependency `@bufbuild/protoc-gen-es@2.11.0`, matching the version recorded in both existing generated headers, and add this root script:

```json
"generate:gateway-proto": "bash scripts/generate-gateway-proto.sh"
```

Create `scripts/generate-gateway-proto.sh`. It accepts the ArgoGateway direct-proto root as its single argument, verifies `gateway/v1/robot_control.proto` and the local `node_modules/.bin/protoc-gen-es`, generates into a `mktemp -d` directory with:

```bash
protoc \
  -I "$proto_root" \
  --plugin=protoc-gen-es="$repo_root/node_modules/.bin/protoc-gen-es" \
  --es_out="$generated_root" \
  --es_opt=target=ts,import_extension=.js \
  gateway/v1/robot_control.proto
```

The script then copies that one generated `robot_control_pb.ts` byte-for-byte to both `packages/gateway-client/src/proto/gateway/v1/robot_control_pb.ts` and `apps/skyline/src/generated/proto/gateway/v1/robot_control_pb.ts`, and removes its temporary directory through a trap. Run it against the isolated ArgoGateway worktree's `src/argo-gateway-direct-proto/proto` directory. Assert the two destinations compare equal and both headers name `protoc-gen-es v2.11.0`. Do not hand-edit either descriptor.

- [ ] **Step 5: Generate context once in the renderer and attach it to Connect**

Add:

```ts
export type LifecycleVerificationContext = {
  runId: string;
  candidateId: string;
  contractId: string;
  testCaseId: string;
  attemptId: string;
};

export type LifecycleDispatch = {
  operationId: string;
  response: LifecycleExecuteResponse;
};
```

`runLifecycleExecute()` generates one nonzero 32-hex trace ID and one 16-hex renderer span, passes the context fields in the proto request, and supplies `traceparent` as Connect call headers. In normal non-Gawain usage it generates operation/trace IDs but leaves verification-only IDs empty; such runs remain functional but are not eligible evidence.

- [ ] **Step 6: Instrument the existing Tauri commands, not a new lifecycle command**

In `argo_tls.rs`, extract only `traceparent` and the `x-gawain-*` identity headers from `GatewayMtlsProxyRequest.headers`. Write start/end JSONL events through the existing runtime log facility, with service `skyline.tauri-mtls`, fresh Tauri span ID, and the renderer span as parent. Apply the same behavior to `gateway_mtls_proxy_stream`. Never log the HTTP body, certificate paths, authorization/cookie headers, or private key material.

- [ ] **Step 7: Make ACK provisional in the lifecycle panel**

Store `{busyOp, operationId}` after dispatch. Clear it only when `subscribeDemoLifecycleState` delivers the same operation ID with a terminal `(Running,true)` or Failed state, or when the Contract timeout produces a visible timeout failure. Reload recovery may adopt an already-running operation only when its operation ID matches persisted nonsecret pending metadata.

- [ ] **Step 8: Run frontend/Tauri checks and commit**

Run:

```bash
bun run --filter @robot/gateway-client test -- demoRobotControl demoLifecycleState
bun run --filter @robot/gateway-client typecheck
bun run --filter @robot/skyline typecheck
cargo fmt --manifest-path apps/skyline/src-tauri/Cargo.toml -- --check
cargo test --manifest-path apps/skyline/src-tauri/Cargo.toml argo_tls -- --nocapture
git diff --check
```

Expected: all commands exit zero. Do not run unrelated Skyline UI tests contrary to its local AGENTS instructions.

Commit: `git commit -am "feat(lifecycle): bind Tauri UI state to terminal operation"` and add generated/test files explicitly.

### Task 4: Build the deterministic canary fixture

**Files (Gawain):**
- Create: `fixtures/service-manager/gawain-canary`
- Create: `fixtures/service-manager/gawain-canary.service`
- Create: `tests/test_canary_fixture.py`

- [ ] **Step 1: Write local fixture tests before the script**

Tests run the script in a temporary state/control directory with a fake `systemd-notify` earlier in PATH. Assert normal mode emits one valid JSON state with generation, PID, boot ID, monotonic start, and script SHA-256; `fail-start` exits 42 without ready notification; `delay-ready=1` delays the ready notification; SIGTERM exits cleanly.

- [ ] **Step 2: Run the focused fixture test and confirm RED**

Run: `python3 -m pytest tests/test_canary_fixture.py -q`

Expected: fixture files do not exist.

- [ ] **Step 3: Implement the POSIX canary**

The script uses fixed environment variables `GAWAIN_CANARY_STATE_DIR` and `GAWAIN_CANARY_CONTROL_DIR`, reads mode from `mode`, gets generation from `/proc/sys/kernel/random/uuid`, boot ID from `/proc/sys/kernel/random/boot_id`, monotonic seconds from `/proc/uptime`, hashes `$0` with `sha256sum`, atomically renames its JSON state file, calls `systemd-notify --ready`, and sleeps until SIGTERM. It never opens network sockets or accesses robot/ROS devices.

The user unit is:

```ini
[Unit]
Description=Gawain deterministic verification canary

[Service]
Type=notify
NotifyAccess=main
Environment=GAWAIN_CANARY_STATE_DIR=%h/.local/state/gawain-canary
Environment=GAWAIN_CANARY_CONTROL_DIR=%h/.config/gawain-canary
ExecStart=%h/.local/lib/gawain-canary/gawain-canary
Restart=no
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=default.target
```

- [ ] **Step 4: Run tests and commit**

Run:

```bash
python3 -m pytest tests/test_canary_fixture.py -q
systemd-analyze verify fixtures/service-manager/gawain-canary.service
```

Expected: tests pass and unit verification exits zero.

Commit: `git commit -am "feat(pilot): add deterministic systemd canary fixture"` plus add new files.

### Task 5: Add Permit-bound SP000065 deployment, oracle, and rollback adapters

**Files (Gawain):**
- Create: `gawain_verification/pilot/__init__.py`
- Create: `gawain_verification/pilot/remote.py`
- Create: `gawain_verification/pilot/service_manager.py`
- Create: `tests/test_pilot_remote.py`
- Create: `tests/test_service_manager_pilot.py`
- Modify: `gawain_verification/cli.py`

- [ ] **Step 1: Write failing command-construction and no-mutation tests**

Use a fake command runner. Assert the adapter performs read-only host identity and digest checks before its first `rsync`/`systemctl` mutation; missing/expired Permit, wrong device, stale digest (N-05), or a requested `--full-access` not present in Permit performs zero mutations.

The CLI shape is fixed:

```text
python3 -m gawain_verification pilot service-manager \
  --contract contract.json --candidate candidate.json --permit permit.json \
  --ssh-target <operator-approved-target> --gateway https://192.168.110.65:50053 \
  [--full-access] --bundle-out <new-empty-directory>
```

`--full-access` is the requested parameter switch. It is accepted only when the signed Permit contains `full_access=true`; it does not weaken identity, evidence, or hardware protections.

- [ ] **Step 2: Run focused adapter tests and confirm RED**

Run: `python3 -m pytest tests/test_pilot_remote.py tests/test_service_manager_pilot.py -q`

Expected: pilot modules and CLI command are absent.

- [ ] **Step 3: Implement a fixed-command remote boundary**

`Remote.run()` accepts an enum-like fixed operation, not arbitrary shell supplied by Contract/Candidate. Implement only host identity, `systemctl --user show`, journal capture, SHA-256, install fixture, set mode, daemon-reload, restart, stop, and restore. Capture stdout/stderr/exit code/timestamps as artifacts, redact known sensitive keys, and enforce the three-minute command timeout.

- [ ] **Step 4: Implement transactional deployment and rollback**

Snapshot existing unit/script/control files and their digests before mutation. Deploy with `rsync`, fixed user-owned destinations, `systemctl --user daemon-reload`, and start. On non-READY outcomes restore the exact snapshot and verify digests; on READY keep the verified canary running for human acceptance. Record `rollback_status` independently from verdict.

- [ ] **Step 5: Implement the independent oracle**

Capture before/after `MainPID`, `ActiveState`, `SubState`, `ActiveEnterTimestampMonotonic`, boot ID, canary generation/state JSON, unit/script digests, and journal window. A positive restart requires generation change and timestamp increase; PID change is auxiliary only.

- [ ] **Step 6: Run tests and commit**

Run: `python3 -m pytest tests/test_pilot_remote.py tests/test_service_manager_pilot.py -q`

Expected: all tests pass with fake remote runner and no real SSH.

Commit: `git commit -am "feat(pilot): add permit-bound canary deployment and oracle"` plus add new modules/tests.

### Task 6: Encode and exercise the six-case Pilot matrix

**Files (Gawain):**
- Create: `gawain_verification/pilot/scenarios.py`
- Create: `gawain_verification/pilot/tauri_driver.py`
- Create: `tests/test_pilot_scenarios.py`
- Create: `examples/service-manager-pilot/contract.json`
- Create: `examples/service-manager-pilot/permit.template.json`

- [ ] **Step 1: Write scenario state-machine tests**

Assert exact order `N-05, P-01, N-01, N-02, N-03, N-04, final-health`. Each mutation scenario must prove setup digest, injection activation, expected oracle, cleanup digest, and cleanup oracle before the next starts.

- [ ] **Step 2: Implement scenario mechanisms**

- N-05: alter only the observed installed digest fixture in the fake/preflight path; expect action blocked and generation unchanged.
- P-01: real Tauri control with service `gawain-canary`; require full §5.3 oracle.
- N-01: drive the same Tauri verification control with `gawain-canary-missing`; expect correlated terminal rejection and unchanged real canary.
- N-02: click Restart, wait until the Tauri proxy records its request-dispatched `SPAN_START`, then reload the Tauri webview before unary ACK is consumed; require no automatic second Restart and recovery only from the matching streamed operation state.
- N-03: set canary mode `fail-start`, prove the mode file digest, click Restart, require systemd/Backend/UI failure, then clear mode and recover.
- N-04: set `delay-ready` beyond Contract timeout, require timeout and rejection of the late terminal event for the ended attempt, then clear mode and recover.

- [ ] **Step 3: Implement the real Tauri driver boundary**

The driver starts the committed Skyline Tauri binary with nonsecret `GAWAIN_RUN_ID`, Candidate/Contract IDs, and bundle artifact directory; connects through the platform Tauri WebDriver; selects SP000065; drives the lifecycle verification control; records screenshots, control IDs, timestamps, operation ID, and terminal UI text. If the real Tauri driver is unavailable, return `BLOCKED_INFRA`; never substitute Playwright browser mode.

- [ ] **Step 4: Seal and validate the bundle**

Collect control-plane trace, application trace, Tauri artifacts, Gateway/Backend logs, device journal/state, deployment digests, scenario records, and rollback record. Hash every artifact, derive the verdict, then invoke the core validator. A bundle that the core rejects cannot be returned as READY.

- [ ] **Step 5: Run off-device scenario tests and commit**

Run:

```bash
python3 -m pytest tests/test_pilot_scenarios.py tests/test_service_manager_pilot.py -q
python3 -m gawain_verification pilot service-manager --help
```

Expected: fake scenario suite passes; help lists the fixed arguments and `--full-access`.

Commit: `git commit -am "feat(pilot): execute service manager verification matrix"` plus add new files.

### Task 7: Build and stage all Candidate components without touching SP000065

**Files:** no source changes expected

- [ ] **Step 1: Verify every isolated worktree is clean except its intended commits**

Record repository path, branch, base, HEAD, tree hash, dirty diff hash, build recipe, and staged artifact paths into Candidate Set. A dirty or conflicted worktree is `ENV_INVALID`.

- [ ] **Step 2: Run full off-device tests**

Run the focused commands from Tasks 1–6 plus:

```bash
# ArgoGateway
cargo test -p argo-gateway-server
cargo clippy -p argo-gateway-server --all-targets --all-features -- -D warnings

# ArgoWatch/demo_app_service
cargo test -p demo-app-lifecycle
cargo clippy -p demo-app-lifecycle --all-targets -- -D warnings

# Frontend
bun run --filter @robot/gateway-client test
bun run --filter @robot/gateway-client typecheck
bun run --filter @robot/skyline typecheck

# Gawain
python3 -m pytest -q
python3 -m compileall -q gawain_verification
```

Expected: all commands exit zero; a silent command beyond three minutes is recorded and continued as a problem.

- [ ] **Step 3: Build target artifacts and compute digests**

Build the Backend for `x86_64-unknown-linux-musl`, build the matching ArgoGateway package, and build the real Skyline Tauri target for the test workstation. Compute SHA-256 from final artifacts, not intermediate binaries, and update Candidate Set through the canonical ID helper.

- [ ] **Step 4: Validate the Permit and dry-run the Pilot**

Run the Pilot CLI in `--dry-run` mode. Expected: it resolves SP000065, prints planned fixed operations and rollback targets, validates `full_access`, creates no SSH mutation, and does not claim READY.

### Task 8: Deploy to SP000065, run the matrix, and hand off for human acceptance

**Files:** generated evidence only under the operator-selected bundle directory; no credentials in repository

- [ ] **Step 1: Perform read-only real-device preflight**

Verify SP000065 identity, `192.168.110.65:50053` mTLS endpoint, boot ID, safety controls, systemd user session, `systemd-notify`, available space, current Backend/Gateway/canary state, and rollback destinations. Any mismatch returns `ENV_INVALID` or `BLOCKED_INFRA` before mutation.

The approved Contract freezes `systemd_scope: user`. Preflight must prove that the Backend's `robot-systemd-user` provider can reach the required user-session D-Bus on SP000065, including the effective runtime environment used by the root system service. If the user manager or session bus is unavailable, record `ENV_INVALID` and stop before mutation; do not silently change the canary or registry entry to system scope.

- [ ] **Step 2: Snapshot and deploy exact artifacts**

Create recoverable timestamped backups, deploy canary plus the Candidate Gateway/Backend using their repository packaging procedures, update only the additive canary registry entry, daemon-reload/restart the affected services in dependency-safe order, and independently verify installed SHA-256.

- [ ] **Step 3: Run the six scenarios with a safety attendant present**

Execute the fixed matrix once. Stop immediately on emergency stop, operator abort, lost contact, failed cleanup, unexpected actuator/navigation activity, or target identity drift. Do not proceed to the next injection without cleanup proof.

- [ ] **Step 4: Validate the sealed bundle and apply outcome policy**

Run:

```bash
python3 -m gawain_verification validate <bundle>/evidence-bundle.json
```

If READY, leave the Candidate and normal canary deployed for user verification. For FAIL, INCONCLUSIVE, ENV_INVALID, or mutation-after-BLOCKED_INFRA, rollback and verify restoration. Preserve the original verdict plus rollback status.

- [ ] **Step 5: Give the user a minimal human acceptance checklist**

Provide bundle ID, Candidate ID, Contract ID, installed digests, current canary generation/unit state, exact UI control used, and the path to evidence. The user independently performs the final real-device check and records acceptance separately; Gawain never writes `ACCEPTED` itself.

## Plan self-review

- Spec coverage: the plan covers the actual existing Tauri mTLS hop, full operation correlation, ACK-vs-terminal semantics, deterministic canary, all five negative cases, independent real-device oracle, artifact sealing, rollback, `full_access`, and human handoff.
- Factual correction: no new lifecycle-specific Tauri command is planned; SP000065 already traverses `gateway_mtls_proxy` and `gateway_mtls_proxy_stream`.
- Isolation: conflicted/dirty shared frontend and Gateway checkouts are never edited; isolated worktrees own all changes.
- Safety: the canary has no robot/ROS/device access, Permit validation precedes mutation, and `full_access` never changes hardware or evidence boundaries.
- Scope: `nav-runtime` is explicitly excluded; it receives a separate Contract only after this Pilot is accepted.
