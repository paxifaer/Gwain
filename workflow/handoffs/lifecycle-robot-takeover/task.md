# task.md — Lifecycle Robot Takeover (P0-P6)

## Goal

Extend `demo-app-lifecycle` so that a single yaml declares **all 20 robot-topology entries** (per `/handoffs/lifecycle-robot-topology-audit/GAP-ANALYSIS.md` SPEC §2), and any lifecycle op on any entry is achievable by yaml edit + zenoh command **without code change**. Phase P0-P4 = code; P5 = robot dogfood (deferred, needs user-picked host); P6 = acceptance + takeover decision.

## Scope split (code phases)

| Phase | Gap | Deliverable |
|---|---|---|
| P1 | G1 + G3 + G6 + G7 + G10 | system scope + token/env_file interpolation + docker exec_start/exec_script + .target suffix |
| P2 | G4 + G5 + G8 | new action `lifecycle.group_restart` + depends_on topological consume + container→exec_process dependency chain |
| P3 | G9 + G11 + G12 | oneshot semantics (`Phase::Completed` or detail flag) + process `start_cmd` + process advanced selectors (`pid_file` / `tmux_session` / `cmdline_regex`) |
| P4 | G2 | new provider kind `http` (reqwest) for roboctl :8765 + read-only HTTP probes |

## Default decisions (user said "go", questions unanswered)

- **roboctl stance**: wrap first (P4 HTTP provider), native group verb in P2 stands alone. A 组 group_restart uses native topo in P2; roboctl remains available as an out-of-band channel via P4 provider once it exists.
- **dogfood host**: out of P0-P4 scope. Robot dogfood deferred to P5 — user picks host then.
- **Cadence**: auto through P0→P4 (each P closes with V ACCEPT, then next P starts). P5+ pauses for user.

## Hard user constraints (verbatim carry-over from MVP)

- 测试坚决不mock (D-004 of MVP)
- 0 shell in src/ — zbus/bollard/sysinfo/libc::kill/reqwest only;no `systemctl|docker|pgrep|pkill|sh -c|bash -c` via `Command::new` in `src/`
- Orchestrator Plan/Dispatch/Judge only (Gawain workflow.md 铁律)
- test gate stays `--test-threads=1` (V3-A4 attribution)
- reconcile.rs sha256 sentry: hash before, hash after each phase, report deviation explicitly
- No robot host modification ([[feedback_robot_host_safety]]);only abc dev machine during P0-P4

## Acceptance (12+ new per phase)

Inherited from MVP task.md Acceptance 1-12, plus per-phase:

P1:
- PA1 system scope unit bind+start/stop on a real system unit (sudo-installed test unit)
- PA2 `.target` unit bind works
- PA3 docker exec_process with selector `exec_start` runs an actual script
- PA4 env_file `${VAR}` interpolated for a token;the old warn removed;new test asserts interpolation result
- PA5 no regression: existing 40 tests still pass

P2:
- PB1 group_restart fans out per `depends_on` topo (start forward, stop reverse) against a 3-service synthetic group
- PB2 sudo-beta1.1-release-style dep: container Restart triggers exec_process Start
- PB3 Audit lines emitted for each fan-out member with op source = group verb

P3:
- PC1 Type=oneshot unit observed → `Phase::Completed` (or equivalent);derive_converged true for (Running, Completed);no repeated actuation via C2
- PC2 `start_cmd` selector spawns the process via native API (tokio::process::Command, NOT sh)
- PC3 `pid_file` / `tmux_session` / `cmdline_regex` mutually-exclusive selectors each demonstrated on a live fixture

P4:
- PD1 ProviderKind::Http + `http.rs` bind + status via reqwest;fixture is a real `python3 -m http.server`-style minimal HTTP daemon with a stub JSON endpoint (real HTTP traffic, NOT a Mock impl)
- PD2 roboctl-shaped endpoint （授 Bearer) 通过 HTTP provider bind + control → real HTTP POST 真到 stub
- PD3 `~/.config/roboctl/token` 模式 fixture (`bearer_token_env`) 真从 env/file 读到 token 注入 header

## Worker route

P1 W+V → P2 W+V → P3 W+V → P4 W+V → 停，等用户决定是否进 P5 (robot dogfood)。

## Reference documents

- Parent: `handoffs/argowatch-mvp-lifecycle/` (SPEC-mvp.md + decisions.md D-001..D-025 + evaluation.md)
- Gap: `handoffs/lifecycle-robot-topology-audit/GAP-ANALYSIS.md` (20 entries + G1..G12 + file:line)
- Topology: user's 2026-08-18 message (§0-§8 service inventory)
- Prompt template rules: D-025 + [[feedback_gawain_prompt_template]]

## Environment invariants

- abc dev machine only (no robot hosts)
- zenohd :7447 (do not touch :17447)
- `argowatch-test.service` user unit still installed (MVP fixture; leave alone)
- `PROTOC=/tmp/protoc/bin/protoc` for all cargo
- `cargo -p demo-app-lifecycle` only
- sudo available for system-unit work;ask via ESCALATE if a prompt needs a new sudo capability not yet granted
- musl-gcc `/usr/bin/musl-gcc` for docker_exec fixture
