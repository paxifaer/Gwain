# PROMPT-W3 — P3 Develop worker (sonnet),oneshot Phase::Completed + process start_cmd + advanced selectors

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

You are **W3 of Lifecycle Robot Takeover P3**. P2 closed ACCEPT WITH CONCERNS at `handoffs/lifecycle-robot-takeover/V2-VERDICT.md` (3/3 PB green, 63/63 serial, sha256 unchanged, D-115 handler-fan-out validated). Stage P3 = **oneshot semantics (`Phase::Completed`) + process provider `start_cmd` selector + process advanced selectors (`pid_file` / `tmux_session` / `cmdline_regex`)**.

## CRITICAL: NO PARTIAL RETURNS

Your turn ends ONLY when the full output contract below is delivered. DO NOT return a plan, an outline, a status update, or a "next I'll ..." announcement. Work continuously until deliverables + test evidence + sha256/sentinel confirmations are all in your final message. If you hit an unrecoverable wall (>5 min stuck on one defect, mutating invariant, missing fixture), ESCALATE with exact evidence in your final message — do not stop quietly.

## Normative reads, in order

1. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/lifecycle-robot-takeover/task.md` — Acceptance PC1/PC2/PC3.
2. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/lifecycle-robot-takeover/decisions.md` — D-101..D-116. **D-108 (oneshot semantics) + D-109 (process start_cmd) + D-110 (advanced selectors mutual exclusion) + D-116 (P3 scoped sha256 exception)** are your binding architectural decisions. Read all four FIRST.
3. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/lifecycle-robot-takeover/V2-VERDICT.md` — what just landed in P2.
4. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/lifecycle-robot-topology-audit/GAP-ANALYSIS.md` — **G9 (oneshot drift), G11 (process Start bail), G12 (advanced selectors)** — the three gaps P3 lifts.
5. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/argowatch-mvp-lifecycle/SPEC-mvp.md` §3 (Phase enum + derive_converged semantic space) and §4.5 (process provider fingerprint contract).
6. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/argowatch-mvp-lifecycle/decisions.md` — D-020 (FeatureSet fingerprint), D-021 (process provider STATUS-only), D-025 (prompt template).

## Environment

- `export PROTOC=/tmp/protoc/bin/protoc` before every cargo.
- `cargo -p demo-app-lifecycle` only; NEVER `--workspace`.
- Test gate: `cargo test -p demo-app-lifecycle -- --test-threads=1`.
- zenohd :7447 live test bus; `:17447` NOT yours.
- abc dev; no robot hosts.
- sudo password available: `abc123` (pattern: `echo "abc123" | sudo -S -p "" <cmd>`). Needed to install oneshot test unit.
- Pre-existing fixtures (leave alone): `argowatch-test.service`, `argowatch-takeover-test.{service,target}`, `argowatch-p2-{a,b,c}.service`, docker image `argowatch-takeover-p1-bash:local`.
- musl-gcc at `/usr/bin/musl-gcc` for any static fixtures.

## SHA256 sentry (D-104 + D-116)

`src/runtime/reconcile.rs` baseline = `43f0155ec54357520c7b87fc7b90a3632b88e7999254c162a10e4b033d09d200`.

**D-116 grants P3 a SCOPED exception**: you may modify `src/runtime/reconcile.rs` ONLY inside `fn derive_converged` (currently at line 183) — a single match-arm addition for `(RunState::Running, Phase::Completed) → true` (and the mirror arm if you judge `(RunState::Stopped, Phase::Completed) → false` needs explicitness over the catch-all). The rest of reconcile.rs must remain **bit-identical** outside `derive_converged`'s body.

Before your edit: sha256 = `43f0155ec5…09d200`. After your edit: compute the new hash and report it. The new hash becomes the new baseline for P4 (recorded in decisions.md by the orchestrator at P3 close).

If you find yourself needing to touch ANY OTHER part of reconcile.rs, ESCALATE — do NOT expand the exception unilaterally. `converge_one` logic, especially C2 actuate-once gate at ~`reconcile.rs:222-270`, is OFF LIMITS this P.

## Deliverables

### 1. `src/providers/mod.rs` — Phase enum extension (D-108)

The `Phase` enum is at `src/providers/mod.rs:49`. Add the `Completed` variant:

```rust
pub enum Phase {
    // existing variants — preserve order (D-108: "不动现有 enum 顺序")
    ...
    Completed,  // new; oneshot ran to completion (active(exit) / SubState=exited)
}
```

Position: append AFTER all existing variants (preserve existing variant order — serde compatibility). Add a brief docstring (≤3 lines) referencing D-108 and the original mapper that produces it.

