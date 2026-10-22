# PROMPT-W1 — P1 Develop worker (sonnet),system scope + env_file + docker exec_start + .target

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

You are **W1 of Lifecycle Robot Takeover P1**. Parent MVP (`handoffs/argowatch-mvp-lifecycle/`) is CLOSED ACCEPT. You extend the same crate `demo-app-lifecycle`. Stage P1 = **system scope + env_file interpolation + docker exec_start + .target**.

## Normative reads, in order

1. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/lifecycle-robot-takeover/task.md`
2. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/lifecycle-robot-takeover/decisions.md` — D-101..D-112
3. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/lifecycle-robot-topology-audit/GAP-ANALYSIS.md` — esp. G1, G3, G6, G7, G10 (file:line refs)
4. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/argowatch-mvp-lifecycle/SPEC-mvp.md` — parent contract (esp. §4.2 systemd, §4.3 docker)
5. `/home/abc/work/ai-stack/workflow/Gawain/workflow/handoffs/argowatch-mvp-lifecycle/decisions.md` — D-014 (scope deferred to M5 — this P lifts it), D-015 (env_file deferred — this P lifts it), D-107 (exec_start/exec_script)

## Environment

- `export PROTOC=/tmp/protoc/bin/protoc` before every cargo.
- `cargo -p demo-app-lifecycle` only;never `--workspace`.
- zenohd :7447 (don't touch :17447). `argowatch-test.service` (user-scope) — leave alone.
- **Reconcile sha256 sentry**: BEFORE any code edit, run `sha256sum src/runtime/reconcile.rs` and record. AFTER all edits + tests green, re-hash. **P1 must keep sha256 `43f0155ec5…09d200` unchanged** (D-104). Any change = hard deviation, must ESCALATE.
- sudo available on abc — you'll need it for system unit install. Confirm non-interactively via `sudo -n -v` first; if ECONNREFUSED/permission issue, ESCALATE.
- abc dev; no robot hosts.

## Deliverables

### 1. `src/providers/systemd.rs` — system scope wiring (G1 lift)

- `SystemdProvider::new(scope)` — the `Scope::System => Err("…deferred to M5 (D-014)")` arm gets replaced. The exact error path is GONE.
- Implementation:
  - `Scope::User` → `zbus::Connection::session()` (existing, unchanged)
  - `Scope::System` → `zbus::Connection::system()` (new)
- Document the permission model in module docstring: daemon must either run as root, OR the calling user must hold polkit authorization `org.freedesktop.systemd1.manage-units`. Note that on a default polkit install a non-root user can only manage user-scope units.
- `.target` suffix: relax `unit.ends_with(".service")` validation to also accept `.target` (G10). charset unchanged.

### 2. `src/main.rs` — parse_systemd_scope lift

- `parse_systemd_scope` (`main.rs`:~251) `"system"` arm — change from `bail!` to `Ok(Scope::System)`. Single-line change.

### 3. `src/spec/loader.rs` — env_file `${VAR}` interpolation (D-112)

- Remove the warn-only behavior (D-015 superseded by D-112).
- Implementation: if `meta.env_file = Some(path)`:
  - Load the env file (dotenv-style `KEY=VALUE` lines, `#` comments, no quoting support).
  - Overlay on top of `std::env::vars()`. env file wins on conflict.
  - For every string field in the loaded yaml (services[].id, display_name, group, selector values, provider config JSON strings), do `${VAR}` substitution. Strict: `${VAR}` syntax only. No default values (`${VAR:-default}` is NOT supported), no nested expansion.
  - If a `${VAR}` is referenced but not defined (env or env_file), fail loader with a clear error naming the variable and the file location.
- Keep the existing C1..C4 validation behavior unchanged.

### 4. `src/providers/docker.rs` — `exec_start` / `exec_script` keys (D-107 lifts G6+G7)

- Selector for `exec_process` services now accepts optional keys:
  - `exec_start`: arbitrary command string (e.g. `bash /home/deployuser/NewDeploy/Argo/start_services.sh`). Spaces, slashes, dots, dashes allowed. No leading/trailing whitespace (trim). No newlines.
  - `exec_script`: container-absolute path to a script (e.g. `/home/deployuser/NewDeploy/Argo/start_services.sh`). Validates absolute path (starts with `/`, no `..`, no shell metachars `;&|$` in path).
- Mutually exclusive: both set → Err; either set overrides placeholder `<proc> infinity &`; neither → placeholder (back-compat with W3+W4 tests).
- `exec_process` charset is UNCHANGED for the `exec_process` key itself (still ASCII alnum/`-`/`_`). The relaxation is ONLY for `exec_start`/`exec_script` keys.
- When `exec_start` set: Start cmd = `["sh", "-c", exec_start]`. When `exec_script` set: Start cmd = `["bash", exec_script]`.
- Stop behavior: unchanged (`pkill -TERM -x <proc>`) — the target process name is still `exec_process` (e.g. `argopilot`). `exec_script` is just HOW you launch;the supervised `pgrep` name is separate.

### 5. Tests + scripts

- `scripts/install-takeover-test-unit.sh` (NEW) — installs:
  - `/etc/systemd/system/argowatch-takeover-test.service` (Type=simple, ExecStart=/bin/sleep infinity, no Restart)
  - `/etc/systemd/system/argowatch-takeover-test.target` (a target unit requiring the .service)
  - Followed by `systemctl daemon-reload` + `systemctl enable argowatch-takeover-test.service`
  - Idempotent;document usage
- `tests/system_scope_e2e.rs` (NEW):
  - Test 1 bind System+unit, status ∈ {Stopped, Running}
  - Test 2 handlers start → converged → systemctl is-active (via system bus read, not Command::new) confirms active
  - Test 3 handlers stop → converged → is-active = inactive
  - Test 4 handlers restart → token rotated → active
  - Test 5 `.target` binding: bind argowatch-takeover-test.target,status → derived from member state;start on .target behaves sanely (document semantics in test docstring)
  - Pre-req: script ran;unit exists;**polkit or root**. If `sudo -n true` fails OR zbus system bus StartUnit call returns auth error, test should `panic!` with clear installation note (fail-loud per testing.md §3)
- `tests/docker_exec_script_e2e.rs` (NEW):
  - Test 1: bind container with `exec_process` + `exec_start = "bash /opt/demostart.sh"` where fixture container pre-bakes `/opt/demostart.sh` that spawns a musl binary `demotarget infinity &`
  - Test 2: same shape with `exec_script = "/opt/demostart.sh"` (path-based)
  - Test 3: mutually-exclusive set both → bind returns Err
  - Test 4: `exec_script` relative path → Err
- `tests/env_file_interp.rs` (NEW):
  - Use `tempfile` to create a .env + a yaml with `${VAR}` placeholders in selector value;assert the loader resolves them
  - Test missing `${VAR}` → clear Err naming the variable
  - Test nested `${A${B}}` → Err (unsupported)
- `tests/spec_loader.rs`: pre-authorized additive update:
  - The 5-service yaml will gain system-scope provider example OR a new yaml is added. Pick one pattern and document it;additive-only (keep all existing asserts).
  - Verify `services.len() >= 4` still passes.

### 6. Cargo.toml + Cargo.lock

- No new dependencies expected (zbus already supports system bus, zbus already in deps). If you find needs, ESCALATE.

### 7. yaml

- `examples/registry-mvp.yaml`: **do not change**. The existing MV yaml stays intact.
- NEW `examples/registry-robot.yaml`: full 20-entry shape per GAP-ANALYSIS SPEC §2. All services declared but only those with provider-coverage as of P1 are runnable end-to-end; others document expected selector shape but comment them out at the bottom for P2/P3/P4 to uncomment progressively. Structure: header comment "Coverage as of P1: […]", then services grouped by section (A/B/C/D/independent/oneshot/roboctl-bridge).

## Hard constraints

- **0 Command::new in src/**. zbus/bollard native APIs only. `systemctl daemon-reload` may appear inside `scripts/install-takeover-test-unit.sh` (dev-env script, not src).
- **0 mock / 0 fake / 0 wiremock / 0 mockall** anywhere.
- **`.control(` sentinel stays exactly 1 hit at reconcile.rs:282** (verify before/after).
- **`src/runtime/reconcile.rs` sha256 must equal `43f0155ec5…09d200` end-of-P1** (D-104;P1 不该碰它,所以不变是合理预期)。
- Do not modify `tests/zenoh_e2e.rs`, `tests/systemd_e2e.rs`, `tests/docker_e2e.rs`, `tests/docker_exec_e2e.rs`, `tests/process_e2e.rs`, `tests/group_api.rs` (existing tests untouched).
- `tests/spec_loader.rs` additive-only.
- No git push, no git commit.
- Time cap: 90 min. polkit/auth debugging >30 min → ESCALATE.

## Write-set (absolute prefix `/home/abc/work/ai-stack/code/ArgoWatch/demo_app_service/`)

- `crates/demo-app-lifecycle/Cargo.toml` (probably no-op;confirm)
- `crates/demo-app-lifecycle/src/providers/systemd.rs` (system scope wiring + .target)
- `crates/demo-app-lifecycle/src/main.rs` (parse_systemd_scope one-line lift)
- `crates/demo-app-lifecycle/src/spec/loader.rs` (env_file interpolation)
- `crates/demo-app-lifecycle/src/providers/docker.rs` (exec_start/exec_script)
- `crates/demo-app-lifecycle/src/spec/mod.rs` (may need re-export for interpolation helper if you add one; minimal)
- `crates/demo-app-lifecycle/scripts/install-takeover-test-unit.sh` (NEW)
- `crates/demo-app-lifecycle/tests/system_scope_e2e.rs` (NEW)
- `crates/demo-app-lifecycle/tests/docker_exec_script_e2e.rs` (NEW)
- `crates/demo-app-lifecycle/tests/env_file_interp.rs` (NEW)
- `crates/demo-app-lifecycle/tests/spec_loader.rs` (additive only)
- `crates/demo-app-lifecycle/examples/registry-robot.yaml` (NEW)

NOTHING ELSE. Specifically do NOT touch `src/runtime/`, `src/handlers.rs`, `src/envelope.rs`, `src/topic.rs`, `src/config.rs`, `src/error.rs`, `src/spec/schema.rs`, `src/providers/mod.rs`, `src/providers/process.rs`, `src/providers/http.rs`, `Cargo.lock` will auto-update if Cargo.toml changes.

## Output contract

1. Deliverables (each file mod/created + line ranges;grep evidence for new selector key code)
2. Test evidence:
   - `cargo build -p demo-app-lifecycle 2>&1 | tail -10`
   - `cargo clippy -p demo-app-lifecycle --all-targets -- -D warnings 2>&1 | tail -10`
   - `cargo test -p demo-app-lifecycle -- --test-threads=1 2>&1 | tail -30` (pre-existing 40 + your new;report sum)
   - `systemctl is-active argowatch-takeover-test.service` at a few checkpoints (paste output)
   - `sha256sum src/runtime/reconcile.rs` BEFORE + AFTER (must match)
   - `.control(` grep after edits
3. Permission model provenance:
   - Report: did the new system scope test daemon run as root or via polkit?
   - If polkit: paste the effective policy path tested
   - If root: paste the `sudo` invocation;note that production deployment needs polkit
4. Design decisions traded (≤6 bullets)
5. Regressions / risks
6. ESCALATEs
7. reconcile sha256 BEFORE/AFTER + confirm-unchanged line
8. Elapsed
