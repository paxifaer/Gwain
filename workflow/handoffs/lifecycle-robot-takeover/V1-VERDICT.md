# V1 Verdict — Lifecycle Robot Takeover P1

Verdict: **ACCEPT WITH CONCERNS**

Verifier: V1 (adversarial). All dynamic evidence below was reproduced in the
verifier's own shell (uid=abc, unprivileged), not transcribed from W's paste.
Full log: `/tmp/v1-test-run.log`.

## Acceptance criteria

- **PA1 system scope bind+start/stop**: PASS — `src/providers/systemd.rs:107-116`
  `Scope::System` arm calls `zbus::Connection::system()` (the old
  `Err("system scope deferred to M5 (D-014)")` arm is gone);
  `src/main.rs:258` `parse_systemd_scope` `"system" => Ok(Scope::System)`.
  Dynamic: `tests/system_scope_e2e` 5/5 green in my shell, driving real
  StartUnit/StopUnit/RestartUnit against `argowatch-takeover-test.service`
  (fixture confirmed installed at `/etc/systemd/system/`, Main PID observed
  via independent `systemctl status`).
- **PA2 .target bind**: PASS — `systemd.rs:154-159` accepts `.service` or
  `.target` with dual-mention error text. `system_scope_e2e::test05` binds
  `argowatch-takeover-test.target` (Requires= the .service), status maps,
  Start accepted. `.target` unit independently confirmed `Active: active`
  via systemctl.
- **PA3 docker exec_start**: PASS — `docker.rs:134-145` mutual exclusion
  before validation; `252-294` validators (trim/no-newline for exec_start;
  absolute/no-`..`/no `;&|$` for exec_script); `605-623` three-shape argv
  dispatch (placeholder only when both absent). Dynamic: 4/4 green in
  `docker_exec_script_e2e` — real container `argowatch-takeover-p1-bash:local`,
  real musl `demotarget` compiled+injected at test time, `pgrep -x demotarget`
  drives the Running assertion, Stop pkills back to Stopped. Both
  exec_start(`bash /opt/demostart.sh`) and exec_script(`/opt/demostart.sh`)
  exercised end-to-end; negative tests pin mutual-exclusion and
  relative-path Errs.
- **PA4 env_file interp real**: PASS — `loader.rs:48-107` env_file overlay
  (file wins over `std::env::vars()`), relative path resolved against yaml
  dir (`:52-60`), hard-Err on load failure with warn emitted first (pinned
  substring "meta.env_file declared" preserved); `256-307` strict `${VAR}`
  (nested/default/empty/invalid/undefined all Err). Warn-only D-015 path
  replaced, not shadowed. Dynamic: `env_file_interp` 3/3 (happy path with
  tempfile pair + yaml-anchored relative env_file; missing-var Err naming
  `MISSING_VAR`; nested `${OUTER${INNER}}` Err despite both names defined).
- **PA5 no regression (40 MVP baseline)**: PASS — arithmetic verified from
  my own run: MVP 40 = lib 3 + main 0 + docker_e2e 4 + docker_exec_e2e 4 +
  group_api 2 + process_e2e 5 + spec_loader 12 + systemd_e2e 4 + zenoh_e2e 6.
  P1 retirements/changes: zenoh_e2e test06 deleted (D-113), test05 rewritten
  (D-113), spec_loader `loader_env_file_warn_is_actually_emitted` converted
  warn→warn+Err (D-114) + 1 additive positive (`registry_robot_loads`).
  New: system_scope 5 + docker_exec_script 4 + env_file_interp 3 + robot 1
  = 13. 40 − 1 + 13 = **52/52 ok, 0 failed, 0 ignored** across 12 binaries
  (3+0+4+4+4+3+2+5+13+5+4+5).

## Hard invariants

- **sha256 reconcile.rs unchanged**: PASS —
  `43f0155ec54357520c7b87fc7b90a3632b88e7999254c162a10e4b033d09d200`
  (exact match to D-104 sentry; file mtime Aug 17 15:49, untouched by P1).
