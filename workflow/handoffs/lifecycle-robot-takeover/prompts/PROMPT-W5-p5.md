# PROMPT-W5 — P5 Develop worker (sonnet), real-robot dogfood on SP000065

```
Before doing anything else:
1. Read /home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's classifier and follow every rule
   that applies.
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly the files declared in this prompt. Report every
   file created or modified, with line numbers, in your final message.
If the task directory has a state.md with a ## Blocked section, the listed
file::symbol entries are read-only for you; needing to touch one is an
ESCALATE trigger.

HEAD-guard: before any git touchpoint, run `git log --oneline -1 && git status --short`.

model_selection:
  model: t9s/kimi-k3
  mode: automatic
  reason: deployment_debugging_and_task_decomposition  # P5 = real-robot dogfood; kimi-k3 balanced per workflow.md §Model Selection
```

---

You are **W5 of Lifecycle Robot Takeover P5** — real-robot dogfood on SP000065. P0-P4 closed ACCEPT (V4 clean) at `handoffs/lifecycle-robot-takeover/V4-VERDICT.md`. Test gate baseline: 99/99 serial. reconcile.rs sha256 sentry = `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822` (D-117). P5 = **validate P0-P4 deliverables against real SP000065 (192.168.100.100, user niic)**. P5 is dogfood — configuration + deployment + verification, NOT code change. If a code fix is needed, ESCALATE.

## CRITICAL: NO PARTIAL RETURNS

Your turn ends ONLY when the full output contract below is delivered. DO NOT return a plan, an outline, a status update, or "next I'll ..." announcements. Work continuously until deliverables + test evidence + sha256/sentinel confirmations are all in your final message. If you hit an unrecoverable wall (>5 min on one defect), ESCALATE with exact evidence in your final message.

## Normative reads, in order

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md` — Gawain classifier + hard constraints.
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/lifecycle-robot-takeover/task.md` — Acceptance PA1-PA5 / PB1-PB3 / PC1-PC3 / PD1-PD3.
3. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/lifecycle-robot-takeover/decisions.md` — D-101..D-117 binding. D-101 (roboctl wrap-first), D-102 (dogfood deferred to P5), D-105 (polkit), D-107 (docker exec_start/script), D-108 (oneshot Phase::Completed), D-109 (start_cmd tokio::process), D-110 (pid_file/tmux_session/cmdline_regex mutex), D-111 (HTTP provider schema), D-112 (env_file ${VAR} interp), D-117 (sha256 sentry).
4. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/lifecycle-robot-takeover/V4-VERDICT.md` — P4 close + 4 non-blocking concerns (body drain, Content-Type, user_agent, default_timeout_ms) to keep in mind during dogfood.
5. `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/lifecycle-robot-takeover/prompts/PROMPT-W4-p4.md` — HTTP provider shape template; P5 activates the P4 "commented" shape against real roboctl :8765.
6. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/examples/registry-robot.yaml` — existing topology manifest; P5 derives `registry-sp000065.yaml` from this.
7. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/examples/lifecycle_cli.rs` — CLI client driving zenoh control plane. Used to issue ops during dogfood.
8. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/src/main.rs` — daemon entry; note `Config::from_env` reads `FLEET_ID`/`BOT_NAME`/registry path; daemon connects to zenohd via argo-dds default endpoint.
9. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/src/config.rs` — Config env-var names (especially `REGISTRY_PATH` or whatever the yaml-path env is — verify before relying on it).

## Environment

### Build machine: wangdang (this host, where the prompt runs)

- cwd: `/home/wangdang/work/ai-stack/code/ArgoWatch` (git branch `feat/lifecycle-robot-takeover` already checked out, HEAD = `d2b3b9d`).
- `export PROTOC=/tmp/protoc/bin/protoc` if protoc is not on PATH (check `which protoc` first; install nothing).
- `cargo -p demo-app-lifecycle` only; NEVER `--workspace`.
- Test gate baseline: 99/99 serial (`cargo test -p demo-app-lifecycle -- --test-threads=1`). P5 MUST NOT regress.
- sudo password `wangdang` IF needed for cargo build deps (unlikely — code already built successfully through P4). Do NOT use sudo for anything else.
- HEAD-guard before any git touchpoint: `git log --oneline -1 && git status --short`. HEAD must remain `d2b3b9d` at end of P5.

