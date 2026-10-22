# V3 Verdict — Lifecycle Robot Takeover P3

Verdict: **ACCEPT WITH CONCERNS**

Verifier: V3 (adversarial). Every dynamic claim below was re-executed in
the verifier's own shell (uid=abc, unprivileged); nothing is transcribed
from W3's paste. Full serial test log: `/tmp/v3-test-run-full.log`.
Test-count breakdown recomputed by the verifier. sha256 and sentinel
counts re-read from disk after the test gate finished.

## Acceptance criteria

- **PC1 Type=oneshot observed → Phase::Completed + derive_converged
  (Running, Completed)=true + no repeat actuation via C2**:
  PASS — `src/providers/systemd.rs:228-239` `map_oneshot_overlay`
  requires `unit_type == Some("oneshot") && active_state == "active" &&
  sub_state == "exited"` (three-way conjunction) and returns
  `Phase::Completed`; any other input passes through unchanged.
  `.target`-unit tolerance via `read_service_property_str_opt` at
  `systemd.rs:285-315` returns `Ok(None)` on "Unknown interface" from
  D-Bus (verified the substring check on lines 302-304), so `.target`
  skips the overlay without erroring. `src/runtime/reconcile.rs:188`
  carries the single new arm `(RunState::Running, Phase::Completed)` as
  one alternative inside the existing `matches!()` macro, with the
  P3 D-108/D-116 attribution comment inline. W3 did NOT add a
  `(Stopped, Completed) → false` explicit arm — the `_ => false`
  pseudo-catch-all encoded by the exhaustiveness of `matches!()`
  covers it; that is the intention, and `test03_oneshot_converged_true`
  asserts the inverse case via `desired=Running`. Behavioral: ran
  `cargo test -p demo-app-lifecycle --test oneshot_e2e` myself →
  5/5 ok in 3.59s; `systemctl show argowatch-takeover-oneshot.service
  -p ActiveState,SubState,Type,Result,RemainAfterExit` returns
  `active / exited / oneshot / success / yes` — live fixture matches
  the mapped phase exactly. No-repeat-actuation: `test04_oneshot_no_
  repeat_actuation` holds `last_executed_seq` AND `last_op.at`
  constant across OBS_TICK*8 (1.6s ≈ 8 observer ticks) AND keeps
  `conditions.converged=true` over the window. `last_op.at` re-stamp
  is the observable C2 side-effect; holding it constant is a real
  behavioral pin, not a tautology. See Test quality audit below.

- **PC2 `start_cmd` spawns via tokio::process (NOT sh)**: PASS —
  `src/providers/process.rs:571-596` `spawn_start_cmd` uses
  `tokio::process::Command::new(argv0).args(rest)` with
  `Stdio::null()` on stdin/stdout/stderr; vec split on
  `split_whitespace()` after `is_start_cmd_safe` charset-guard
  (`process.rs:206-216`). `Stdio::null()` import is `std::process::
  Stdio` — a Stdio *enum*, NOT a Command (the 0-shell grep for
  `std::process::Command::new` is empty across src/, exit=1).
  ControlOp::Start at `process.rs:647-670` branches Some(cmdline)→
  spawn / None→pre-P3 bail message verbatim. Fingerprint at
  `process.rs:601-614` returns `STATUS | LIFECYCLE` iff `start_cmd`
  is set, else STATUS only. Leaked-child tradeoff is documented at
  the decision site (lines 559-570); chosen because P3's spawn
  targets are long-lived daemons. Behavioral:
  `tests/process_start_cmd_e2e.rs` 6/6 green; test02 spawns an
  argv0-unique link in `/tmp/p3-target-bin/` and asserts
  (a) sysinfo process table shows argv0 live within 5s post-Start,
  (b) provider's own `status()` flips `Phase::Running`, (c) receipt
  `accepted=true`. Test harness verifies via real sysinfo reads —
  not via a string match on internal bookkeeping. No shell-out
  anywhere in src/ — charset explicitly blocks `;&|$><`, test03
  pins two shapes (`/tmp/p3-target; rm -rf /` and
  `/tmp/p3-target;ls`) and both bind-Err naming "shell metachars".

