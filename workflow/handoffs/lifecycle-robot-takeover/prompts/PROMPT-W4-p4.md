# PROMPT-W4 — P4 Develop worker (sonnet),ProviderKind::Http + bearer token + handler matrix fix

```
Before doing anything else:
1. Read /home/abc/work/ai-stack/workflow/Gawain/workflow/bootstrap.md
2. Classify per three questions; follow rules.
3. Non-interactive. Judgment calls → ESCALATE.
4. Write-set bounded below. Report every file written with line ranges.

HEAD-guard: before any git touchpoint, run `git log --oneline -1 && git status --short`.

model_selection:
  model: sonnet
  mode: automatic
  reason: coding_and_testing
```

---

You are **W4 of Lifecycle Robot Takeover P4** — final code phase. P3 closed ACCEPT WITH CONCERNS at `handoffs/lifecycle-robot-takeover/V3-VERDICT.md` (3/3 PC green, 83/83 serial, 0 Hard FAIL). P4 = **`ProviderKind::Http` provider + bearer token injection (roboctl :8765 + read-only :8090/:19090) + handler op_allowed matrix (Restart, Completed) fix (V3-C1)**.

## CRITICAL: NO PARTIAL RETURNS

Your turn ends ONLY when the full output contract below is delivered. DO NOT return a plan, an outline, a status update, or "next I'll ..." announcements. Work continuously until deliverables + test evidence + sha256/sentinel confirmations are all in your final message. If you hit an unrecoverable wall (>5 min on one defect), ESCALATE with exact evidence in your final message.

## Normative reads, in order

1. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/lifecycle-robot-takeover/task.md` — Acceptance PD1/PD2/PD3.
2. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/lifecycle-robot-takeover/decisions.md` — D-101..D-117. **D-111 (HTTP provider schema), D-105 (polkit preferred), D-117 (new sha256 sentry = P4 baseline)** are binding.
3. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/lifecycle-robot-takeover/V3-VERDICT.md` — P3 close. **Concern C1** (state-plane vs handler-matrix `Restart`-for-`Completed` mismatch) is now P4 scope.
4. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/lifecycle-robot-takeover/V2-VERDICT.md` — P2 close.
5. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/lifecycle-robot-topology-audit/GAP-ANALYSIS.md` — **G2 (ProviderKind closed — P4 lifts this), G3 (no token injection — P4 lifts half of this**, other half = env_file `${VAR}` interp which P1 already did).
6. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/argowatch-mvp-lifecycle/SPEC-mvp.md` §4 (provider contract) + §3 (envelope + audit).
7. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/argowatch-mvp-lifecycle/decisions.md` — D-003 (no shell), D-020/D-021 (fingerprint contract).

## Environment

- `export PROTOC=/tmp/protoc/bin/protoc` before every cargo.
- `cargo -p demo-app-lifecycle` only; NEVER `--workspace`.
- Test gate: `cargo test -p demo-app-lifecycle -- --test-threads=1`.
- zenohd :7447 live; `:17447` NOT yours.
- abc dev; no robot hosts.
- sudo password `abc123` (pattern: `echo "abc123" | sudo -S -p "" <cmd>`).
- Python 3 must be installed (fixture stub uses `python3 -m http.server`). Verify with `which python3` before test design.
- Existing fixtures (leave alone): `argowatch-test.service`, `argowatch-takeover-test.{service,target}`, `argowatch-takeover-oneshot.service`, `argowatch-p2-{a,b,c}.service`, docker image `argowatch-takeover-p1-bash:local`.

## SHA256 sentry (D-117)

`src/runtime/reconcile.rs` baseline for P4 = `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822` (D-117 — new value after P3's scoped D-116 exception).

**P4 must keep this hash unchanged.** The HTTP provider is a pure provider-side module; it does not intersect `derive_converged`, `converge_one`, C2, or any reconcile.rs code path. If you find a legit reason to touch reconcile.rs in P4, ESCALATE before editing — P4 has NO exception granted.

## Deliverables

### 1. `src/spec/schema.rs` — ProviderKind::Http variant (G2 lift)

Add `Http` variant in `src/spec/schema.rs:49-55`'s `pub enum ProviderKind`. Follow existing variants: `#[serde(rename_all = "lowercase")]` so yaml writes `kind: http`. Append the variant; do NOT reorder existing variants. Add brief docstring (≤2 lines).

