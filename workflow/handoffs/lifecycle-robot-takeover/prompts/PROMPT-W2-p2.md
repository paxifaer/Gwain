# PROMPT-W2 — P2 Develop worker (sonnet),group_restart + depends_on topology + restart cascade

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

You are **W2 of Lifecycle Robot Takeover P2**. P1 closed ACCEPT WITH CONCERNS at `handoffs/lifecycle-robot-takeover/V1-VERDICT.md` (5/5 PA green, all invariants green, 0 Hard FAIL). Stage P2 = **group_restart verb + depends_on topology consumption (handler-level fan-out) + restart cascade**.

## Normative reads, in order

1. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/lifecycle-robot-takeover/task.md` — Acceptance PB1/PB2/PB3
2. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/lifecycle-robot-takeover/decisions.md` — D-101..D-115. **D-115 is your architect's intent for PB2 — read it first.**
3. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/lifecycle-robot-takeover/V1-VERDICT.md` — what just landed in P1 (so you don't re-litigate)
4. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/lifecycle-robot-topology-audit/GAP-ANALYSIS.md` — **G4, G5, G8** (the three gaps P2 lifts)
5. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/argowatch-mvp-lifecycle/SPEC-mvp.md` §3 (handler + envelope + audit shape) and §4 (provider contract)
6. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/argowatch-mvp-lifecycle/decisions.md` — D-006 (topic scheme), D-008 (boot semantics), D-023 (inverted-index group), D-025 (prompt template)

## Environment

- `export PROTOC=/tmp/protoc/bin/protoc` before every cargo.
- `cargo -p demo-app-lifecycle` only; **NEVER `--workspace`**.
- Test gate: `cargo test -p demo-app-lifecycle -- --test-threads=1`.
- zenohd :7447 test bus live; `:17447` not yours.
- `argowatch-test.service` (user scope) and `argowatch-takeover-test.{service,target}` (system scope) are pre-installed fixtures; leave them alone.
- polkit rule `/etc/polkit-1/rules.d/49-argowatch-lifecycle.rules` grants abc `manage-units`; system scope tests run unprivileged.
- abc dev; no robot hosts.

## SHA256 sentry (D-104)

`src/runtime/reconcile.rs` baseline = `43f0155ec54357520c7b87fc7b90a3632b88e7999254c162a10e4b033d09d200`.

**D-104 grants P2 a legitimate exception**: depends_on topology consumption MAY touch converge_one. **D-115 (just landed) says you should NOT need the exception.** Implementation strategy below routes depends_on consumption through the handler fan-out, not through converge_one. Target sha256 end-of-P2 **unchanged** at `43f0155ec5…09d200`.

If during implementation you discover a situation that genuinely requires reconcile.rs changes (i.e., handler fan-out demonstrably cannot satisfy a PB acceptance target), ESCALATE with evidence BEFORE editing reconcile.rs — do NOT take the exception unilaterally.

## Deliverables

### 1. `src/spec/loader.rs` — C6/C7 depends_on validation

`depends_on: Vec<String>` is declared at `src/spec/schema.rs:74` but `validate` only runs C1..C4. Add:

