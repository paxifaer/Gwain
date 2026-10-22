# PROMPT-E2 — E2 worker for P8 (live E2E + cargo deb packaging) — kimi-k3, 30-min cap

```
Before doing anything else:
1. Read /home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's classifier. Q4=YES (cross-boundary
   zenoh integration) → 必读 agentflow/observability/evidence.md end-to-end
   as the adversarial checklist (8 traceability checks). Also load
   agentflow/observability/{context,events,propagation}.md for cross-ref.
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly 2 files:
   - crates/demo-app-backend/Cargo.toml  (MODIFY — add [package.metadata.deb].assets entry for debian/registry-robot.yaml)
   - crates/demo-app-lifecycle/reports/E2-E2E-REPORT.md  (NEW — E2E + cargo deb report)
   Report every file created/modified with line numbers in your final message.
   Any file outside this list = contract violation.

HEAD-guard: before any git touchpoint, run `git log --oneline -1 && git status --short`.
HEAD MUST remain `d2b3b9d`. NEVER `git add` / `git commit` / `git push`. NEVER AI attribution.

model_selection:
  model: t9s/kimi-k3
  mode: automatic
  reason: verification-and-implementation  # E2 does live E2E + cargo deb extension + writes report
```

---

你是 **E2 worker for P8** — live E2E re-run + cargo deb packaging followup。session-id 见 `prompt.txt`。

**第一步**:Read `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/demo-app-backend-lifecycle-integration/prompts/PROMPT-E2.md` in full(就是本文件)+ 然后执行 Step 1-Step 9。

## CRITICAL: 30-MIN HARD CAP + 2-FILE WRITE-SET

- **Hard time cap: 30 min wall clock**(`timeout -k 5 1800s`)。到点必停,partial report 交付。
- **Write-set 严格 2 个文件**:
  1. `crates/demo-app-backend/Cargo.toml` MODIFY — 扩展 `[package.metadata.deb].assets` 加 `debian/registry-robot.yaml` → `/etc/demo-app-backend/registry.yaml` (mode 0644, user root)
  2. `crates/demo-app-lifecycle/reports/E2-E2E-REPORT.md` NEW — E2E + cargo deb report
- **0 git push / 0 git commit / 0 git add / 0 AI attribution**。
- **0 改动 `demo-app-lifecycle/src/`*** — 严格 0(sha256 sentry 保持 `74b92f34...72b822`)
- **0 改动 `demo-app-lifecycle/examples/lifecycle_cli.rs`** — P7b pre-existing
- **0 改动其他 src/ 文件**(handlers.rs / main.rs / config.rs / observability.rs / frontend / types 都不动)
- **0 改动 `debian/registry-robot.yaml`**(W2 NEW 144L,只往 Cargo.toml 加引用,不改 yaml)
- **HEAD-guard** before any git touchpoint。HEAD 必须保持 `d2b3b9d`。
- **NEVER modify SP000065 host files**(本 task 不涉及 SSH)— local-only。
- **禁止**返回 plan / outline / status update / "next I'll ..."。Work continuously 直到 E2-E2E-REPORT.md 写完 + final message 交付。

## Pre-known facts (inline, do not re-verify)

### W2 implementation (Scheme A accepted mech)
- `demo-app-backend` adds `demo-app-lifecycle` as path dep
- main.rs spawns `Runtime` + observer/converge loops
- handlers.rs `dispatch_action` adds `lifecycle.*` match arms + `to_lifecycle_env` / `from_lifecycle_env` bridge fns at `:400-407` (request) + `:430-437` (response)
- 6 docker fns deleted; `handle_logs_collect` / `handle_robot_status` / `handle_robot_operational` / `query_robot_in_container` preserved
- `debian/registry-robot.yaml` NEW 144L — 8 service_ids, 4 groups (robot-comm / robot-stack-members / robot-oneshot / robot-stack)

### W3 observability schema (V3 ACCEPTED)
- `src/observability.rs` NEW 28L — `log_fail!` macro with 13 canonical fields
- Both FAIL sites use `crate::log_fail!(config, envelope, "request"/"response", "BadEnvelopeBridge", &e, "envelope_bridge")`
- 13 canonical fields: event_kind / run_id / corr / attempt / service / instance_id / caller / callee / op / phase / error_class / error_message / cause
- `GAWAIN_RUN_ID` env wired → `Config.run_id` → `log_fail!` macro
- 3 retired `demo-app-types` consts + `docker_restart_timeout_secs` orphan cleanup