Update any exhaustive matches on `Phase` in the codebase. `derive_converged` is one site; `compute_available_actions` in `src/main.rs:410-436` is another. Search for other consumers with `grep -rn "Phase::" src/ | grep -v "//"`. For each non-reconcile site:
- In `compute_available_actions`: `Phase::Completed` should NOT push `start` (it's not "stopped; can start" — the op already ran). The honest available action is `restart` (re-fire the oneshot). Update the matrix accordingly.
- Any other match: prefer adding the `Completed` arm explicitly (no catch-all that accidentally treats it as Stopped).

### 2. `src/providers/systemd.rs` — map `Type=oneshot` + `SubState=exited` to `Phase::Completed`

The systemd `map_state` flow currently maps `ActiveState=active → Running`, `inactive → Stopped`. Read GAP-ANALYSIS G9 for the exact problem.

Implementation:
1. In `SystemdBoundService::status` (or whichever status function owns `map_state`), additionally query the `Type` property on the `org.freedesktop.systemd1.Unit` interface (path already constant at `:70`).
2. When `Type=oneshot` AND `ActiveState=active` AND `SubState=exited`: return `Phase::Completed` (instead of `Phase::Running`).
3. When `Type=oneshot` AND `ActiveState=inactive` (RemainAfterExit=no, completed and deactivated): ALSO return `Phase::Completed` if we have positive evidence the unit ran (consult `ExecMainStatus == 0` or `Result=success` via the same interface). If the unit never ran, return `Phase::Stopped` as before. ESCALATE if distinguishing "never ran" from "ran and deactivated" proves ambiguous without journal access; document the actual signal you used.
4. All other `Type` values (simple, forking, notify, etc.): unchanged mapping.
5. `detail` map: include `"systemd_type" = "<Type>"` and `"substate" = "<SubState>"` for observability.

### 3. `src/runtime/reconcile.rs` — SINGLE-ARM extension inside `derive_converged` only (D-116)

Inside `fn derive_converged`:

```rust
fn derive_converged(desired: RunState, phase: Phase) -> bool {
    match (desired, phase) {
        // existing arms — PRESERVE EXACTLY
        ...
        (RunState::Running, Phase::Completed) => true,   // D-116 single-arm addition
        // maybe (RunState::Stopped, Phase::Completed) => false — explicitness choice; document
        _ => false,
    }
}
```

Rules:
- Preserve every existing match arm byte-for-byte (incl. comments).
- Add the new arm BEFORE any `_ =>` catch-all.
- Do not reformat, reorder, or "clean up" other arms.
- The new arm must be the ONLY body change in this file.
- Run `sha256sum` BEFORE (record) and AFTER (must be some new hash; report it). Verify the diff is exactly the arm addition via `git diff src/runtime/reconcile.rs`.

### 4. C2 actuate-once gate on `Phase::Completed` — READ-ONLY verification, NO code change

Per task.md PC1: "no repeated actuation via C2". Walk the code path: when phase becomes `Completed` with desired=Running, C2's logic at `reconcile.rs:222-270` must not re-actuate (that's the PC1 acceptance). You likely don't need to change anything — C2 keys on `seq > last_executed_seq OR restart_token ≠ last_executed_token`, NOT on phase. Verify by reading C2 + writing a test that shows: a oneshot service, once it reaches `Phase::Completed`, does not produce another `.control(` call on subsequent converge passes after the initial actuation.