Note: `schema.rs` was off-limits in P1-P3 but is now unlocked. Keep the diff minimal.

### 2. `src/providers/mod.rs` — `pub mod http;`

Add the module declaration. Do not change ProviderKind-related types that already exist.

### 3. `src/providers/http.rs` — NEW provider (D-111)

#### Module shape

```rust
//! HTTP provider. Read-only probes and command-style control endpoints over HTTP.
//! Two selector shapes multiplexed:
//! - Status-only probes (e.g. rustbot-monitor :8090, robot-service-agent :19090)
//! - Command control (e.g. roboctl :8765 Bearer)
//! Bearer token source: `bearer_token_env` XOR `bearer_token_file` (D-111).
```

#### Selector schema (per-service, parsed in `bind()`)

```yaml
provider:
  instance: <http-pool>
  selector:
    status:                          # OPTIONAL; presence → STATUS feature
      url: "http://robot:8090/status"
      method: GET                    # GET or POST
      success_codes: "200,204"       # comma-sep; default "200"
      timeout_ms: 2000               # default 2000
    start:                           # OPTIONAL; presence → LIFECYCLE + Start allowed
      url: "http://robot:8765/api/group/robot-stack/start"
      method: POST
      success_codes: "200,202"
      body: '{"action":"start"}'     # OPTIONAL raw JSON body string; sent verbatim
      headers: {"X-Custom": "val"}   # OPTIONAL static extra headers
    stop:                            # OPTIONAL; presence → stop
      # same shape
    restart:                         # OPTIONAL; presence → restart
      # same shape
```

At least ONE of `status` / `start` / `stop` / `restart` must be present (else bind Err).

All four sub-objects share the same field set. All fields optional except `url`. `method` defaults to GET for `status`, POST for the three verbs.

#### Provider config (per-provider, parsed in `HttpProvider::new(config)`)

```yaml
providers:
  - id: roboctl-pool
    kind: http
    config:
      bearer_token_env: ROBOCTL_TOKEN       # OR bearer_token_file; XOR (D-111)
      # bearer_token_file: /home/abc/.config/roboctl/token
      default_timeout_ms: 2000
      user_agent: "argowatch-lifecycle/1.0"
```