### V3 verdict (D-125, ACCEPT)
- 7 PASS / 1 N-A / 0 FAIL for 8 evidence.md checks
- sha256 sentry `reconcile.rs` = `74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822` ✓
- HEAD `d2b3b9d` ✓
- V3 ESCALATE #1: `handlers.rs:89/196/363` 3 处 pre-existing `.map_err(|e| format!` — out of W3 scope, **flag-for-W4** (NOT E2 scope)
- 6 informational W3 ESCALATEs: #1 flag-for-W4 / #2 ratify (E2 job) / #3 flag-for-W4 / #4 flag-for-W4 / #5 flag-for-W4 / #6 flag-for-W4

### W2 §6 open issues (E2 关闭)
- #1 `lifecycle_cli` E2E re-run against merged process — 7 ops: `lifecycle.start|stop|restart|get_state|list_state|list_groups|group_restart`
- #2 Wildcard race verification — 1 submit → 1 reply (single subscriber, single dispatch)
- #3 `cargo deb` package build — extend `Cargo.toml [package.metadata.deb].assets`
- #7 Live musl binary cargo-deb packaging — `cargo deb --target x86_64-unknown-linux-musl -p demo-app-backend`

### 7 lifecycle.* ops to test
1. `lifecycle.start` — start a service_id (e.g. ping/echo service)
2. `lifecycle.stop` — stop a service_id
3. `lifecycle.restart` — restart a service_id
4. `lifecycle.get_state` — query state of a service_id
5. `lifecycle.list_state` — list state of all service_ids
6. `lifecycle.list_groups` — list groups
7. `lifecycle.group_restart` — restart a group (e.g. robot-stack)

## Task (9 步)

### Step 1: Read normative + W2/W3/V3 deliverables (~3 min)

