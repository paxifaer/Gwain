# V2 Verdict — Lifecycle Robot Takeover P2

Verdict: **ACCEPT WITH CONCERNS**

Verifier: V2 (adversarial). Every dynamic claim below was re-executed in
the verifier's own shell (uid=abc, unprivileged); no evidence is
transcribed from the worker's paste. Full serial test log:
`/tmp/v2-test-run.log`. Synthetic-loader probe drove six C6/C7 edge
cases via a scratch `tests/v2_synthetic_probe.rs` written+run+deleted
by the verifier (no trace remains in the deliverable).

## Acceptance criteria

- **PB1 group_restart fans out per depends_on topo (start forward, stop reverse)**:
  PASS — `tests/group_restart_e2e.rs::test01_group_restart_topo_order`
  drove the full chain against real `argowatch-p2-{a,b,c}.service` user
  units (confirmed installed at `~/.config/systemd/user/`, 168 bytes
  each, mtime Aug 18 12:13). Audit evidence captured from my own run:

  ```
  stop  svc_c seq=2  requester=test-op(via lifecycle.group_restart group=p2-topo-group orig=688ecab7-...)
  stop  svc_b seq=2  requester=test-op(via ... orig=688ecab7-...)
  stop  svc_a seq=2  requester=test-op(via ... orig=688ecab7-...)
  start svc_a seq=3 restart_token=Some("42eb1e0e-...") requester=test-op(via ...)
  start svc_b seq=3 restart_token=Some("b13dbcb6-...") requester=test-op(via ...)
  start svc_c seq=3 restart_token=Some("3504394b-1c08-...") requester=test-op(via ...)
  ```

  Single `orig=` uuid shared across all six lines; reverse-topo stops
  precede forward-topo starts; per-member fresh UUID restart_tokens
  distinct pairwise. `src/handlers.rs:707-786` walks reverse for stop
  leg, forward for start leg, via custom `write_desired_group_start`
  (line 624) that rotates the token.

- **PB2 container Restart triggers exec_process Start**:
  PASS — `tests/restart_cascade_e2e.rs::test01_cascade_on_container_restart`
  uses the real `argowatch-takeover-p1-bash:local` fixture (image
  presence asserted at line 260), real musl-gcc-compiled `demotarget`
  injected at test time (line 152), real `/opt/demostart.sh` (line 245),
  real bollard client and real Runtime (line 377-418). Cascade audit
  evidence captured from my own run:

  ```
  lifecycle.audit service_id=svc_exec op=Restart seq=2
    restart_token=Some("06358ae0-dd43-4e57-9441-9bb6936954c6")
    requester=op(cascade from lifecycle.restart svc=svc_container orig_seq=1)
  ```

  Test asserts BOTH the dep's `desired.restart_token` rotated
  (pre/post `Option<String>` compared, `assert_ne` + `is_some`) AND
  the audit line carries the cascade marker naming `svc=svc_container`
  and `service_id=svc_exec`. test02 + test03 pin the two suppression
  paths (desired=Stopped, no-reverse-deps) with negative audit
  assertions AND pre/post token equality.

- **PB3 audit line per fan-out member with op source = group verb**:
  PASS — handler emits one `lifecycle.audit` line per member per leg
  (six lines for a 3-member group). `requester` carries
  `orig + "(via lifecycle.group_restart group=<gid> orig=<req-uuid>)"`
  (handler lines 736-740 stop leg, 763-765 start leg). Audit assertions
  in test01 verify this via the production `lifecycle.audit` tracing
  target (CaptureBuf pattern, line 87-95 of the test file), not via
  handler bookkeeping.

## Hard invariants

- **sha256 reconcile.rs unchanged**: PASS —
  `43f0155ec54357520c7b87fc7b90a3632b88e7999254c162a10e4b033d09d200`
  (exact match; mtime Aug 17 15:49, P1-era, untouched by W2). D-115's
  commitment to NOT use the D-104 P2 exception is honoured.