Mutual exclusion (D-111): `bearer_token_env` and `bearer_token_file` MUST NOT both be set. If neither set → provider operates with no Authorization header (e.g., read-only probes without auth). If both set → bind Err naming both fields. If `bearer_token_env` set but env var missing → provider respects env_file `${VAR}` — that resolution happened earlier at loader time; at provider construction the env lookup may still return None; in that case bail with a clear Err naming the missing env var (this is the D-111 hook into D-112's `${VAR}`).

If `bearer_token_file` set: read file content at provider construction; trim trailing whitespace; if file unreadable → Err naming path.

#### Bound service implementation

For each service that binds to this provider, produce a `BoundService` with:

- `fingerprint()`: 
  - STATUS if `status` sub-object present
  - LIFECYCLE for whichever of `start`/`stop`/`restart` present (FeatureSet granularity may vary; use the existing FeatureSet API. If FeatureSet is bitwise, return the OR combination.)
- `status()`: only callable if `status` sub-object present. Perform the HTTP request. Map response:
  - HTTP success (status in `success_codes`) → `Phase::Running` with `detail["http_status"] = <code>`
  - Connection refused/timeout/DNS error → `Phase::Stopped` with `detail["http_error"] = <kind>`
  - HTTP non-success (status NOT in `success_codes`) → `Phase::Failed` with `detail["http_status"] = <code>`
- `control(ControlOp)`:
  - If op not backed by a selector sub-object → bail with `ControlOp X not supported by HTTP selector shape for service Y` (this preserves the "pruned" FeatureSet contract).
  - Perform the HTTP request via the op's sub-object.
  - Bearer header applied if provider has a token: `Authorization: Bearer <token>`.
  - Success → ControlReceipt::default() (empty detail is fine; attach the HTTP status code as detail if cheap).

#### Auth header application

- Only build the `Authorization` header if token source is configured on the provider.
- Header is applied to BOTH status and control requests from services on this provider. (Yes, even read-only probes can need auth — roboctl :8765 might).

#### reqwest dependency

- Add to `Cargo.toml`: `reqwest = { workspace = true, features = ["json", "rustls-tls"], default-features = false }`. (Workspace already has reqwest at top level; verify before adding — if existing features suffice, reuse them.) If `rustls-tls` feature not enabled at workspace, add it to the features list — do NOT bring in `native-tls` (libreSSL dep is heavy).
- Use `reqwest::Client` (async) — the lifecycle crate is tokio-native. Build one `Client` per provider (not per request).

### 4. `src/main.rs` — factory match arm

At the existing provider factory match (~`main.rs:107-138`), add the `ProviderKind::Http` arm that calls `providers::http::HttpProvider::new(config)`. Ensure the new arm compiles; existing arms untouched.

### 5. `src/handlers.rs` — extend op_allowed matrix (V3-C1)

At `handlers.rs:50-61` (the `op_allowed` matrix), extend to allow `(ControlOp::Restart, Phase::Completed) → true`. This closes V3-C1: state-plane advertises `restart` for a Completed oneshot; preflight should not bounce it.

Constraint: this is the ONLY matrix change permitted. Other matrices unchanged. When in doubt, ESCALATE rather than guess.

Also verify `compute_available_actions` in main.rs stays consistent — if it  already advertises `restart` for Completed, no change needed there.

### 6. `examples/registry-robot.yaml` — roboctl Http shape + :8090/:19090 commented

Add two new provider pools (commented since dogfood is P5):

```yaml
# P4 HTTP provider shapes (uncomment on dogfood robot):
# providers:
#   - id: roboctl-pool
#     kind: http
#     config:
#       bearer_token_file: /home/deployuser/.config/roboctl/token
#   - id: ro-http-probes
#     kind: http
#     config: {}   # no auth needed for these endpoints
#
# services:
#   - id: roboctl-robot-stack
#     provider:
#       instance: roboctl-pool
#       selector:
#         restart:
#           url: "http://127.0.0.1:8765/api/group/robot-stack/restart"
#           method: POST
#           success_codes: "200,202,204"
#         start: ...
#         stop: ...
#
#   - id: rustbot-monitor-ro
#     provider:
#       instance: ro-http-probes
#       selector:
#         status: { url: "http://127.0.0.1:8090/status", method: GET, success_codes: "200" }
#
#   - id: robot-service-agent-ro
#     provider:
#       instance: ro-http-probes
#       selector:
#         status: { url: "http://127.0.0.1:19090/status", method: GET, success_codes: "200" }
```

Header comment refresh to P4.

### 7. Tests — NO mocks. Real `python3 -m http.server` stub.

Create `scripts/start-p4-http-stub.sh` (NEW, idempotent):
- Starts a `python3 -m http.server <port>` instance on a per-test port (e.g., 18888/18889/18890 per test file)
- Writes the chosen port to a tmp file the test harness reads
- Or run inline from the test binary via `std::process::Command` (allowed in tests, NOT in src) — this is simpler; skip the shell script entirely

Use `python3 -m http.server` (built-in) OR `python3 -c "<custom>"` if you need control endpoints that return specific codes / accept POST. `python3 -m http.server` only serves GET; for POST-accepting fixture you'll need a tiny `python3 -c` inline script:

```python
import http.server, socketserver, sys, json
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/status":
            self.send_response(200); self.end_headers(); self.wfile.write(b'{"ok": true}')
        else:
            self.send_response(404); self.end_headers()
    def do_POST(self):
        if self.path.startswith("/api/"):
            body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            self.send_response(200); self.end_headers(); self.wfile.write(b'{"restarted": true}')
        else:
            self.send_response(404); self.end_headers()
    def do_PUT(self):
        self.send_response(405); self.end_headers()
    def log_message(self, fmt, *args): pass
with socketserver.TCPServer(("127.0.0.1", int(sys.argv[1])), H) as s:
    s.serve_forever()
```

Save as `tests/fixtures/http_stub.py` and spawn via `std::process::Command::new("python3").arg("tests/fixtures/http_stub.py").arg("<port>")`. Test harness kills it on teardown.

#### `tests/http_provider_status_e2e.rs` (NEW)

Read-only probe shape.

1. **test01_bind_plus_status_running**: bind a service `{ status: { url: http://127.0.0.1:<port>/status, method: GET, success_codes: "200" } }`. Status call → Phase::Running, `detail["http_status"] == 200`.
2. **test02_status_failed_on_404**: request to `/nonexistent`. → Phase::Failed, `detail["http_status"] == 404`.
3. **test03_status_stopped_on_conn_refused**: kill the stub; status call → Phase::Stopped (connection refused mapped correctly).
4. **test04_control_bails_on_status_only_shape**: ControlOp::Restart on this shape → Err (no `restart` selector present).

#### `tests/http_provider_control_e2e.rs` (NEW)

Command control shape.

1. **test01_restart_op_via_http_post**: bind with `restart: { url: /api/group/robot-stack/restart, method: POST, success_codes: "200" }`. Control(Restart) → ControlReceipt Ok. Verify via a side-channel (e.g., the python stub logs the hit; or simpler — run the stub in verbose mode and assert the response status via your ControlReceipt detail).
2. **test02_op_missing_selector_bails**: bind a shape with only `start: {...}`, then ControlOp::Stop → Err.
3. **test03_non_success_code_maps_to_err**: stub returns 500 on a path; control call → Err with the HTTP code visible in the message.
4. **test04_bearer_token_injected_when_configured**: provider config `bearer_token_env: P4_TEST_TOKEN`. Set env `P4_TEST_TOKEN=abc123`. Spawn the stub so it REQUIRES the header (assert presence; return 401 without it). Control call → success. Assert the stub saw `Authorization: Bearer abc123`. (If you implement the stub to echo the header it saw, the test reads it back.)

#### `tests/http_bearer_token_e2e.rs` (NEW)

Bearer token source paths.

1. **test01_bearer_token_env_happy**: env var set; provider constructs; token used.
2. **test02_bearer_token_env_missing**: env var NOT set → provider constructor Err naming the env var. ENVIRONMENT cleanup: ensure the var is unset (use `std::env::remove_var` at test start; env-var mutex per Env-var Test Lock memory: guard the whole test with a static tokio::sync::Mutex, and have any other test reading the default env hold the same mutex — see `feedback_env_var_test_lock`).
3. **test03_bearer_token_file_happy**: tempfile with token content → provider constructs → control/stats call includes header.
4. **test04_bearer_token_file_unreadable**: file with mode 000 → provider Err naming path.
5. **test05_bearer_token_env_and_file_mutual_exclusion**: both set → Err naming both fields.

#### `tests/spec_loader.rs` — additive

One test: a yaml declaring a `kind: http` provider parses. Another: assert an unknown kind (e.g. `kind: grpc`) still fails to parse (back-compat pin for serde strict).

### 8. Cargo.toml change

- Add `reqwest` with `rustls-tls`, `json` features (or reuse existing workspace features if suitable).
- Report `cargo tree -p demo-app-lifecycle -i reqwest` output.
- Cargo.lock auto-updates. No other changes.

## Hard constraints

- **0 `Command::new` / `std::process::Command::new` in `src/`** — Python stub spawn happens only in tests. The HTTP provider uses reqwest (a native Rust HTTP library), not curl/wget/via Command.
- **0 mock / 0 fake / 0 wiremock / 0 mockall** anywhere. Python stub is a REAL HTTP server, not a mock crate. This is the same pattern as the docker fixture work — a real running process serving real traffic.
- **`.control(` sentinel exactly 1 hit at `src/runtime/reconcile.rs`** — re-verify before + after.
- **`src/runtime/reconcile.rs` sha256 must equal `74b92f34…72b822` end-of-P4** (D-117). P4 has NO exception granted. If reconcile.rs sha256 differs at end → Hard FAIL.
- Do NOT touch: `src/runtime/`, `src/envelope.rs`, `src/topic.rs`, `src/config.rs`, `src/error.rs`, `src/providers/docker.rs`, `src/providers/process.rs`, `src/providers/systemd.rs`, `src/spec/loader.rs` (unless a tiny additive change is needed for HTTP selector parsing — ESCALATE first if so).
- Do NOT touch existing tests except `tests/spec_loader.rs` (additive only).
- No git commit, no git push.

## Write-set (absolute prefix `/home/abc/work/ai-stack/code/ArgoWatch/demo_app_service/`)

- `crates/demo-app-lifecycle/Cargo.toml` (reqwest dep)
- `crates/demo-app-lifecycle/src/spec/schema.rs` (ProviderKind::Http variant, minimal)
- `crates/demo-app-lifecycle/src/providers/mod.rs` (`pub mod http;`)
- `crates/demo-app-lifecycle/src/providers/http.rs` (NEW — the provider)
- `crates/demo-app-lifecycle/src/main.rs` (factory match arm)
- `crates/demo-app-lifecycle/src/handlers.rs` (op_allowed matrix — (Restart, Completed) extension ONLY; nothing else)
- `crates/demo-app-lifecycle/scripts/install-p4-fixture.sh` (NEW; only if needed — inline python spawn may suffice)
- `crates/demo-app-lifecycle/tests/fixtures/http_stub.py` (NEW)
- `crates/demo-app-lifecycle/tests/http_provider_status_e2e.rs` (NEW; 4 tests)
- `crates/demo-app-lifecycle/tests/http_provider_control_e2e.rs` (NEW; 4 tests)
- `crates/demo-app-lifecycle/tests/http_bearer_token_e2e.rs` (NEW; 5 tests)
- `crates/demo-app-lifecycle/tests/spec_loader.rs` (additive)
- `crates/demo-app-lifecycle/examples/registry-robot.yaml` (P4 commented HTTP shape + header refresh)

NOTHING ELSE.

## Output contract

1. **Deliverables** — every file created/modified + line ranges + one-line purpose. Grep evidence for: `ProviderKind::Http`, `bearer_token_env`, `bearer_token_file`, `pub mod http`, `mock` (expect prohibition-comments only), op_allowed Completed arm.
2. **Test evidence**:
   - `cargo build -p demo-app-lifecycle 2>&1 | tail -10`
   - `cargo clippy -p demo-app-lifecycle --all-targets -- -D warnings 2>&1 | tail -10`
   - `cargo test -p demo-app-lifecycle -- --test-threads=1 2>&1 | tail -60` — report pass/total. Pre-P4 = 83. Target = 83 + ~13 (4 status + 4 control + 5 bearer) + additive spec_loader = ~98.
   - HTTP stub log evidence showing bearer token header received (if stub logs/holds requests)
   - Oneshot Restart-from-Completed evidence: after the op_allowed matrix extension, a `lifecycle.restart` on a Completed oneshot now succeeds (previously bounced). Show before/after via test.
   - sha256 BEFORE + AFTER for reconcile.rs — must equal D-117 value `74b92f34…72b822`.
   - `grep -c '\.control(' src/runtime/reconcile.rs` AFTER — must = 1.
3. **Design decisions traded** (≤6 bullets) — esp.:
   - Selector sub-object shape justification (status/start/stop/restart independently optional)
   - Bearer token applied to both status and control requests (why)
   - reqwest feature set chosen (rustls vs native-tls)
   - Env-var test mutex pattern (feedback_env_var_test_lock)
4. **Regressions / risks**.
5. **ESCALATEs** (if any).
6. **reconcile.rs sha256 = `74b92f34…72b822` end-of-P4 (confirm)**.
7. **Elapsed**.

## Time cap

120 min. The HTTP provider is the largest single-file deliverable of P0-P4. Single-defect debugging >30 min → ESCALATE.