### Run machine: SP000065 (192.168.100.100, user niic)

SSH path (direct from wangdang, key auth):
```
ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new niic@192.168.100.100 '<cmd>'
```

Known facts (verified 2026-08-18 15:00 local):
- hostname: SP000065, Linux 6.12.55 #23 SMP PREEMPT_DYNAMIC DOVETAIL x86_64, glibc (verify with `ldd --version` if it matters).
- Listening ports: `50053` (argo-gateway mTLS), `192.168.100.100:8765` (roboctl, python3), `127.0.0.1:7447` (zenohd global, loopback only).
- roboctl process: `python3 /home/niic/Downloads/robot-stack/bin/roboctl.pyz --host 192.168.100.100 --port 8765` (PID ~2850, user niic, NOT systemd-managed).
- roboctl config dir: `/home/niic/.config/roboctl/` contains `registry.ini`, `server.ini`, `token` (bearer token file).
- Docker: `localization-robot-1` container running (single container, `docker ps`).
- zenohd processes: `/usr/bin/zenohd -c /etc/argo-zenoh/zenohd-global.json5` (PID ~49771), `/usr/bin/zenohd -c /etc/argo-zenoh/zenohd-local.json5` (PID ~49772). Both run as `argo-ze+` user. zenohd-global listens on `127.0.0.1:7447` (loopback; lifecycle daemon MUST run on SP000065 to reach it).
- argo-gateway-server: PID ~49781, `/usr/local/bin/argo-gateway-server` (running).
- NOT listening on SP000065: `:8090` (rustbot-monitor), `:19090` (robot-service-agent). These were the W4 prompt's hypothetical read-only probe targets; they are not running on SP000065. P5 must NOT assume they exist — verify, and skip/comment out if absent.

### Robot host boundary (HARD — feedback_robot_host_safety)

- **NEVER modify any SP000065 host file**: no `/etc/systemd/system/...`, no `/etc/argo-zenoh/...`, no `~/.config/roboctl/...` content edits, no new docker images pre-built and pushed, no `apt install`, no rust toolchain install on SP000065.
- **NEVER restart SP000065's existing systemd services** (argo-zenoh, argo-gateway-server, roboctl process). The lifecycle daemon you deploy is the only new process you start; you may stop/start/restart it freely.
- **NEVER touch the `localization-robot-1` container's runtime state in a non-reversible way**. `docker stop`/`docker start`/`docker restart` are reversible and acceptable for dogfood; `docker rm`/`docker rename`/config edits are NOT.
- All lifecycle ops you issue must be reversible: `start`/`stop`/`restart` are fine.
- If a fixture install is needed on SP000065 (e.g., test system unit, synthetic 3-service group, test docker image, test process), **ESCALATE rather than install**.
- Sandbox: deploy the lifecycle binary to `/tmp/lifecycle-p5/` on SP000065 (auto-cleaned on reboot). DO NOT install to `/usr/local/bin/` or any persistent location.
- Cleanup: kill the lifecycle daemon and remove `/tmp/lifecycle-p5/` at end of P5 (after evidence collection). Verify no `demo-app-lifecycle` process remains on SP000065.

## SHA256 sentry (D-117)

`src/runtime/reconcile.rs` baseline for P5 = `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822` (D-117, unchanged end-of-P4).

**P5 MUST keep this hash unchanged.** P5 is dogfood — no code changes. If P5 finds a legit reason to touch reconcile.rs (or any src/ file), ESCALATE BEFORE editing — P5 has NO code-change exception granted.

## Deliverables

### 1. SP000065 service inventory — `reports/sp000065-inventory.md` (NEW)

SSH to SP000065 and discover what's actually there. Map each discovered service to a lifecycle selector shape. Cover:

- **systemd units (system + user scope)**:
  - `systemctl list-units --type=service --state=running --no-pager`
  - `systemctl --user list-units --type=service --state=running --no-pager` (run as niic; may be empty)
  - Identify units matching `argo|robo|robot|zenoh|watch|ros|navigation` (candidate lifecycle-managed services).