- **`.control(` sentinel 1**: PASS — `grep -c` returns exactly 1.
- **0 Command::new in src/**: PASS — empty grep (exit 1). `Command::new`
  appears only in tests (musl-gcc/bash spawn) and the two dev scripts,
  which is permitted (rule binds `src/` only).
- **0 mock/fake/wiremock/mockall**: PASS — all 10 grep hits are comments
  referencing the prohibition (testing.md §3 fail-loud rationale,
  reconcile.rs mock-clock note). No double anywhere.
- **No git commit/push**: PASS — HEAD still `43f9c55`; whole crate is
  untracked MVP-era state; workspace Cargo.toml/lock diffs are the MVP
  crate-registration, untouched by P1 (mtimes Aug 17 18:17).

## G-gap lifts

- **G1 systemd system scope**: PASS — `Scope::System` → `Connection::system()`
  (static) + `pkcheck --action-id org.freedesktop.systemd1.manage-units` →
  `result=yes` from unprivileged shell + 5/5 system_scope_e2e green without
  sudo (behavioral). Real system bus, real Manage-units calls.
- **G3 env_file interp**: PASS — loader stage-3 implemented exactly per
  D-112 (overlay + strict `${VAR}` + hard-Err); 3/3 env_file_interp green.
  Also feeds the P4 token-injection prerequisite.
- **G6 exec_start freed**: PASS — `ShellLine` override reaches
  `["sh","-c","bash /opt/demostart.sh"]` and drives a real scripted start
  in a live container (test01).
- **G7 exec charset relaxed (via exec_start)**: PASS — `bash
  /opt/demostart.sh` (space + slash + dot) binds and executes; the strict
  alnum/-/_ charset on the `exec_process` key itself is unchanged
  (D-107 scopes the relaxation to the two new keys).
- **G10 .target suffix**: PASS — bind accepts `.target`; live
  `argowatch-takeover-test.target` bound + status + Start in test05.

## Test quality audit

- **system_scope_e2e (real-systemd evidence)**: NON-tautological. Calls
  the crate's real `SystemdProvider::new(Scope::System)` → zbus system
  bus; binds the on-disk fixture unit; exercises Start/Stop/Restart and
  re-reads `ActiveState`/`LoadState`/`SubState` via LoadUnit+Get from the
  live daemon. Fail-loud panics name the install script and polkit action
  (testing.md §3 compliant). test01 cross-checks detail `ActiveState`
  against the mapped Phase (mapping consistency, not just Ok-return).
  Weakness noted under Concerns (#4): test05's post-Start acceptance set
  is broad.
- **docker_exec_script_e2e (real-container evidence)**: NON-tautological.
  Fresh container per test from a bash-enabled derivative image; C source
  compiled by musl-gcc at test time, base64-injected via exec;
  `demostart.sh` injected with a documented argv[0]/comm load-bearing
  PATH trick (empirically derived — evidence of real debugging, cited as
  W1-resume finding). Running assertion = `pgrep -x demotarget` exit 0 in
  the live container via the provider's own status path. Cleanup via
  catch_unwind + container removal. Tests 3/4 are pure-selector negatives
  (no fixture) — appropriate for bind-shape Errs.
- **env_file_interp (tempfile evidence)**: NON-tautological. Real tempfile
  TempDir + File I/O; asserts the *loaded Registry's selector value* equals
  the interpolated string (`argowatch-takeover-test.service`), which the
  yaml alone cannot produce. Missing/nested tests assert Err content.
  ENV_LOCK mutex held per [[feedback_env_var_test_lock]].
- **zenoh_e2e test05 (D-113)**: real binary spawn with `scope: system`
  registry, alive-after-3s + reverse pin that stderr lacks "system scope
  deferred to M5"; early-exit path dumps captured stdout/stderr on
  failure. Matches D-113's authorized shape exactly. test06 absent (only
  a historical comment remains).
- **spec_loader D-114 conversion**: warn capture (CaptureBuf fan-in)
  asserts "meta.env_file declared" substring AND `load_from_str` Err
  naming the path + `meta.env_file` — both pins intact, no tautology.
- No silenced/skipped/deleted tests beyond D-113-authorized test06
  retirement; `0 ignored` across the whole suite.

## Write-set compliance

- Modified (P1, authorized): `src/main.rs`, `src/providers/systemd.rs`,
  `src/providers/docker.rs`, `src/spec/loader.rs`, `src/spec/mod.rs`
  (minimal doc refresh), `tests/spec_loader.rs` (additive + D-114 test),
  `tests/zenoh_e2e.rs` (D-113 scope only).
- New (authorized): `scripts/install-takeover-test-unit.sh`,
  `scripts/ensure-takeover-bash-image.sh`, `tests/system_scope_e2e.rs`,
  `tests/docker_exec_script_e2e.rs`, `tests/env_file_interp.rs`,
  `examples/registry-robot.yaml` (18 services, 3 providers, 5 groups —
  matches SPEC §2 manifest; P-later entries commented).
- **Out-of-write-set touches: NONE.** All MUST-NOT-TOUCH files carry
  pre-P1 mtimes (Aug 17): `src/runtime/*`, `src/handlers.rs`,
  `src/envelope.rs`, `src/topic.rs`, `src/config.rs`, `src/error.rs`,
  `src/providers/mod.rs`, `src/providers/process.rs`,
  `tests/{docker_e2e,docker_exec_e2e,process_e2e,group_api,systemd_e2e}.rs`,
  `examples/registry-mvp.yaml`, `Cargo.toml` (no-op confirmed — dev-deps
  tempfile+base64 both predate P1; base64 introduced by W4's
  docker_exec_e2e).
- `src/spec/schema.rs` mtime is Aug 18 11:17 (W1 wrote, W1-resume
  reverted). Content verified line-by-line against SPEC-mvp §3.1: closed
  3-variant ProviderKind, plain `Meta.env_file`, all
  `deny_unknown_fields`, `is_mvp_supported` intact. Revert is real at the
  content level; mtime movement is process residue only.

## Permission model

- Provenance: **(b) polkit rule active** — verified firsthand:
  - `/etc/polkit-1/rules.d/49-argowatch-lifecycle.rules` (root:root 644,
    written Aug 18 11:52): grants `org.freedesktop.systemd1.manage-units`
    to `subject.user == "abc"` unconditionally (no active-session clause).
  - `pkcheck --action-id org.freedesktop.systemd1.manage-units --process $$`
    → `polkit\56result=yes`, exit 0, from the verifier's unprivileged shell.
  - `cargo test` ran as uid=abc (no sudo anywhere); system_scope_e2e 5/5
    green ⇒ the zbus system-bus manage-units calls were authorized by this
    rule (abc is non-root; polkit is the only grant path).
- Recommendation for prod robot deployment: ship an equivalent
  `/etc/polkit-1/rules.d/*.rules` for the daemon's runtime user (optionally
  tightening with `subject.local == true` / active-session guards), OR run
  the daemon as root. Polkit is the preferred shape per D-105; document
  the rule file alongside the unit-install script at deploy time. Note the
  current rule grants ALL manage-units ops to abc with no unit filter —
  acceptable on a dev box, should be scoped per-unit or
  per-prefix on robots if polkit's limited expressiveness allows, else
  accept full manage-units for the daemon user.

## Concerns (even though ACCEPT)

1. **`systemd.rs:274` hardcodes `detail["scope"]="user"`** in
   `SystemdBoundService::status()` — the state plane will report
   `scope: user` for system-scope binds. Cosmetic lie; scope is not
   threaded into the bound struct. Recommend P-later threads `Scope` into
   `SystemdBoundService` and emits the true value.
2. **`main.rs:~101-104` stale factory comment**: still says *"Per D-014 /
   SPEC §4.2, MVP accepts only `"user"`. `"system"` fails startup with a
   clear error naming the deferred milestone."* — directly contradicts the
   lifted `parse_systemd_scope` six lines below. Doc rot only; code is
   correct.
3. **`zenoh_e2e.rs:42-44` header inventory rot**: still frames the
   D-014/D-015 side rails as "startup failure paths ... non-zero exit",
   while test05 is now a positive boot test and test06 is retired. The
   inline D-113 comment block at ~476-485 compensates but the header lags.
4. **system_scope_e2e test05 post-Start assertion is broad**
   (`Running|Stopped|Starting`): G10's load-bearing pin (bind acceptance)
   is real, but a fixture-backed member-state assertion (Requires=
   ride-along ⇒ `.service` active) would tighten it. Also: the suite
   leaves the takeover `.service` running on exit (test05's Start);
   harmless for a sleep-infinity fixture, but a teardown Stop would be
   cleaner hygiene.
5. **schema.rs mtime moved** despite full content revert (see Write-set
   above) — noted for audit-trail completeness, not a defect.

## Hard FAILs

None.