- **PC3 pid_file/tmux_session/cmdline_regex mutual exclusion
  demonstrated on live fixtures**: PASS —
  `src/providers/process.rs:181-191` `MatchStrategy` enum has the
  four variants (`Pgrep(String)` / `PidFile(PathBuf)` /
  `TmuxSession(String)` / `CmdlineRegex(regex::Regex)` — the last
  pre-compiled at bind). Mutual exclusion enforced at
  `process.rs:230-249`: STRATEGY_KEYS constant of size 4, filter
  counts keys present, `!= 1` bails naming both the strategy set
  and the exact conflicting keys. Unknown keys rejected at
  `process.rs:250-259`. Behavioral:
  `tests/process_advanced_selectors_e2e.rs` 5/5 green. test01
  pid_file: real `/bin/sleep infinity` spawn → write
  `/tmp/p3-pidfile-t01.pid` → bound shows `detail.pid` matches live
  pid → kill → Stopped within timeout. test02 tmux_session: real
  `tmux -L <sock> new-session -d -s p3_nav_t02 sleep 60` with
  socket-isolated server (identifiable by unique `-L` socket name
  per-test-pid) → bound shows `detail.tmux_session=p3_nav_t02` +
  `detail.cmdline` contains both "tmux" and the sid → `kill-server`
  → Stopped. test03 cmdline_regex: distinctive `/bin/sleep 999`
  anchored `^/bin/sleep 999$` → Running with cmdline detail match →
  kill → Stopped. test04 sweeps the full 4×4 matrix: zero → Err,
  all-four → Err, every pair → Err, every single-key → Ok,
  every single-key + start_cmd → Ok. test05 pins that `bogus_key`
  is Err naming the offending key. TMUX was present on the host
  (`which tmux` exit 0).

## Hard invariants

- **reconcile.rs sha256 = D-117 value**: PASS —
  `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822`
  computed twice (pre + post full serial gate); exact match to the
  D-117 sentry value.
- **`.control(` sentinel = 1**: PASS — `grep -c '\.control('
  src/runtime/reconcile.rs` returns 1.