If reading C2 convinces you that re-actuation WILL occur (i.e., a rare drift condition exists where the gate doesn't catch up), ESCALATE before touching anything — the fix may need a different shape than you imagine.

### 5. `src/providers/process.rs` — `start_cmd` selector (D-109) + Start lift

#### 5a. Selector schema extension

Currently `process.rs:88-110` validates `pgrep` as the ONLY selector. Add `start_cmd` as an OPTIONAL co-key:

- Selector map now accepts: `{ pgrep: <name> }` (existing) OR `{ pgrep: <name>, start_cmd: <cmdline> }`.
- `start_cmd` value: full commandline as a single string. Charset per D-109: ASCII alnum + `-` + `_` + `.` + `/` + ` ` (space separates argv tokens). NO shell metachars `;&|$><` etc.
- Spawn implementation: **NOT sh, NOT system(), NOT fork+execvp**. Use `tokio::process::Command`:
  ```rust
  let argv: Vec<&str> = cmdline.split_whitespace().collect();
  let mut cmd = tokio::process::Command::new(argv[0]);
  cmd.args(&argv[1..]);
  // IMPORTANT: spawn detached (no parent-child lifetime coupling)
  // std::process::Stdio::null() for stdin/stdout/stderr
  let _child = cmd.stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null()).spawn()?;
  // intentionally leaked; we don't keep a handle
  ```
  D-109 says: "仍属 '原生 API' (D-003 兼容）". `tokio::process::Command` is a native tokio API — same phylogeny as zbus/bollard. Document this in the code.
- The selector remains OBSERVABLE via `pgrep` — i.e., we spawn the process, then later status() reads via `pgrep` — the existing fingerprint and converged logic still applies.

#### 5b. Lift `ControlOp::Start` bail

At `process.rs:229-232`: `ControlOp::Start => bail!("process provider cannot start; MVP binds Start to systemd/docker RestartPolicy …")`. Replace:

- If `start_cmd` is SET: spawn via the mechanism in 5a.
- If `start_cmd` is NOT set: keep the existing bail.

#### 5c. Fingerprint extension

`FeatureSet::STATUS` at line 205 becomes conditional:
- If selector has `start_cmd`: return `FeatureSet::STATUS | FeatureSet::LIFECYCLE` (or however the enum composition works — follow FeatureSet's API).
- Otherwise: keep `FeatureSet::STATUS`.

This way status-only process services keep their read-only contract; only services that declared a `start_cmd` unlock the Start verb. Stop/Restart keep their existing semantics (SIGTERM→grace→SIGKILL).

### 6. `src/providers/process.rs` — advanced selectors `pid_file` / `tmux_session` / `cmdline_regex` (D-110)

Add three NEW selector keys, mutually exclusive with `pgrep` AND with each other. Exactly one of the four match strategies must be present:

| Key | Value shape | Match strategy | Example |
|---|---|---|---|
| `pgrep` (existing) | ASCII alnum/`-`/`_` (existing charset) | argv[0] strict equality against `p.cmd().first()` (existing) | `pgrep: tmux` |
| `pid_file` | absolute path to a file containing a single integer pid (e.g. `/run/myapp.pid`) | read file → parse pid → look up via sysinfo `Process::pid()` — process matches if pid exists AND is alive | `pid_file: /run/myapp.pid` |
| `tmux_session` | session name, ASCII alnum/`-`/`_` | find processes whose `cmdline` starts with `tmux` AND contains `-S` or `new-session -s <name>` — most pragmatically: any tmux client/server whose argv contains `-s <name>` or `=<name>` | `tmux_session: nav_stack` |
| `cmdline_regex` | regex string (crate `regex` is already in workspace deps) | any process whose full cmdline matches the pattern | `cmdline_regex: "^emacs --daemon"` |

Mutual exclusion rules (D-110):
- Exactly ONE of `pgrep` / `pid_file` / `tmux_session` / `cmdline_regex` must be set.
- Multiple set → bind Err naming the conflicting keys.
- Zero set → bind Err (unchanged behavior; previously required pgrep).

Additional selector key `start_cmd` is orthogonal and may co-occur with any of the four match strategies.

Implementation notes:
- Factor the match logic out of `find_first` so each strategy has its own fn. `find_first` becomes a dispatcher over strategy enum.
- For `pid_file`: if file unreadable or pid not alive → treat as "no match" (not Err). This enables clean drift detection after soft-kill.
- For `tmux_session`: match against the FULL cmdline, not just argv[0]. Document that this is a heuristic; provider should NOT shell out to `tmux has-session` (0 shell).
- For `cmdline_regex`: pre-compile the regex once in `bind()`, store `Regex` in the bound struct. Regex parse failure → bind Err.
- The 0-shell rule: do NOT run `tmux`, `pgrep`, `grep`, etc. via subprocess. All matching happens in-process via sysinfo.

### 7. `examples/registry-robot.yaml` — document P3 shapes

Add to the robot yaml (commented out, since these are P5 dogfood targets):

```yaml
# P3 shapes (uncomment for P5 dogfood):
# - service: ethercat
#   provider: { instance: main-systemd-system, selector: { unit: ethercat.service } }
#   # oneshot: will be reported Phase::Completed after run; available_actions=[restart]
# - service: navigation_v2
#   provider: { instance: main-process, selector: { tmux_session: nav_stack, start_cmd: "/path/to/nav_launch.sh" } }
```

Header comment refresh: "P3 adds: oneshot Phase::Completed + process start_cmd + advanced selectors".

### 8. Tests

#### `tests/oneshot_e2e.rs` (NEW)

Fixture: install a new system unit `argowatch-takeover-oneshot.service`:
```ini
[Unit]
Description=ArgoWatch P3 Oneshot Test

[Service]
Type=oneshot
ExecStart=/bin/true
RemainAfterExit=yes
```

Install via `scripts/install-p3-oneshot-test.sh` (NEW, idempotent). Use sudo (root install).

Tests:
1. **test01_oneshot_initial_state_stopped**: before any op, phase=Stopped (or Completed if previously run — read code to decide).
2. **test02_oneshot_start_converges_completed**: Start → phase becomes Completed (within timeout). Assert `detail["systemd_type"] == "oneshot"`.
3. **test03_oneshot_converged_true**: `converged` flag = true when phase=Completed + desired=Running.
4. **test04_oneshot_no_repeat_actuation**: after convergence, wait 3 converge ticks (e.g., 2-3 seconds); assert `.control(` was called EXACTLY ONCE total. Use tracing CaptureBuf and grep `control` invocations; or use a verifyable state signal like `last_executed_seq` staying constant.
5. **test05_oneshot_available_actions**: GET_STATE on a completed oneshot should show `available_actions` containing `restart`, NOT `start`. (Or whatever the new matrix dictates — assert that.)

#### `tests/process_start_cmd_e2e.rs` (NEW)

Use a host-musl binary again (like docker_exec_e2e does). Compile a static `p3-target` binary that loops. Place it at `/tmp/p3-target` (via `install -m 0755`).

Tests:
1. **test01_bind_with_start_cmd**: selector `{ pgrep: p3-target, start_cmd: "/tmp/p3-target" }` binds successfully.
2. **test02_start_cmd_actually_spawns**: Start op → `pgrep -x p3-target` matches a live process. Verify via sysinfo or `cat /proc/<pid>/cmdline` — NO shelling out to pgrep from the crate (the test harness can use std::process::Command to run `pgrep` since tests are not src/).
3. **test03_start_cmd_charset_rejection**: `{ start_cmd: "/tmp/p3-target; rm -rf /" }` → bind Err (shell metachar).
4. **test04_start_cmd_missing_binary**: `{ start_cmd: "/tmp/does-not-exist" }` → Start op returns Err (or phase goes to Failed — assert whichever you implement).
5. **test05_fingerprint_lifecycle_unlocked**: the bound service's fingerprint includes LIFECYCLE.
6. **test06_no_start_cmd_start_bails**: selector WITHOUT `start_cmd` → Start op returns the pre-P3 bail error (back-compat).

#### `tests/process_advanced_selectors_e2e.rs` (NEW)

Three test shapes, one per selector strategy:

1. **test01_pid_file_selector**: 
   - Setup: launch `sleep infinity` via harness `std::process::Command`, capture pid, write to `/tmp/p3-pidfile.pid`.
   - Bind service with `{ pid_file: "/tmp/p3-pidfile.pid" }` → Status returns Running.
   - Kill the process → Status returns Stopped.
   - Mutual exclusion: also set `pgrep: ...` in the same selector → bind Err naming both.

2. **test02_tmux_session_selector**:
   - Setup: spawn `tmux new-session -d -s p3_nav_stack sleep 60` via harness.
   - Bind service with `{ tmux_session: "p3_nav_stack" }` → Status returns Running (target process matched).
   - Kill the tmux session (`tmux kill-session -t p3_nav_stack`) → Status returns Stopped.
   - Mutual exclusion evidence.

3. **test03_cmdline_regex_selector**:
   - Setup: spawn a process with distinctive cmdline, e.g. `/bin/sleep 999` with arbitrary arg order.
   - Bind with `{ cmdline_regex: "^/bin/sleep 999$" }` → Status returns Running.
   - Kill it → Status returns Stopped.
   - Mutual exclusion evidence.

Prereq: `tmux` must be installed on the box. Verify with `which tmux`. If absent, ESCALATE before skipping test02 — do not silently mark it ignored.

#### `tests/spec_loader.rs` — additive tests

- One test asserting a registry with `pid_file` + `tmux_session` both set → bind fails.
- One test asserting a registry yaml with `{ unit: argowatch-takeover-oneshot.service }` parses (stays green).
- Or fold these into the e2e files if more natural — additive only either way.

## Hard constraints

- **0 `Command::new` in `src/`** — `tokio::process::Command` is allowed (D-109; native tokio API). `std::process::Command` in TESTS is allowed (test harness, not src/).
- **0 mock / 0 fake / 0 wiremock / 0 mockall** anywhere.
- **`.control(` sentinel exactly 1 hit at `src/runtime/reconcile.rs`** — re-verify before + after.
- **reconcile.rs edit boundary (D-116)**: ONLY inside `fn derive_converged`. Nothing else in that file.
- `converge_one`, `boot_observe_into_states`, `main converge_loop`, C2 gate: OFF LIMITS this P.
- Do NOT touch: `src/handlers.rs` (P2 just landed; only touch if you discover an interaction bug and ESCALATE first), `src/envelope.rs`, `src/topic.rs`, `src/config.rs`, `src/error.rs`, `src/spec/schema.rs` (unless a tiny Phase addendum is needed; ESCALATE first), `src/providers/docker.rs`, `src/providers/http.rs`, `src/providers/systemd.rs` unless for oneshot status mapping.
- Do NOT touch existing tests: `tests/zenoh_e2e.rs`, `tests/systemd_e2e.rs`, `tests/docker_e2e.rs`, `tests/docker_exec_e2e.rs`, `tests/docker_exec_script_e2e.rs`, `tests/process_e2e.rs`, `tests/group_api.rs`, `tests/system_scope_e2e.rs`, `tests/env_file_interp.rs`, `tests/group_restart_e2e.rs`, `tests/restart_cascade_e2e.rs`. `tests/spec_loader.rs` additive-only.
- No git commit, no git push.

## Write-set (absolute prefix `/home/abc/work/ai-stack/code/ArgoWatch/demo_app_service/`)

- `crates/demo-app-lifecycle/Cargo.toml` (add `regex` if not already a dep; otherwise no-op)
- `crates/demo-app-lifecycle/src/providers/mod.rs` (Phase::Completed variant + docstring)
- `crates/demo-app-lifecycle/src/providers/systemd.rs` (oneshot Type property read + Completed mapping)
- `crates/demo-app-lifecycle/src/providers/process.rs` (start_cmd + advanced selectors + Start lift + fingerprint)
- `crates/demo-app-lifecycle/src/runtime/reconcile.rs` (ONLY derive_converged single-arm addition — D-116)
- `crates/demo-app-lifecycle/src/main.rs` (compute_available_actions Matrix extension for Completed; possibly nothing else)
- `crates/demo-app-lifecycle/src/spec/mod.rs` (only if a re-export is truly required)
- `crates/demo-app-lifecycle/scripts/install-p3-oneshot-test.sh` (NEW)
- `crates/demo-app-lifecycle/tests/oneshot_e2e.rs` (NEW)
- `crates/demo-app-lifecycle/tests/process_start_cmd_e2e.rs` (NEW)
- `crates/demo-app-lifecycle/tests/process_advanced_selectors_e2e.rs` (NEW)
- `crates/demo-app-lifecycle/tests/spec_loader.rs` (additive only)
- `crates/demo-app-lifecycle/examples/registry-robot.yaml` (P3 shapes commented + header refresh)

NOTHING ELSE.

## Output contract

1. **Deliverables** — every file created/modified + line ranges + one-line purpose. Grep evidence for: `Phase::Completed`, `start_cmd`, `pid_file`/`tmux_session`/`cmdline_regex` tokenizer code.
2. **Test evidence**:
   - `cargo build -p demo-app-lifecycle 2>&1 | tail -10`
   - `cargo clippy -p demo-app-lifecycle --all-targets -- -D warnings 2>&1 | tail -10`
   - `cargo test -p demo-app-lifecycle -- --test-threads=1 2>&1 | tail -50` — report pass/total. Pre-P3 = 63. P3 target = 63 + ~11-15 = 74-78.
   - `systemctl status argowatch-takeover-oneshot.service` at checkpoints
   - For each new e2e test: observable evidence (sysinfo output for process state, audit line for oneshot Completed, etc.)
3. **sha256 BEFORE + AFTER for `src/runtime/reconcile.rs`** — record both. The diff should be EXACTLY ONE match arm addition in `derive_converged`. Paste the `git diff` for reconcile.rs.
4. **`.control(` sentinel count** AFTER (`grep -c '\.control(' src/runtime/reconcile.rs` must = 1).
5. **Design decisions traded** (≤6 bullets) — esp.:
   - How you distinguished "oneshot ran and deactivated" from "oneshot never ran" (RemainAfterExit=no case)
   - Whether `start_cmd` spawn retains Child handle or intentionally drops it
   - How `pid_file` handles pid reuse (e.g. pid file stale pid now belongs to a different process)
6. **Regressions / risks**.
7. **ESCALATEs** (if any) — evidence + decision you need.
8. **New sha256 for reconcile.rs** — becomes new P4 baseline.
9. **Elapsed**.

## Time cap

120 min. Three independent deliverable clusters; expect the process provider rework to dominate. Single-defect debugging >30 min → ESCALATE.