Read:
- `workflow/bootstrap.md`
- `workflow/agentflow/observability/{README,context,events,propagation,evidence}.md` (8 checks adversarial checklist)
- W2 report: `demo_app_service/crates/demo-app-lifecycle/reports/P8-INTEGRATION-IMPLEMENTATION.md` (§6 open issues — E2 closes #1/#2/#3/#7)
- W3 report: `demo_app_service/crates/demo-app-lifecycle/reports/W3-FOLLOWUP-REPORT.md` (§6 accurate file:line)
- V3 verdict: `demo_app_service/crates/demo-app-lifecycle/reports/V3-VERDICT.md` (ACCEPT — E2 proceeds)
- `demo_app_service/crates/demo-app-lifecycle/examples/lifecycle_cli.rs` (P7b CLI commands — DO NOT MODIFY)
- `demo_app_service/crates/demo-app-backend/Cargo.toml` (current `[package.metadata.deb]` section if exists)
- `demo_app_service/crates/demo-app-backend/debian/registry-robot.yaml` (8 service_ids, 4 groups — for E2E test target)
- `demo_app_service/crates/demo-app-backend/src/main.rs` (lifecycle Runtime asm + topic prefix)

### Step 2: HEAD-guard + verify post-V3 state intact (~1 min)

```bash
cd /home/wangdang/work/ai-stack/code/ArgoWatch
git log --oneline -1   # must be d2b3b9d
git status --short demo_app_service/

# sha256 sentry
sha256sum demo_app_service/crates/demo-app-lifecycle/src/runtime/reconcile.rs
# Must be: 74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822

# Verify post-V3 9-file write-set still intact
ls -la demo_app_service/crates/demo-app-backend/src/observability.rs  # W3 NEW
grep -n "crate::log_fail!" demo_app_service/crates/demo-app-backend/src/handlers.rs  # :400 + :430
```

### Step 3: Build musl binary (~3 min)

```bash
cd /home/wangdang/work/ai-stack/code/ArgoWatch
cargo build --target x86_64-unknown-linux-musl -p demo-app-backend 2>&1 | tee /tmp/e2-musl-build.log
echo "musl build exit: $?"

# Verify binary exists
ls -la target/x86_64-unknown-linux-musl/debug/demo-app-backend
```

If musl build fails, fall back to `cargo build -p demo-app-backend` (debug glibc) — record fallback as ESCALATE.

### Step 4: Start backend process in background (~2 min)

```bash
cd /home/wangdang/work/ai-stack/code/ArgoWatch
export GAWAIN_RUN_ID="e2-$(date +%Y%m%d-%H%M%S)"
export REGISTRY_YAML="/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-backend/debian/registry-robot.yaml"
export BOT_NAME="e2-test-bot"
export ZENOH_TOPIC_PREFIX="demo/e2"
# Other env vars per demo-app-backend.service

BINARY=target/x86_64-unknown-linux-musl/debug/demo-app-backend
[ -x "$BINARY" ] || BINARY=target/debug/demo-app-backend

mkdir -p /tmp/e2
$BINARY 2>&1 | tee /tmp/e2/backend.log &
BACKEND_PID=$!
echo $BACKEND_PID > /tmp/e2/backend.pid
sleep 3
# Verify backend is alive
kill -0 $BACKEND_PID && echo "backend alive: PID=$BACKEND_PID" || echo "backend died — check /tmp/e2/backend.log"
```

If backend fails to start, record as ESCALATE — fall back to running ops via `cargo run -p demo-app-backend` directly.

### Step 5: Run lifecycle_cli with 7 ops (~5 min)

```bash
cd /home/wangdang/work/ai-stack/code/ArgoWatch
# Find lifecycle_cli binary
LIFECYCLE_CLI=$(find target -name 'lifecycle_cli' -type f -executable | head -1)
[ -x "$LIFECYCLE_CLI" ] || cargo build -p demo-app-lifecycle --example lifecycle_cli
LIFECYCLE_CLI=$(find target -name 'lifecycle_cli' -type f -executable | head -1)

# Run 7 ops — adjust topic prefix + service_ids per registry-robot.yaml
# 1. lifecycle.list_groups — list all groups
$LIFECYCLE_CLI --topic-prefix "$ZENOH_TOPIC_PREFIX" list-groups 2>&1 | tee /tmp/e2/op1-list-groups.log

# 2. lifecycle.list_state — list all state
$LIFECYCLE_CLI --topic-prefix "$ZENOH_TOPIC_PREFIX" list-state 2>&1 | tee /tmp/e2/op2-list-state.log

# 3. lifecycle.get_state — get state of one service (e.g. argo-zenoh-global)
$LIFECYCLE_CLI --topic-prefix "$ZENOH_TOPIC_PREFIX" get-state --service-id argo-zenoh-global 2>&1 | tee /tmp/e2/op3-get-state.log

# 4. lifecycle.start — start a service (use a safe systemd-system target)
$LIFECYCLE_CLI --topic-prefix "$ZENOH_TOPIC_PREFIX" start --service-id argo-zenoh-global 2>&1 | tee /tmp/e2/op4-start.log

# 5. lifecycle.stop — stop a service
$LIFECYCLE_CLI --topic-prefix "$ZENOH_TOPIC_PREFIX" stop --service-id argo-zenoh-global 2>&1 | tee /tmp/e2/op5-stop.log

# 6. lifecycle.restart — restart a service
$LIFECYCLE_CLI --topic-prefix "$ZENOH_TOPIC_PREFIX" restart --service-id argo-zenoh-global 2>&1 | tee /tmp/e2/op6-restart.log

# 7. lifecycle.group_restart — restart a group (robot-stack)
$LIFECYCLE_CLI --topic-prefix "$ZENOH_TOPIC_PREFIX" group-restart --group-id robot-stack 2>&1 | tee /tmp/e2/op7-group-restart.log
```

**Read `lifecycle_cli.rs` first** to confirm exact CLI flag names (could be `--topic-prefix` vs `--topic_prefix` vs positional; `--service-id` vs `--service` etc.).

**Verify per op**:
- Exit code 0
- Single `<- reply` (NOT multiple replies — wildcard race gone per W1 §4.1)
- No timeout
- Reply content sane (e.g. list-groups returns 4 groups; list-state returns 8 service_ids)

**Wildcard race check**: for each op, count `result` replies in log:
```bash
for i in 1 2 3 4 5 6 7; do
  echo "=== op$i ==="
  grep -c "result\|reply\|response" /tmp/e2/op${i}-*.log
done
# Expected: 1 per op (single subscriber → single reply)
```

### Step 6: Trigger 1 FAIL event + grep canonical fields (~3 min)

```bash
# Method A: send a bad envelope to backend (e.g. malformed JSON to lifecycle.* topic)
# Method B: stop lifecycle subsystem mid-op (harder)
# Method C: send lifecycle op for non-existent service_id (may or may not trigger BAD_ENVELOPE_BRIDGE)

# Try Method C first — easiest to trigger
$LIFECYCLE_CLI --topic-prefix "$ZENOH_TOPIC_PREFIX" get-state --service-id NON_EXISTENT_SERVICE 2>&1 | tee /tmp/e2/fail-bad-service.log

# Or send raw bad envelope via zenoh publish (use python or zenoh-cli)
# Inspect backend log
grep -n "log_fail\|FAIL\|BAD_ENVELOPE_BRIDGE" /tmp/e2/backend.log | head -20

# If FAIL event captured, verify 13 canonical fields
grep -A2 "event_kind=\"FAIL\"" /tmp/e2/backend.log | head -30

# Verify corr= matches envelope.header.id
grep -o "corr=[a-f0-9-]*" /tmp/e2/backend.log | head -5

# Verify run_id= matches GAWAIN_RUN_ID env
grep -o "run_id=[^, ]*" /tmp/e2/backend.log | head -5
# Expected: run_id=e2-YYYYMMDD-HHMMSS
```

If FAIL event not triggered (e.g. all ops succeed), record as ESCALATE — V3 has already verified canonical fields via static code analysis; E2 live FAIL injection is best-effort.

### Step 7: Extend Cargo.toml [package.metadata.deb].assets (~1 min)

Read `demo-app_service/crates/demo-app-backend/Cargo.toml` first to find current `[package.metadata.deb]` section (or note its absence).

Add asset entry:
```toml
[package.metadata.deb]
# ... existing assets ...
assets = [
    # ... existing entries ...
    # NEW: ship registry-robot.yaml to /etc/demo-app-backend/registry.yaml
    ["debian/registry-robot.yaml", "/etc/demo-app-backend/registry.yaml", "0644"],
]
```

If `[package.metadata.deb]` section doesn't exist, create one per cargo-deb conventions. Preserve existing assets (e.g. demo-app-backend.service, etc).

Verify edit:
```bash
cd /home/wangdang/work/ai-stack/code/ArgoWatch
git diff --stat HEAD -- demo_app_service/crates/demo-app-backend/Cargo.toml
# Expected: 1 file changed, +N insertions (just the new asset line, ~1-3 LoC)
```

### Step 8: Run cargo deb + verify .deb (~5 min)

```bash
cd /home/wangdang/work/ai-stack/code/ArgoWatch

# Check if cargo-deb is installed
which cargo-deb || cargo install cargo-deb --target x86_64-unknown-linux-musl 2>&1 | tee /tmp/e2-cargo-deb-install.log
# (if install needed, use proxy: export https_proxy=http://127.0.0.1:7897 http_proxy=http://127.0.0.1:7897)

# Run cargo deb
cargo deb --target x86_64-unknown-linux-musl -p demo-app-backend 2>&1 | tee /tmp/e2-cargo-deb.log
echo "cargo deb exit: $?"

# Find the .deb
find target/x86_64-unknown-linux-musl/debian -name '*.deb' -type f | tee /tmp/e2-deb-path.txt
DEB_PATH=$(cat /tmp/e2-deb-path.txt | head -1)

# Verify .deb exists
ls -la "$DEB_PATH"

# Inspect .deb contents — verify registry-robot.yaml is included
dpkg-deb -c "$DEB_PATH" | grep -E "registry|demo-app-backend"
# Expected: ./etc/demo-app-backend/registry.yaml entry
```

If cargo-deb install fails (network/proxy), record as ESCALATE — fall back to static Cargo.toml verification only (the asset entry existing is the main proof; the actual .deb build is best-effort).

### Step 9: Stop backend + write E2-E2E-REPORT.md (~4 min)

```bash
# Stop backend
kill $(cat /tmp/e2/backend.pid) 2>/dev/null
sleep 2
# Confirm dead
kill -0 $(cat /tmp/e2/backend.pid) 2>/dev/null && echo "backend still alive" || echo "backend stopped cleanly"
```

Write `demo_app_service/crates/demo-app-lifecycle/reports/E2-E2E-REPORT.md` (~80-150L):

```markdown
# E2 — Live E2E re-run + cargo deb packaging

- **Worker**: E2 (kimi-k3, session <UUID>)
- **HEAD**: `d2b3b9d` (unchanged)
- **Pre-known**: V3 ACCEPT — 7 PASS / 1 N-A / 0 FAIL for 8 evidence.md checks (W3 followup verified)

## §1 7 ops PASS / FAIL

| # | Op | Command | Exit | Reply count | Verdict | Notes |
|---|---|---|---|---|---|---|
| 1 | lifecycle.list_groups | (cmd) | 0/non-0 | N | PASS/FAIL | (notes) |
| 2 | lifecycle.list_state | (cmd) | ... | ... | ... | ... |
| 3 | lifecycle.get_state | ... | ... | ... | ... | ... |
| 4 | lifecycle.start | ... | ... | ... | ... | ... |
| 5 | lifecycle.stop | ... | ... | ... | ... | ... |
| 6 | lifecycle.restart | ... | ... | ... | ... | ... |
| 7 | lifecycle.group_restart | ... | ... | ... | ... | ... |

**Wildcard race**: 1 submit → 1 reply per op = PASS / FAIL (per W1 §4.1)

## §2 FAIL event canonical fields (live log)

- Trigger method: (Method A/B/C)
- FAIL event captured: YES / NO
- 13 canonical fields present (live log): PASS / FAIL / N-A
  - event_kind / run_id / corr / attempt / service / instance_id / caller / callee / op / phase / error_class / error_message / cause
- `corr=` matches `envelope.header.id`: PASS / FAIL / N-A
- `run_id=` matches `GAWAIN_RUN_ID` env: PASS / FAIL / N-A (expected `e2-YYYYMMDD-HHMMSS`)
- Backend log excerpt: (paste relevant lines)

## §3 cargo deb packaging

- Cargo.toml `[package.metadata.deb].assets` extended: PASS / FAIL
  - New entry: `["debian/registry-robot.yaml", "/etc/demo-app-backend/registry.yaml", "0644"]` at Cargo.toml:N
- cargo-deb installed: YES / NO (fallback ESCALATE if NO)
- `cargo deb --target x86_64-unknown-linux-musl -p demo-app-backend` exit: 0 / non-0
- .deb path: target/x86_64-unknown-linux-musl/debian/demo-app-backend_<version>_<arch>.deb
- .deb size: NNNN KB
- .deb contents inspection:
  - `./etc/demo-app-backend/registry.yaml`: PRESENT / ABSENT
  - `./etc/systemd/system/demo-app-backend.service`: PRESENT / ABSENT (if existing)
  - `./usr/bin/demo-app-backend`: PRESENT / ABSENT

## §4 W2 §6 open issues closed

| # | W2 §6 issue | E2 closure | Evidence |
|---|---|---|---|
| 1 | lifecycle_cli E2E re-run 7 ops | CLOSED / ESCALATE | (§1 above) |
| 2 | Wildcard race verification | CLOSED / ESCALATE | (§1 wildcard race row) |
| 3 | cargo deb package build | CLOSED / ESCALATE | (§3 above) |
| 7 | Live musl binary cargo-deb | CLOSED / ESCALATE | (§3 above) |

## §5 Files modified (2-file write-set)

- `demo_app_service/crates/demo-app-backend/Cargo.toml` — +N LoC (add `[package.metadata.deb].assets` entry for `debian/registry-robot.yaml`)
- `demo_app_service/crates/demo-app-lifecycle/reports/E2-E2E-REPORT.md` — ~N LoC (this report, NEW)

## §6 Lifecycle untouched verify

- `git diff --numstat HEAD -- demo_app_service/crates/demo-app-lifecycle/src/`: (must be empty)
- sha256 sentry `reconcile.rs`: (must be `74b92f34...72b822`)

## §7 E2 ESCALATEs (judgment calls E2 made alone)

- (any E2 ESCALATE — e.g. musl build fallback, cargo-deb install failure, FAIL event not triggerable, etc)

## §8 Open issues for V4 / W4

- V4 verifier should adversarial verify §1 (re-run 7 ops if possible) + §3 (cargo deb actually produces .deb with yaml)
- W4 flagged by V3: lifecycle-side run_id / RestartServiceRequest DTO retire / action_to_topic_segment delete / STATE events / custom fmt layer / `.map_err(|e| format!` cleanup at handlers.rs:89/196/363

## §9 Time elapsed

- Step 1 (read normative + W2/W3/V3): ~3 min
- Step 2 (HEAD-guard): ~1 min
- Step 3 (musl build): ~3 min
- Step 4 (start backend): ~2 min
- Step 5 (7 ops): ~5 min
- Step 6 (FAIL event + grep): ~3 min
- Step 7 (Cargo.toml extend): ~1 min
- Step 8 (cargo deb + inspect): ~5 min
- Step 9 (stop + write report): ~4 min
- **Total**: ~27 min / 1800s cap
```

## Output Contract — E2 Final Message

E2 final message 必须包含:
1. **Overall verdict**: SUCCESS / PARTIAL / FAIL
2. **§1 7 ops 速览** — 7 行,每行 PASS/FAIL + reply count + 1 行 note
3. **§2 FAIL event live grep** — canonical fields PASS/FAIL + corr= + run_id= 匹配 env
4. **§3 cargo deb** — Cargo.toml asset entry 加了 + cargo deb exit 0 + .deb 内含 registry-robot.yaml
5. **§4 W2 §6 #1/#2/#3/#7 closure** — 4 行 CLOSED / ESCALATE
6. **§5 2-file write-set** — Cargo.toml +N LoC + E2-E2E-REPORT.md +N LoC
7. **§6 lifecycle untouched** — sha256 sentry 保持 + src/ 0 改动
8. **§7 E2 ESCALATEs** — any judgment calls (musl fallback / cargo-deb install / FAIL not triggered)
9. **Time elapsed** — Xs / 1800s

## Hard constraints (recap)

- **30-min hard cap** (`timeout 1800s`)。partial 到点必停。
- **2-file write-set 严格**:`Cargo.toml` MODIFY + `E2-E2E-REPORT.md` NEW。其他都 0 改动。
- **0 git push / 0 git commit / 0 git add / 0 AI attribution**。
- **0 改动 `demo-app-lifecycle/src/`*** + **0 改动 `lifecycle_cli.rs`** + **0 改动其他 src/ 文件**。
- **HEAD-guard** before any git touchpoint。HEAD 必须保持 `d2b3b9d`。
- **NEVER modify SP000065 host files / services**(local-only)。
- **sha256 sentry 保持** `74b92f34...72b822`。
- **Live process is local** — 不可 SSH 到 robot host(`feedback_robot_host_safety`)。
- **musl build preferred** for dogfood binary per `feedback_musl_target_for_robot_dogfood`(glibc 兼容性)。Fall back to debug glibc build if musl fails — record ESCALATE。
- **cargo-deb install** 如需,用 proxy `http://127.0.0.1:7897`(`user_china_proxy`)。

## Normative reads (8 files, 60s)

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md`
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/README.md`
3. `/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/evidence.md` (8 checks — already V3-verified, E2 reaffirms via live log)
4. `/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/context.md`
5. `/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/events.md`
6. `/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/propagation.md`
7. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/reports/V3-VERDICT.md` (ACCEPT — E2 proceeds)
8. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/reports/P8-INTEGRATION-IMPLEMENTATION.md` (W2 §6 open issues E2 closes)

工作语言:中文为主,关键术语/文件路径保留英文。

现在开始:read 8 normative (60s),HEAD-guard + verify post-V3 (1 min),build musl (3 min),start backend (2 min),7 ops (5 min),FAIL event + grep (3 min),Cargo.toml extend (1 min),cargo deb + inspect (5 min),stop + write report (4 min)。30 min hard cap。