- **`.control(` sentinel = 1**: PASS — `grep -c` returns exactly 1.
- **0 `Command::new` in src/**: PASS — grep returns empty (exit 1).
  `Command::new` surfaces only inside tests (musl-gcc spawn for the
  demotarget compile) which is permitted; rule binds `src/` only.
- **0 mock/fake/wiremock/mockall**: PASS — all 10 grep hits across
  src/tests/scripts/examples/Cargo.toml are prohibition-referencing
  comments (same set V1 logged, plus the two new test files
  restating the same fail-loud language). No double anywhere.
- **No git commit/push**: PASS — HEAD remains `43f9c55`;
  `git status --short` matches V1's closing state exactly
  (workspace `Cargo.toml`/`Cargo.lock` `M`, whole
  `crates/demo-app-lifecycle/` untracked). Zero new tracked touches.
- **D-115 compliance**: PASS —
  - `reconcile.rs` includes zero references to `depends_on`,
    `group_restart`, or `cascade` (triple-grep all empty).
  - The cascade fires ONLY in `handle_lifecycle_restart`
    (`src/handlers.rs:257`), NEVER inside `converge_one` /
    `observer_loop`.
  - No background watcher exists that auto-restarts exec_process on
    container state change (would surface as new spawn in
    `runtime/mod.rs` or service-map walk in `reconcile.rs`; both are
    absent — confirmed by the sha256 pin).
  - Op-driven cascade, not observer self-heal. converge_one unchanged.

## Lift verification

- **G4 group verb**: PASS — new action constant
  `ACTION_LIFECYCLE_GROUP_RESTART = "lifecycle.group_restart"` at
  `src/handlers.rs:41` (colocated with the other ACTION_* constants,
  matching the prompt's allowance). Dispatch arm at
  `src/main.rs:316` with the new P2 comment block at line 313-315
  referencing G4/D-101. Full error envelope set present:
  `MISSING_FIELD` (line 684), `UNKNOWN_GROUP` (line 692),
  `EMPTY_GROUP` (line 700), `MISSING_FEATURE` (line 712),
  `TOPO_CYCLE` (line 724), `GROUP_MEMBER_STOP_FAILED`,
  `GROUP_MEMBER_START_FAILED` (defensive legs). Both PB1-ordering and
  PB3-audit evidence above.
- **G5 depends_on topological consumption**: PASS —
  `check_c6_depends_on_refs_resolve` at `src/spec/loader.rs:429-443` +
  `check_c7_depends_on_acyclic` at `src/spec/loader.rs:459-519`
  invoked after C1-C4 (`validate()` body at line 309-321). Kahn's
  algorithm is used in BOTH places (loader for cycle rejection,
  handler for fan-out ordering) as the docstring promises
  (`loader.rs:457`). Handler-side `topo_sort_group_forward` at
  `src/handlers.rs:485-585` walks the transitive `depends_on`
  closure (line 503-514) so out-of-group deps sit correctly in the
  order, then filters them out of the emitted sequence (line 580-584)
  — never actuating foreign services. Synthetic probe drove six edge
  cases (unknown ref, self-loop, two-cycle, five-cycle, two disjoint
  cycles, clean DAG); all bailed/passed as claimed, C6 error names
  both svc + target, C7 error names up to 4 residue members with
  total residue size.
- **G8 container Restart cascade to exec_process**: PASS —
  `cascade_restart_to_reverse_deps` at `src/handlers.rs:275-340`.
  Reverse-dep discovery via `s.depends_on.iter().any(|d| d == target_sid)`
  (line 286). Three gates in order:
  (a) `dep_spec.expose.contains(&Feature::Lifecycle)` (line 296-298)
      — non-Lifecycle deps skipped silently per W's claim,
  (b) `dep.desired.state == RunState::Running` (line 299-308) — the
      D-115 desired-gate, phase ignored (correctly: converge_one
      resolves Start vs Restart from live phase),
  (c) write via `write_desired_and_signal(.., ControlOp::Restart, ..)`
      rotates `restart_token` to a fresh UUID and bumps `seq`
      (handler lines 113-154). Single-level confirmed: the cascade
      function does NOT recurse into dep's own reverse-deps (loop
      body lines 292-339 has no self-call).

## Test quality audit

- **`group_restart_e2e` fixture real + assertions observable**:
  NON-tautological. Fixture sanity at `tests/group_restart_e2e.rs:159-182`
  binds + statuses each of the three user units and panics naming the
  install script if unreachable (testing.md §3 fail-loud). Real
  `SystemdProvider::new(Scope::User)` + real user-session zbus; real
  `Runtime` with observer + converge loops spawned (lines 213-221).
  - test01 payload member_order AND audit-line ordering both asserted,
    where the audit side is captured from the PRODUCTION `lifecycle.audit`
    tracing target (CaptureBuf, lines 87-95), not internal state. The
    6 ordered eprintln!s are emitted as evidence on `--nocapture`.
  - test02 asserts per-member `phase=Running` AND `conditions.converged`.
  - test03/test04 drive the wire `Envelope` and assert the
    `err.code == "UNKNOWN_GROUP" | "EMPTY_GROUP"` and the message text
    contains the offending gid — these are on the wire Envelope,
    not on internal side effects.
  - test05 compares pre/post `restart_token` and requires `post.is_some()`
    + pairwise-distinct across the three members. The
    `assert_ne!(pre, post)` is weakly tautological when `pre=None` (as
    it must be after a Start); the load-bearing pin is
    `post.is_some()` since only the custom `write_desired_group_start`
    rotates the token on Start. Not a tautology, but the strictest
    form would also pin `pre.is_none()`. Acceptable.
- **`restart_cascade_e2e` fixture real + cascade evidence**:
  NON-tautological. Real container from the existing
  `argowatch-takeover-p1-bash:local` image (line 269, image presence
  fail-loud with remediation line); real musl-gcc compile + base64
  injection at test time (lines 152-171 + 218-252); observable signal
  via `pgrep -x demotarget` exit code (line 293) — same fixture
  contract as the P1 `docker_exec_script_e2e` suite. Test01 asserts
  BOTH post-cascade token rotation AND audit substring. Tests 02/03
  are not Yes-men: they assert no-cascade audit line AND token
  equality, so a regression that mistakingly cascades would trip them.
  Cleanup via `catch_unwind` + container removal (lines 553, 651,
  748-749).
- **C6/C7 spec_loader coverage**: NON-tautological. The three additive
  tests at lines 421, 457, 501 assert the Err content names the
  offending service AND the unknown dep (C6) or names cycle
  participants (C7, including the self-loop case the prompt didn't
  strictly require). W2 added `loader_depends_on_self_loop_is_cycle`
  as a third test beyond the prompt's "1-2 tests"; the
  `loader_env_file_warn_is_actually_emitted` D-114 test content at
  line 542 is byte-identical to its P1 shape (verified by reading).
  Additive placement is mid-file (before the warn-capture section),
  not strictly end-of-file — but additive-only is honoured (no
  existing test modified).
- **Tautology hunt result**: NO tautological tests found. Every
  assertion is observable through the production-emission path
  (wire envelope, tracing subscriber, systemd/docker live state) or
  through the test's own direct state-plane read
  (`rt.states.read().await`) which the test can also corroborate via
  audit / phase arrive-watch. Environment-missing paths panic with
  remediation text (install script name, docker group hint) — no
  silent skips, no in-memory fallbacks.

## Write-set compliance

- **Modified** (P2, authorized):
  - `src/main.rs` (Aug 18 12:13) — dispatch arm + P2 comment.
  - `src/handlers.rs` (Aug 18 12:13) — constant + cascade +
    computed_members helper + write_desired_group_start +
    handle_lifecycle_group_restart.
  - `src/spec/loader.rs` (Aug 18 12:09) — C6/C7.
  - `tests/spec_loader.rs` (Aug 18 12:09) — 3 additive tests
    (file went 13 → 16 tests).
  - `examples/registry-robot.yaml` (Aug 18 12:19) — depends_on
    chains uncommented (rustbot-monitor→rustbot-daemon,
    argogateway-client→argo-zenoh-local,
    argogateway-server→[argo-zenoh-global, argo-zenoh-local],
    argopilot→sudo-beta1.1-release,
    roboskill_server_v2→sudo-beta1.1-release) + P2 header note.
- **New** (authorized):
  - `scripts/install-p2-test-units.sh` (34 LoC) — matches
    `install-test-unit.sh` MVP pattern (idempotent, no
    Requires/Wants between the three units).
  - `tests/group_restart_e2e.rs` (517 LoC).
  - `tests/restart_cascade_e2e.rs` (753 LoC).
- **Untouched as required**:
  - `src/topic.rs` (Aug 17 15:41) — ACTION constant placed in
    `handlers.rs` instead, per the prompt's "whichever file owns
    the other ACTION_* constants" allowance.
  - `src/spec/mod.rs` (Aug 18 11:21, P1-era).
  - `src/runtime/*.rs` all carry pre-P2 mtimes (Aug 17 15:42-15:49).
  - `src/envelope.rs`, `src/error.rs`, `src/config.rs`,
    `src/providers/*.rs` (Aug 17 15:41 / Aug 18 11:22 P1).
  - `src/spec/schema.rs` (Aug 18 11:17, V1 already noted the
    W1-write-then-revert residue; content matches MVP spec §3.1).
  - All off-limits tests (`zenoh_e2e.rs`, `systemd_e2e.rs`,
    `docker_e2e.rs`, `docker_exec_e2e.rs`, `docker_exec_script_e2e.rs`,
    `process_e2e.rs`, `group_api.rs`, `system_scope_e2e.rs`,
    `env_file_interp.rs`) carry P1/pre mtimes.
  - `Cargo.toml`/`Cargo.lock` untouched (Aug 17 18:17, MVP crate
    registration).
- **Out-of-bounds touches**: NONE.

## Concerns (non-blocking)

1. **`src/spec/loader.rs:23` top-of-file doc rot**: still says
   "registry yaml loader + **5 hard fail-fast checks** ... Semantic
   checks **C1, C2, C3, C4** (unchanged from MVP)". The five-check
   count predates C6/C7 (now seven), and stage 4 should list C6 and
   C7 alongside C1-C4. The `validate()` body's inline comment at
   line 314-317 and the per-check docstrings at lines 424 and 445
   compensate, but the loader crate contract at the top lags. Doc
   rot only; code is correct.
2. **`src/main.rs:101-105` stale "MVP accepts only `user` ..."
   comment**: carried over from V1 Concern #2 (pre-existing, not
   introduced by W2, already documented in V1). Code six lines
   below lifts the restriction per P1.
3. **Worker's reported LoC figures differ from actual** (claimed
   `group_restart_e2e.rs = 380 LoC` vs actual 517; claimed
   `restart_cascade_e2e.rs = 430 LoC` vs actual 753). Sloppy
   arithmetic in the final message, not a correctness issue. Both
   files do exist with the claimed tests inside.
4. **Stop-leg timeout is silently swallowed** (`let _ =
   wait_for_phase(...)` at `src/handlers.rs:756`): if a member
   never reaches `Phase::Stopped` within 5s, the group verb
   proceeds to the next member AND marks the member as
   `<sid>_stopped` in `member_order` before start-leg begins.
   Trade-off is documented in the handler docstring ("audit log
   reflects a strict one-by-one sequence") and the test fixture
   uses `sleep infinity` (stop is prompt), so this is acceptable
   for the current scope. A future tightening could log a warn
   when the budget elapses without settling, or surface it in the
   result envelope under a `member_warnings` key.
5. **Cascade error path is `warn!`-only** (`src/handlers.rs:330-337`):
   if a cascade write fails (e.g. converge queue closed), the
   primary op still returns Ok and the only signal is the warn
   log. The docstring at lines 218-244 names the audit trail as
   the operator-visible mechanism for spotting partial cascades,
   so this is documented intent; the cost is that programmatic
   consumers of the response envelope cannot tell a partial
   cascade from a clean one. Acceptable for P2; flag for P5
   dogfood if multi-level cascades are added.
6. **`test05_restart_token_rotated_for_all_members`'s
   `assert_ne!(pre, post)`** is weakly tautological when `pre=None`
   (which is always the case post-Start because stock Start does
   not rotate). The load-bearing assertion is `post.is_some()`
   (proves the custom `write_desired_group_start` rotated) plus the
   pairwise-distinct check at lines 512-514 (proves fresh UUID per
   member). Not a real tautology; could be tightened by
   pre-pinning `pre.is_none()` so the assert_ne symmetry is used
   alongside the positivity pin.

## Hard FAILs

None.

## Time elapsed

~35 minutes from normative reads through verdict dispatch, including
the full serial test gate (63/63 ok) re-executed from a fresh cargo
cache, the six-case synthetic-loader probe (written+run+deleted),
two targeted `--nocapture` audit-capture reruns for PB1 and PB2
evidence, and a complete must-NOT-touch mtime sweep.