- **0 `std::process::Command::new` in src/**: PASS — grep returns
  empty (exit=1). All other `Command::new` hits in src/ are
  `tokio::process::Command::new(argv0)` at `process.rs:576` (D-109
  permitted) plus a docstring reference at `process.rs:129`.
- **0 mock/fake/wiremock/mockall**: PASS — 20 grep hits across
  src/tests/scripts/examples/Cargo.toml are all prohibition-referencing
  comments (testing.md §3 fail-loud citations, D-004 citations). No
  actual mock import or use anywhere.
- **No git commit/push**: PASS — `git log --oneline -1` still
  `43f9c55`; `git status --short` matches V2's closing state exactly
  (workspace Cargo.toml/Cargo.lock `M` from MVP crate registration,
  `crates/demo-app-lifecycle/` untracked). Zero new tracked touches.
- **D-116 scope compliance (only derive_converged edited in
  reconcile.rs)**: PASS — read lines 180-200 of reconcile.rs:
  `derive_converged` at line 183 contains the `matches!()` macro
  with the pre-P3 two alternatives on lines 186-187 (untouched, no
  reformat, no reorder) plus the single new alternative on line 188
  `(RunState::Running, Phase::Completed) // P3 D-108/D-116: oneshot
  ran`. Everything else in the file is bit-identical — `grep -n
  'Completed' src/runtime/reconcile.rs` returns ONE hit (line 188
  only). Line count went 326 → 329 = +3 (comment line + new arm +
  line-continuation). converge_one, boot_observe_into_states,
  converge_loop: all carry pre-existing shape confirmed by reading.

## Lift verification

- **G9 oneshot drift resolved**: PASS — oneshot unit observed at
  `ActiveState=active + SubState=exited` now reports
  `Phase::Completed` instead of the pre-P3 lying `Phase::Running`
  (which let C2 think the unit needed no further action while the
  state plane claimed "currently executing"). `detail` map carries
  the observability pins: `systemd_type=oneshot` +
  `substate=exited` (camelCase `ActiveState`/`SubState`/`LoadState`
  kept for back-compat with system_scope_e2e/systemd_e2e — see
  systemd.rs:373-375). RemainAfterExit=no conservative Stopped
  mapping is documented at systemd.rs:207-223 with the D-Bus
  evidence rationale (busctl-probed 2026-08-18; Result/ExecMain-
  Status are zero-valued whether never-ran or ran-and-deactivated,
  journal is the only reliable discriminator, journal stays
  out-of-scope per D-003). This is the right honest choice — W3
  refused to synthesize a "completed-and-deactivated" phase without
  positive evidence. `derive_converged(Running, Completed)=true`
  closes the converge loop.

- **G11 process Start bail lifted (with start_cmd)**: PASS — when
  `start_cmd` selector key is present, `ControlOp::Start` no longer
  bails; instead `spawn_start_cmd` runs via `tokio::process::
  Command` (native tokio API per D-109). Back-compat: without
  `start_cmd` the original bail message
  `"process provider cannot start; MVP binds Start to systemd/
  docker RestartPolicy — restart via supervising runtime (SPEC
  §4.4)"` is preserved verbatim at `process.rs:666-669`; test06
  pins this substring AND asserts fingerprint stays STATUS-only
  without `start_cmd`. Missing-binary Start surfaces
  `Err` naming the offending argv0 (`Err(anyhow!("spawn '{}': {}
  (argv0='{}'; does the binary exist and is it executable?)", …))`),
  covered by test04. Fingerprint conditional `STATUS|LIFECYCLE`
  when `start_cmd` declared (test05).

- **G12 advanced selectors land**: PASS — `MatchStrategy` enum at
  `process.rs:181-191` with four variants; per-strategy finders
  refactored out of the single `find_first` into `find_first_pid_
  file` (`process.rs:408-…`), `find_first_tmux_session` (line 435),
  `find_first_cmdline_regex` (referenced at line 505 via grep), with
  the legacy `find_first` Pgrep semantics preserved (argv\[0\] strict
  equality — the W4 contract). Regex pre-compiled once at bind time
  (line 313-320) and stored in `MatchStrategy::CmdlineRegex(re)`;
  `regex::Regex::new(...)` failure → bind Err naming the pattern +
  compile error (test03 regex-compile negative case). Mutual
  exclusion across the 4 strategies bind-time-enforced
  (`process.rs:242-249`) with both conflicting key names echoed in
  the Err message; `start_cmd` orthogonal (STRATEGY_KEYS + ORTHO_
  KEYS constants at lines 234-236; ORTHO_KEYS contains only
  `"start_cmd"`). All matching happens in-process via sysinfo — no
  `tmux has-session`, no `pgrep`, no shell grep — confirmed by the
  0-shell grep.

## Test quality audit

- **`oneshot_e2e` actuate-once observable**: NON-tautological.
  test04 asserts `last_executed_seq` and `last_op.at` BOTH frozen
  across OBS_TICK*8 (~1.6s = 8 observer ticks). `last_op.at` is the
  write-side receipt timestamp updated by `converge_one` when it
  actually calls `.control()`; holding it constant is the C2 gate's
  observable hand. A regression that re-fired Start would re-stamp
  `last_op.at` and trip the assertion. Additional window assertion
  `conditions.converged==true` over the same window pins the
  D-116 arm against flip-regressions. The test isn't peeking at
  internal bookkeeping alone: it drives Start through
  `handle_lifecycle_start` (the real handler), waits via the real
  observer loop, and reads the state-plane `st.conditions.last_op`
  — the same data a zenoh GET_STATE client would observe. Strong
  against C2 regression, weak against timestamp-resolution races;
  acceptable given 1.6s dwell.
- **`process_start_cmd_e2e` spawn observable**: NON-tautological.
  test02 spawns an argv0-unique hard-link (per-test-id `p3-target-
  t02`) and asserts via **sysinfo process table** (not via the
  provider's own find_first) that a live process with that argv0
  exists within 5s. Then asserts provider's own `status()` reaches
  Running (cross-validation between sysinfo ground truth and the
  provider's abstracted view). Cleanup via SIGKILL in a Drop guard
  (`FixtureCleanup`), since the musl pause-loop ignores SIGTERM.
  Verified post-run: `pgrep -af 'p3-target'` returns zero hits —
  no leaked fixture processes.
- **`process_advanced_selectors_e2e` mutual exclusion coverage**:
  NON-tautological and exhaustive. test04 sweeps the full 4×4
  matrix: zero → Err, all-four → Err, every pair among 4 → Err,
  every single-key alone → Ok, every single-key + `start_cmd` → Ok.
  Plus test01/02/03 pin a pair-Err each as byproduct of the
  functional path. test05 pins unknown-key rejection naming the
  offending key. Tmux test02 uses isolated `-L <sock>` socket per
  test-pid so concurrent runs don't collide — though
  `--test-threads=1` is the gate anyway.
- **Tautology hunt result**: no tautological tests found. Every
  assertion routes through a real observable (live systemd unit
  via D-Bus, real sysinfo process table, real tmux server, real
  pid file + real kill, real regex engine binding a real cmdline,
  real CaptureBuf for audit pins). Environment-missing paths panic
  with remediation text naming the install script or apt hint
  (`apt install tmux`, `apt install musl-tools`). Zero `#[ignore]`,
  zero silent skip.

## State-plane vs handler-matrix inconsistency

**REAL but W3 documented + bounded.**

- `src/main.rs:438` `restart_ok = matches!(phase, Running | Degraded |
  Stopped | Failed | Completed)` — state plane advertises `restart`
  for a Completed oneshot.
- `src/handlers.rs:53-64` `op_allowed` matrix — `(Restart, Completed)`
  falls into the `_ => false` arm. Preflight at `handlers.rs:80`
  rejects the op with an Err before it ever reaches converge_one.
- Net effect: a zenoh client that GET_STATEs a Completed oneshot sees
  `available_actions = ["restart", "get_state", "list_state"]`, issues
  `lifecycle.restart`, and gets an InvalidArgument envelope. The
  state plane is technically lying about what the handler will
  accept.

W3's mitigation: `main.rs:429-437` carries an inline comment naming
this exact caveat ("the handlers-side op_allowed matrix at
handlers.rs:53-64 is write-set-restricted this P, so a Restart op
issued against a Completed oneshot is still bounced by preflight. The
state plane is deliberately optimistic; reconcile-side RestartUnit
would succeed."). handlers.rs was on W3's MUST-NOT-TOUCH list per
the prompt, and the prompt explicitly instructed W3: "The honest
available action is `restart` (re-fire the oneshot). Update the
matrix accordingly." W3 followed the prompt, documented the
consequence, did not edit handlers.rs (mtime 2026-08-18 12:13, P2-
close, untouched). No ESCALATE was triggered for this because the
prompt's language made the state-plane side binding.

**Judgement**: real but acceptable for P3 close. Two paths forward
for P4 or later:
1. Extend `op_allowed` in `src/handlers.rs` with `(Restart,
   Completed) → true` (1-arm addition mirroring the state plane).
2. Have reconcile-side Start with `desired=Running, phase=Completed`
   map to RestartUnit internally (the systemd.doc says RestartUnit
   on an active(exited) unit re-fires ExecStart). Then a manual
   restart path isn't even needed.

Recommendation: lift (1) in the same PR that lets state-P4 land
(dogfood will hit this).

## Write-set compliance

- **Modified** (P3, authorized):
  - `Cargo.toml` (regex workspace dep added, lines 25-27 comment +
    line 27 `regex = { workspace = true }`).
  - `src/providers/mod.rs` (mtime 12:40, Phase::Completed +
    docstring; 146 lines).
  - `src/providers/systemd.rs` (mtime 12:40, oneshot overlay +
    Service.Type read; 394 lines).
  - `src/providers/process.rs` (mtime 12:47, start_cmd + advanced
    selectors + Start lift + fingerprint; 746 lines).
  - `src/runtime/reconcile.rs` (mtime 12:40, D-116 single arm;
    329 lines).
  - `src/main.rs` (mtime 12:46, compute_available_actions +
    matrix_tests module; 492 lines).
  - `examples/registry-robot.yaml` (header refreshed for P3, P3
    shapes still commented with `P4/P5 will uncomment` notes).
  - `tests/spec_loader.rs` (additive — 2 new tests:
    `loader_process_pid_file_plus_tmux_session_bind_fails` +
    `loader_oneshot_unit_selector_parses_and_binds`; total 16→18).
- **New** (P3, authorized):
  - `scripts/install-p3-oneshot-test.sh` (58 lines, idempotent,
    Requires no pokit change beyond the existing P1 rule).
  - `tests/oneshot_e2e.rs` (485 lines).
  - `tests/process_start_cmd_e2e.rs` (376 lines).
  - `tests/process_advanced_selectors_e2e.rs` (381 lines).
- **Untouched as required** (mtimes pre-P3):
  - `src/handlers.rs` (2026-08-18 12:13, P2-close).
  - `src/envelope.rs`, `src/topic.rs`, `src/config.rs`,
    `src/error.rs` (2026-08-17, MVP-era).
  - `src/spec/schema.rs` (2026-08-18 11:17, P1 W1-write-then-revert
    residue — V1 already audited this; content unchanged from MVP).
  - `src/providers/docker.rs` (2026-08-18 11:22, P1).
  - `src/spec/loader.rs` (P2-era).
  - All 13 pre-existing test files except the additive-declared
    `spec_loader.rs` (mtimes all ≤12:13 P2-close).
- **Cargo.toml/Cargo.lock**: workspace `Cargo.toml` had
  `regex = "1"` already pinned at line 29 (workspace deps section);
  the crate-level `regex = { workspace = true }` inherits
  correctly. `cargo tree -p demo-app-lifecycle -i regex` confirms
  the crate now consumes the workspace regex v1.12.3 alongside
  the pre-existing `prost-build → argo-dds` chain. Cargo.lock
  updated automatically by cargo (allowed under W3's prompt).
- **Out-of-bounds touches**: NONE.

## Concerns (non-blocking)

1. **State-plane vs handler-matrix inconsistency** (see dedicated
   section above). State plane advertises `restart` for Completed
   but handler preflight rejects. W3 knowingly landed this shape
   per prompt direction. Lift in P4 alongside other state-plane
   cleanup.
2. ** `.target`-unit Unit-type probe indirection**: systemd.rs
   `read_service_property_str_opt` parses the D-Bus error message
   to detect "Unknown interface" (lines 300-311). W3 probed this
   live on abc dev; a stricter zbus-shaped check would catch
   `zbus::Error::InterfaceNotFound` typed variants, but the
   substring approach handles both old ("Unknown interface") and
   new ("UnknownInterface") spellings. Cosmetic; function is
   behaviorally correct across both dialects.
3. **Leaked-child tradeoff on `spawn_start_cmd`**: process.rs
   drops the `Child` handle post-spawn. The kernel still SIGCHLDs
   the lifecycle daemon, briefly leaving a zombie until the daemon
   exits. sysinfo reads the zombie with empty argv → observed
   "Stopped". For P3's intended long-lived-daemon use case this is
   irrelevant, but if a future selector wants to start a short-
   lived helper, the visible "Stopped" observer state could be
   misread. Documented at lines 559-570. P5 revisit candidate.
4. **test05_oneshot_available_actions** doesn't directly assert
   `available_actions` on the wire — the state-plane payload is
   built by `publish_state_once` which lives on the binary side
   (main.rs) and requires a zenoh session to reach. test05 pins
   the handler-side `conditions.converged` + `phase` observable
   instead; the matrix is pinned by the two bin-crate unit tests
   at `main.rs:467-491`. Split between lib-e2e + bin-unit is
   deliberate and documented at test05:412-433. Acceptable; the
   combined coverage is non-tautological across the two halves.
5. **`derive_converged` has no explicit `(Stopped, Completed)` arm**:
   the prompt allowed explicitness vs rely-on-catch-all as a W3
   choice; W3 chose to rely on the implicit coverage of `matches!()`
   (no explicit catch-all arm — exhaustiveness completes it). A
   future reader greping for the Stopped/Completed case won't find
   it; comment at main.rs:435 partially addresses this. Additive
   follow-up (not required for P3 close).

## Hard FAILs

None.

## Time elapsed

~28 minutes from normative reads through verdict dispatch,
including full serial test gate executed twice from a fresh test
binary (83/83 ok in both runs), targeted `--nocapture` reruns on
oneshot test02, mtime sweep of all MUST-NOT-TOUCH files, fixture
state verification via `systemctl show` (live active/exited
confirmed), post-test leak probes (`pgrep -af` clean), and live
D-Bus evidence cross-check against `map_oneshot_overlay`
preconditions.