- **C6 depends_on ref check**: every entry in `services[].depends_on` must reference an existing `services[].id` in the same registry. Error message names the service holding the bad ref and the unknown dep target.
- **C7 depends_on cycle check**: the depends_on DAG must be acyclic. Use topological sort (Kahn's algorithm or DFS with visited/in-stack); on cycle detection, error names at least two services on the cycle. Self-loop (`A depends_on A`) counts as a cycle.
- C6/C7 numbering is local to the loader's documentation; do NOT renumber C1-C4.
- C6/C7 must run AFTER C1-C4 so pre-existing error paths don't change shape.

### 2. `src/topic.rs` + `src/main.rs` — new action constant + dispatch entry

- Add `pub const ACTION_LIFECYCLE_GROUP_RESTART: &str = "lifecycle.group_restart";` (in whichever file owns the other ACTION_* constants — same module).
- Add dispatch arm in `main.rs` `dispatch_one` mapping the new action to `handlers::handle_lifecycle_group_restart`.
- The topic path flag mechanism (submit/result) is identical to existing verbs — do not extend it.

### 3. `src/handlers.rs` — `handle_lifecycle_group_restart` + restart cascade

This is the core of P2. Two capabilities land here.

#### 3a. Group verb handler

Signature shape (follow existing handler style):

```rust
pub async fn handle_lifecycle_group_restart(
    envelope: Envelope,
    states: &Arc<RwLock<HashMap<ServiceId, ServiceState>>>,
    registry: &Arc<Registry>,
    converge_tx: &mpsc::Sender<ServiceId>,
) -> Envelope
```

Semantics:

1. Parse payload: `{ group_id: String, requested_by: Option<String> }`. Missing `group_id` → Err envelope (`MISSING_FIELD`).
2. Resolve `computed_members` for the group from `registry.services` (same projection `handle_lifecycle_list_groups` uses — if it's factored into a helper, reuse it; if not, factor it now).
3. Unknown `group_id` → Err envelope (`UNKNOWN_GROUP`); empty member list → Err envelope (`EMPTY_GROUP`).
4. Topological sort `computed_members` using `services[].depends_on`. Services within the group with no in-group deps sort first. Deps pointing OUTSIDE the group are respected for ordering (foreign dep sorts before group internal that depends on it) but the foreign dep is NOT actuated by this op. If a cycle exists between members of this group (already prevented by C7 in loader) → defensive Err.
5. Fan-out, sequential in topo order — for each member:
   - Write Desired (`stop` op first with new seq; wait for state to reach Phase::Stopped or timeout ~5s; then `start` op with new seq; do not wait for full convergence — converge worker runs async).
   - Emit audit line via existing audit mechanism with `requested_by = format!("{}(via lifecycle.group_restart group={} orig={})", requested_by_or_unknown, group_id, seq)`.
   - Trigger converge via `converge_tx.send(service_id)`.
6. **Stop order = reverse topo** (leaves first, dependencies last). **Start order = forward topo** (deps first, leaves last). Implement as two loops, or a single loop with per-member stop-then-start if simpler — but the audit log order must be verifiable as "reverse topo stops, then forward topo starts" via per-member audit lines.
7. Result envelope: `{"group_id": ..., "members_affected": N, "member_order": ["svc_a_stopped", ..., "svc_a_started", ...]}` shape — pick a concrete JSON shape and document it in the handler docstring + test assertions.

Do NOT introduce a new envelope wire format. Reuse the existing envelope; only new `action` string + payload field.

#### 3b. Restart cascade on per-service `lifecycle.restart` (PB2, D-115)

Modify `handle_lifecycle_restart` (or its internal flow):

1. Existing behavior preserved: write Desired=Running + new restart_token + seq++, signal converge.
2. NEW: after writing the target service's Desired, compute **reverse deps** = services whose `depends_on` includes the target. For each reverse-dep service where the current state has `desired.phase == Running` (i.e., the dep is supposed to be up), CASCADE a restart:
   - Write Desired=Running + fresh restart_token + seq++ for the dep.
   - Signal converge_tx for the dep.
   - Emit audit line with `requested_by = format!("{}(cascade from lifecycle.restart svc={} orig_seq={})", requested_by, target_service_id, orig_seq)`.
3. Cascade is single-level (do not recursively cascade the cascades — reverse-deps of the dep are not touched in this op). If reverse-dep has its own reverse-deps whose Desired=Running, they'll eventually converge via their own trigger; document this in the handler docstring.
4. Circular reverse-deps already excluded by C7.
5. If the operator wants no cascade for a specific restart, they can call a yet-to-exist `--no-cascade` flag — out of scope for P2. Note in docstring.

Behavior matrix to pin in tests:
- `restart <container>` where `<exec_process>` depends_on container AND desired=Running → container restarts + exec_process gets fresh token (fresh start).
- `restart <container>` where `<exec_process>` depends_on container BUT desired=Stopped → container restarts only; exec_process stays down.
- `restart <standalone>` (no reverse-deps) → identical to pre-P2 behavior (no fan-out, no extra audit line).

### 4. `src/handlers.rs` — factor `computed_members` helper if needed

If `handle_lifecycle_list_groups` computes the inverted-index inline, extract a private fn `computed_members_for_group(registry, group_id) -> Vec<ServiceId>` used by both the existing read path and the new group handler. Keep the factor surgical; do not refactor unrelated code.

### 5. `examples/registry-robot.yaml` — uncomment depends_on chains

Update the robot yaml to:
- Uncomment the depends_on field on the sudo-beta1.1-release business services (argopilot, roboskill_server_v2) declaring `depends_on: [sudo-beta1.1-release]`.
- Uncomment the depends_on chains in Group A (rustbot-daemon + rustbot-monitor + gateway services have natural deps — pick a defensible order; e.g., `rustbot-monitor depends_on [rustbot-daemon]`, `argogateway-server depends_on [argo-zenoh-global, argo-zenoh-local]`).
- Document in the yaml's header comment: "P2 adds: depends_on chains for groups with internal ordering; fan-out via lifecycle.group_restart; restart cascade on reverse-deps."

The yaml remains DESCRIPTIVE — most services still aren't runnable on abc dev. Just expose the depends_on shape.

### 6. New tests

#### `tests/group_restart_e2e.rs` (NEW, PB1+PB3)

3-service synthetic group with depends_on: svc_a ← svc_b depends_on svc_a, svc_c depends_on svc_b. Use systemd user scope (we know it works on this box; `argowatch-test.service` reuse pattern via three separate units OR re-use the same unit thrice with distinct service ids is NOT acceptable — test ordering requires three observable units).

Pragmatic fixture: 3 systemd user units `argowatch-p2-a.service`, `argowatch-p2-b.service`, `argowatch-p2-c.service`, each `Type=simple ExecStart=/bin/sleep infinity`. Install via `scripts/install-p2-test-units.sh` (NEW, idempotent).

Tests:
1. **test01_group_restart_topo_order**: bind registry with 3 services + `depends_on` chain + group containing all three. Dispatch `lifecycle.group_restart`. Wait for full convergence. Assert **audit log order**: member stops in reverse topo order (c, b, a) THEN member starts in forward topo order (a, b, c). Source: tracing `lifecycle.audit` target — use the same `CaptureBuf` pattern as spec_loader tests, or subscribe via tracing_subscriber.
2. **test02_group_restart_converges_running**: after group_restart, all three services phase=Running.
3. **test03_group_unknown_id**: `group_id` not declared → Err envelope with `UNKNOWN_GROUP` code.
4. **test04_group_empty_members**: group declared but zero members (no services reference it) → Err envelope with `EMPTY_GROUP`.
5. **test05_restart_token_rotated_for_all_members**: after group_restart, each member's `desired.restart_token` differs from before (fresh UUID).

#### `tests/restart_cascade_e2e.rs` (NEW, PB2)

2-service depends_on pair: container + exec_process inside it.

Use the existing `docker_exec_script_e2e` fixture pattern (`argowatch-takeover-p1-bash:local` already exists, keep reusing it — do NOT build a new image unless you cannot avoid it).

- Service A: docker container named `p2-cascade-<uuid>`, expose [lifecycle, status].
- Service B: docker exec_process inside A with `exec_process = "demotarget"` + `exec_script = "/opt/demostart.sh"`, `depends_on = [A]`, expose [lifecycle, status].

Tests:
1. **test01_cascade_on_container_restart**: bind both, start both, wait convergence. Issue `lifecycle.restart A`. Wait for A converged Running AND for B's `desired.restart_token` to have rotated (via GET_STATE on B, compare token pre/post). Assert audit line contains "cascade from lifecycle.restart" sub-string.
2. **test02_no_cascade_when_dep_stopped**: bind both, start A only (B desired=Stopped). Issue `lifecycle.restart A`. Assert B's `desired.restart_token` did NOT rotate and B phase stays Stopped.
3. **test03_no_cascade_when_no_reverse_deps**: bind standalone container C (no reverse deps). Issue restart. Assert no extra audit cascade line and C restart_token rotates once.

### 7. Update `tests/spec_loader.rs` — additive only

Add 1-2 tests for C6/C7:
- **loader_depends_on_unknown_ref**: registry with `depends_on: [no_such_service]` → Err naming the unknown ref.
- **loader_depends_on_cycle**: registry with A→B→A cycle → Err naming both.

Additive-only as before; do not touch existing tests.

## Hard constraints

- **0 `Command::new` in `src/`** — zbus/bollard native APIs only. Tests and scripts MAY use `Command::new` (e.g., the install script, the test harness spawning the binary).
- **0 mock / 0 fake / 0 wiremock / 0 mockall** anywhere.
- **`.control(` sentinel exactly 1 hit at `src/runtime/reconcile.rs`** — re-verify before + after.
- **`src/runtime/reconcile.rs` sha256 = `43f0155ec5…09d200` end-of-P2** unless you ESCALATE first (see "SHA256 sentry" above). If you do change it AFTER an ESCALATE approval, the new hash must be reported in your output AND be accompanied by a surgical explanation of why handler-fan-out was insufficient.
- Do NOT touch: `src/envelope.rs` (reuse as-is), `src/config.rs`, `src/error.rs`, `src/providers/*.rs` (P2 doesn't change providers), `tests/zenoh_e2e.rs`, `tests/systemd_e2e.rs`, `tests/docker_e2e.rs`, `tests/docker_exec_e2e.rs`, `tests/docker_exec_script_e2e.rs`, `tests/process_e2e.rs`, `tests/group_api.rs`, `tests/system_scope_e2e.rs`, `tests/env_file_interp.rs`, `tests/spec_loader.rs` (additive only).
- No git commit, no git push.

## Write-set (absolute prefix `/home/abc/work/ai-stack/code/ArgoWatch/demo_app_service/`)

- `crates/demo-app-lifecycle/src/topic.rs` (new ACTION constant)
- `crates/demo-app-lifecycle/src/main.rs` (dispatch entry; doc comment refresh; minimal)
- `crates/demo-app-lifecycle/src/handlers.rs` (group_restart handler + restart cascade + member helper factoring)
- `crates/demo-app-lifecycle/src/spec/loader.rs` (C6/C7 validations)
- `crates/demo-app-lifecycle/src/spec/mod.rs` (only if a re-export is truly needed; keep minimal)
- `crates/demo-app-lifecycle/scripts/install-p2-test-units.sh` (NEW)
- `crates/demo-app-lifecycle/tests/group_restart_e2e.rs` (NEW)
- `crates/demo-app-lifecycle/tests/restart_cascade_e2e.rs` (NEW)
- `crates/demo-app-lifecycle/tests/spec_loader.rs` (additive only)
- `crates/demo-app-lifecycle/examples/registry-robot.yaml` (uncomment depends_on chains; header refresh)
- `crates/demo-app-lifecycle/Cargo.toml` (only if you actually need a new dep; **do NOT add deps speculatively** — current deps should suffice)

NOTHING ELSE. Specifically do NOT touch `src/runtime/`, `src/envelope.rs`, `src/config.rs`, `src/error.rs`, `src/providers/`, `src/spec/schema.rs`. Cargo.lock will auto-update if Cargo.toml changes.

## Output contract

1. **Deliverables** — every file created/modified + line ranges + a one-line purpose. Grep evidence for `ACTION_LIFECYCLE_GROUP_RESTART`, `computed_members_for_group`, cascade code path.
2. **Test evidence**:
   - `cargo build -p demo-app-lifecycle 2>&1 | tail -10`
   - `cargo clippy -p demo-app-lifecycle --all-targets -- -D warnings 2>&1 | tail -10`
   - `cargo test -p demo-app-lifecycle -- --test-threads=1 2>&1 | tail -50` — report pass/total. Pre-P2 = 52/52. P2 target = 52 + ~7-10 new = 59-62.
   - `systemctl is-active argowatch-p2-{a,b,c}.service` at checkpoints
   - Cascade test evidence: paste the audit log lines showing "cascade from lifecycle.restart"
   - Topo ordering evidence: paste the audit log lines showing stop-order is reverse topo and start-order is forward topo
   - sha256 BEFORE + AFTER for `src/runtime/reconcile.rs` (should match `43f0155ec5…09d200` unless ESCALATE approved otherwise)
   - `grep -c '\.control(' src/runtime/reconcile.rs` AFTER (must = 1)
3. **Design decisions traded** (≤6 bullets) — esp.:
   - How you resolved "sequential per-member stop+start" vs "two-pass stop-then-start"
   - How you treated out-of-group deps in topo ordering
   - How you deduped cascade vs. explicit operator intent
4. **Regressions / risks**.
5. **ESCALATEs** (if any). For each: the evidence, the decision you need, and what you did instead while waiting.
6. **sha256 BEFORE/AFTER + confirm-unchanged line** (or the post-ESCALATE story).
7. **Elapsed**.

## Time cap

90 min. The depends_on handlers are substantive logic — take the time needed to land them cleanly. If a single defect consumes >30 min, ESCALATE rather than band-aid.