- **Docker containers**: `docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'`. Note `localization-robot-1`.
- **Listening ports**: `ss -tlnp` (or `netstat -tlnp` if ss unavailable). Map each to a service.
- **Long-running processes**: `ps -ef | grep -E 'argo|roboctl|robot|zenoh|ros|navigation' | grep -v grep`. Identify candidates for process provider selectors (`pgrep` / `pid_file` / `tmux_session` / `cmdline_regex`).
- **roboctl API shape** (the big unknown — P4's W4 prompt assumed `/api/group/robot-stack/restart` but did not verify against a real robot):
  - `curl -sS http://192.168.100.100:8765/` (root; expect 404 or welcome)
  - `curl -sS -H "Authorization: Bearer $(cat /home/niic/.config/roboctl/token)" http://192.168.100.100:8765/api/` (probe API root)
  - Try common paths: `/api/group`, `/api/services`, `/api/health`, `/api/status`, `/api/list`, `/openapi.json`, `/docs`, `/api/group/robot-stack`, `/api/v1/...`. Record every response (status code + body snippet ≤200 chars).
  - If roboctl responds to `GET /api/group` with a list, use it as the source of truth for group names. If not, fall back to reading `/home/niic/.config/roboctl/registry.ini` (read-only — do NOT modify).
  - Document the actual roboctl API endpoints (path, method, expected request body, success codes) for use in the HTTP provider selector.

Output format: a table per category (systemd / docker / ports / processes / roboctl API) with columns: name, current state, lifecycle-selector-shape match (or "no match — comment out").

### 2. SP000065 registry yaml — `examples/registry-sp000065.yaml` (NEW)

Derive from `examples/registry-robot.yaml` but activate ONLY the selector shapes that have a real SP000065 counterpart. Specifically:

- **HTTP provider** (P4, D-111) for roboctl :8765: uncomment the `roboctl-pool` provider with `bearer_token_file: /home/niic/.config/roboctl/token` (real path on SP000065). Configure the `roboctl-robot-stack` service with `restart` (and `start`/`stop` if the API supports them) selector pointing to the real roboctl endpoint discovered in step 1.
- **Docker provider** (P1) for `localization-robot-1`: bind the container as a service. If the container runs an `exec_process` (check `docker inspect localization-robot-1` for the entrypoint), also bind an exec_process service.
- **Systemd provider** (P1, system scope) for any matching `argo-*` or `robot-*` unit. If `argo-gateway-server` is a systemd unit, bind it. If it's a bare process (PID 49781), use the Process provider instead.
- **Process provider** (P3) for `argo-gateway-server` (PID 49781) and `roboctl` (PID 2850): bind each with a `cmdline_regex` selector matching the actual cmdline (verify via `ps -p <PID> -o cmd=`).
- **Systemd user scope** for niic: if any user units are running, bind them. (Likely empty per the prior probe; record that.)
- **Skip / comment out** the `rustbot-monitor` :8090 and `robot-service-agent` :19090 entries (not listening on SP000065).
- **Skip / comment out** the `robot-systemd-system` provider if no real system unit is a safe dogfood target (e.g., if the only candidate is `argo-gateway-server` which is a critical service — restart could break the robot — DO NOT bind it for `restart`, only for `status`).

Add a header comment block:
```yaml
# SP000065 dogfood registry — P5
# Generated from examples/registry-robot.yaml by W5 on 2026-08-18.
# Active selector shapes: <list>
# Skipped shapes (no SP000065 counterpart): <list>
# Hard boundary: feedback_robot_host_safety — no host file modification,
# no irreversible ops. Restart of critical services (argo-gateway-server,
# argo-zenoh) is FORBIDDEN; status-only binds are allowed.
```

### 3. Build & regression on wangdang

- `export PROTOC=/tmp/protoc/bin/protoc` (if needed)
- `cargo build -p demo-app-lifecycle --release --example lifecycle_cli 2>&1 | tail -10`
- `cargo test -p demo-app-lifecycle -- --test-threads=1 2>&1 | tail -20` — must report 99/99 PASS
- `cargo clippy -p demo-app-lifecycle --all-targets -- -D warnings 2>&1 | tail -5` — must be clean
- `sha256sum src/runtime/reconcile.rs` — must equal `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822`
- `git log --oneline -1` — must still be `d2b3b9d`

### 4. Deploy to SP000065

- `ssh niic@192.168.100.100 'mkdir -p /tmp/lifecycle-p5'`
- `scp target/release/demo-app-lifecycle niic@192.168.100.100:/tmp/lifecycle-p5/`
- `scp target/release/examples/lifecycle_cli niic@192.168.100.100:/tmp/lifecycle-p5/`
- `scp examples/registry-sp000065.yaml niic@192.168.100.100:/tmp/lifecycle-p5/registry.yaml`
- Verify deployment: `ssh niic@192.168.100.100 'ls -la /tmp/lifecycle-p5/'`

### 5. Run lifecycle daemon on SP000065

Inspect `src/main.rs` and `src/config.rs` to determine the exact env-var names for: registry path, zenoh endpoint, fleet-id, bot-name. (W2 main.rs comment names `FLEET_ID`/`BOT_NAME`/registry path — verify in config.rs before relying on these names.)

Start the daemon (background, nohup, with explicit env):
```
ssh niic@192.168.100.100 'cd /tmp/lifecycle-p5 && \
  FLEET_ID=dogfoot BOT_NAME=SP000065 \
  <REGISTRY_PATH_ENV>=/tmp/lifecycle-p5/registry.yaml \
  [<ZENOH_ENDPOINT_ENV>=tcp/127.0.0.1:7447 if override needed] \
  RUST_LOG=demo_app_lifecycle=info,argo_dds=info,lifecycle.audit=info \
  nohup ./demo-app-lifecycle > daemon.log 2>&1 & echo $! > daemon.pid'
```

Verify startup:
- `ssh niic@192.168.100.100 'sleep 2 && cat /tmp/lifecycle-p5/daemon.log | head -30'` — look for "zenoh session established" / "registry loaded" / similar.
- If daemon exited early, read daemon.log fully and ESCALATE with the log.

### 6. Execute dogfood test matrix

For each acceptance criterion below, run a real op via `lifecycle_cli` and verify state change on SP000065. Record per-test PASS/FAIL/ESCALATE with evidence.

Template:
```
# Issue op
ssh niic@192.168.100.100 '/tmp/lifecycle-p5/lifecycle_cli \
  --fleet-id dogfoot --bot-name SP000065 \
  --op <OP> --service <SID> --timeout-secs 30 2>&1'

# Verify state change
ssh niic@192.168.100.100 '<verification cmd>'

# Capture audit log line
ssh niic@192.168.100.100 'grep "lifecycle.audit" /tmp/lifecycle-p5/daemon.log | tail -3'
```

Tests (skip any whose fixture is unavailable on SP000065; ESCALATE the skip with reason):

#### PA1 — system scope unit bind + start/stop
- Requires a system-scope systemd unit on SP000065 that can be safely stopped/started.
- Candidates: any `argo-*` unit (but DO NOT restart critical services). If the only safe candidate is `argo-gateway-server`, bind for `status` only and ESCALATE the start/stop portion.
- If NO safe system unit exists, ESCALATE with: "no safe system-scope unit on SP000065 for start/stop dogfood; status-only binds verified for <list>".

#### PA2 — `.target` unit bind
- Requires a `.target` unit on SP000065. Check `systemctl list-units --type=target --state=active`.
- If none relevant, ESCALATE.

#### PA3 — docker exec_process with `exec_start`
- Use `localization-robot-1` container. `docker inspect localization-robot-1` to find its entrypoint/cmd.
- Configure a service with `exec_start: <cmd>` (e.g., `exec_start: "echo hello-from-lifecycle"`).
- Issue `lifecycle.start` on the service. Verify via `docker logs localization-robot-1 --tail 10` that the exec_start cmd ran inside the container.

#### PA4 — env_file `${VAR}` interpolation
- Already verified by P1 unit tests on wangdang (spec_loader.rs). For P5, add a yaml entry with `env_file: /tmp/lifecycle-p5/test.env` containing `TEST_TOKEN=dogfood-value-XYZ` and a selector using `${TEST_TOKEN}` (e.g., HTTP provider header value or exec_start echo).
- Verify the lifecycle daemon's startup log shows the interpolated value (not the literal `${TEST_TOKEN}`).

#### PA5 — no regression
- 99/99 tests pass on wangdang (step 3). MUST PASS.

#### PB1 — group_restart fans out per depends_on topo
- Requires a 3-service synthetic group with `depends_on` chain on SP000065.
- If no such group exists in production, ESCALATE. Do NOT install synthetic fixtures on SP000065.
- Alternative: if `robot-stack` group exists in roboctl's registry, bind it via HTTP provider and issue `lifecycle.group_restart robot-stack`. Verify via roboctl's response that the group op was accepted.

#### PB2 — sudo-beta1.1-release-style dep: container Restart triggers exec_process Start
- The D-115 op-driven cascade. Requires a container with a reverse-dep exec_process service.
- If `localization-robot-1` has a known exec_process dependency (check roboctl's registry.ini or docker-compose), bind both and issue `lifecycle.restart localization-robot-1`. Verify the exec_process service also restarts.
- If no such dependency exists on SP000065, ESCALATE.

#### PB3 — audit lines emitted for each fan-out member
- Verify daemon.log contains `lifecycle.audit` lines for each fan-out op (group_restart members, cascade members). Capture 3+ audit lines as evidence.

#### PC1 — oneshot Type → Phase::Completed
- Requires a `Type=oneshot` systemd unit on SP000065. Check `systemctl list-units --type=oneshot --state=active`.
- If none, ESCALATE.
- If yes, bind it and issue `lifecycle.status` — verify the daemon reports `Phase::Completed` (not `Running`).

#### PC2 — `start_cmd` selector spawns process via tokio::process::Command
- Bind a service with `start_cmd: /bin/sleep 30` (or similar benign cmd).
- Issue `lifecycle.start`. Verify via `pgrep -f "sleep 30"` that the process spawned.
- Issue `lifecycle.stop`. Verify the process is gone.

#### PC3 — `pid_file` / `tmux_session` / `cmdline_regex` mutual exclusion
- For each of the three advanced selectors, find a real SP000065 process to bind:
  - `pid_file`: find a process with a pidfile (e.g., `/var/run/argo-gateway-server.pid` if it exists — check `ls /var/run/*.pid /run/*.pid`). If found, bind a service with `pid_file: <path>` and verify `lifecycle.status` reports `Running`.
  - `tmux_session`: `tmux ls` on SP000065. If a session exists, bind with `tmux_session: <name>`. If no tmux sessions, ESCALATE.
  - `cmdline_regex`: bind `argo-gateway-server` (PID 49781) with `cmdline_regex: "argo-gateway-server"` and verify `lifecycle.status` reports `Running`.
- Each selector demonstrated independently on a real SP000065 process.

#### PD1 — ProviderKind::Http + status via reqwest
- Bind a service with `status.url: http://192.168.100.100:8765/<discovered-status-path>` (use the roboctl API discovery from step 1; if no status endpoint exists, use `status.url: http://192.168.100.100:8765/` and accept that 404 maps to `Phase::Failed` per the http provider contract).
- Issue `lifecycle.status`. Verify the daemon reports a phase + `detail.http_status` matching the actual HTTP response code.

#### PD2 — roboctl-shaped endpoint Bearer + control real HTTP POST
- Bind a service with `restart.url: http://192.168.100.100:8765/api/group/<real-group>/restart` (path from step 1 discovery; method POST; success_codes from actual API behavior).
- Issue `lifecycle.restart`. Verify:
  - `lifecycle_cli` returns success (ControlReceipt Ok).
  - The daemon's audit log records the op.
  - The actual roboctl side effect is observable (e.g., roboctl's own log shows the restart hit, or the group's member services show a recent restart timestamp).

#### PD3 — `bearer_token_file` from real `/home/niic/.config/roboctl/token`
- Verify the lifecycle daemon reads the token file at startup (no Err in daemon.log about token file).
- Verify the token is sent in the Authorization header (roboctl would 401 without it; PD2 success implies PD3, but make the dependency explicit in the report).

### 7. Final dogfood report — `reports/P5-DOGFOOD-REPORT.md` (NEW)

Structure:
1. **SP000065 inventory summary** — counts per category, key services.
2. **Test matrix** — PA1-PA5, PB1-PB3, PC1-PC3, PD1-PD3: per-test verdict (PASS / FAIL / ESCALATE / SKIP), evidence (commands + output snippets + audit log lines).
3. **reconcile.rs sha256** — before/after, must equal D-117 value.
4. **Regression** — `cargo test` count, must be 99/99.
5. **Robot host boundary compliance** — explicit statement that no SP000065 host file was modified, no irreversible op was issued. List every op issued against SP000065 with reversibility confirmation.
6. **ESCALATEs** — every skipped test, every blocker, every judgment call the worker made alone.
7. **Design decisions traded** (≤6 bullets) — e.g., which services to bind for status-only vs full lifecycle, which selectors to skip, choice of cmdline_regex pattern, etc.
8. **Regressions / risks** — anything that could break in production due to P5 dogfood.
9. **Cleanup confirmation** — daemon killed, /tmp/lifecycle-p5/ removed, no `demo-app-lifecycle` process on SP000065.
10. **Elapsed** — wall-clock from normative reads through final report.

### 8. Cleanup

After evidence collection:
- `ssh niic@192.168.100.100 'kill $(cat /tmp/lifecycle-p5/daemon.pid) && rm -rf /tmp/lifecycle-p5'`
- Verify: `ssh niic@192.168.100.100 'pgrep -fa demo-app-lifecycle'` should return empty.

## Hard constraints

- **0 robot host file modification** (HARD boundary; see Robot host boundary above).
- **0 mock / 0 fake** — all tests against real SP000065 services.
- **0 src/ file changes** — P5 is dogfood. If a code fix is needed, ESCALATE.
- **reconcile.rs sha256 must equal D-117 value end-of-P5** (no code changes in P5).
- **0 regression**: existing 99/99 tests pass on wangdang.
- **No git commit / git push**. HEAD must remain `d2b3b9d` at end of P5.
- `.control(` sentinel in `src/runtime/reconcile.rs` must remain 1 (re-verify at end).
- 0 `std::process::Command::new` in `src/` (unchanged from P4; P5 does not touch src/).
- Do NOT touch `src/`, `tests/`, `Cargo.toml`, `Cargo.lock`, `scripts/` (the existing ones).
- HEAD-guard before any git touchpoint.

## Write-set (absolute prefix `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/`)

- `examples/registry-sp000065.yaml` (NEW; real-robot config)
- `reports/sp000065-inventory.md` (NEW; service inventory)
- `reports/P5-DOGFOOD-REPORT.md` (NEW; per-test verdicts + evidence)
- `reports/daemon.log` (NEW; SP000065 daemon log excerpt for audit trail)

NOTHING in `src/`. NOTHING in `Cargo.toml`. NOTHING in `tests/`. NOTHING in `scripts/`.

The `reports/` directory may not exist yet — create it under the crate root.

## Output contract

Your final message to the orchestrator (me) must contain:

1. **Deliverables** — every file created/modified + line ranges + one-line purpose. Grep evidence for the registry-sp000065.yaml active selectors.
2. **Test evidence**:
   - `cargo build -p demo-app-lifecycle --release --example lifecycle_cli 2>&1 | tail -10` on wangdang.
   - `cargo test -p demo-app-lifecycle -- --test-threads=1 2>&1 | tail -20` — must report 99/99 PASS.
   - `cargo clippy -p demo-app-lifecycle --all-targets -- -D warnings 2>&1 | tail -5` — must be clean.
   - Per-test PASS/FAIL/ESCALATE/SKIP with actual command output snippets (lifecycle_cli output + SP000065 state verification + audit log excerpts).
   - `sha256sum src/runtime/reconcile.rs` BEFORE + AFTER — must equal `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822`.
   - `grep -c '\.control(' src/runtime/reconcile.rs` AFTER — must = 1.
   - `git log --oneline -1` AFTER — must be `d2b3b9d`.
3. **Design decisions traded** (≤6 bullets).
4. **Regressions / risks**.
5. **ESCALATEs** (every skipped test, every blocker, every judgment call).
6. **Robot host boundary compliance** — explicit statement + list of ops issued.
7. **Cleanup confirmation** — daemon killed, /tmp/lifecycle-p5/ removed.
8. **Elapsed**.

## Time cap

180 min. Dogfood involves cross-machine SSH + real-robot probing + roboctl API discovery; allow time for discovery + ESCALATE cycles. Single-defect debugging >30 min → ESCALATE.
