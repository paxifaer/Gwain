# PROMPT-V2 — V2 verifier for W2 demo-app-backend ↔ demo-app-lifecycle integration (kimi-k3, adversarial)

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
4. Your write-set is exactly 1 file:
   - crates/demo-app-lifecycle/reports/V2-VERDICT.md  (NEW — verifier verdict)
   Report every file created with line numbers in your final message.
   Any file outside this list = contract violation.

HEAD-guard: before any git touchpoint, run `git log --oneline -1 && git status --short`.
HEAD MUST remain `d2b3b9d`. NEVER `git add` / `git commit` / `git push`. NEVER AI attribution.

model_selection:
  model: t9s/kimi-k3
  mode: automatic
  reason: verification  # adversarial verifier — kimi-k3 balanced per workflow.md
```

---

You are **V2 verifier for W2 of demo-app-backend ↔ demo-app-lifecycle integration**。W2 (session `0bf41e22-f060-4337-ab16-166ecd13acbe`, glm-5.2, ~6.5 min wall clock) 完成 Scheme A implementation + 4 ESCALATE self-resolution + 7-file write-set + P8-INTEGRATION-IMPLEMENTATION.md report。

**你的 mandate 是 disprove, NOT confirm**。Find evidence that each W2 claim is false。Adversarial framing kills confirmation bias per workflow.md §Verification。

## CRITICAL: 15-MIN HARD CAP + 0 CODE MODIFICATION

- **Hard time cap: 15 min wall clock**(`timeout -k 5 900s`)。到点必停,partial verdict 交付。
- **0 code modification** — V2 是 verifier,只读 + 写 verdict report。NEVER Edit / Write(除 V2-VERDICT.md)/ NotebookEdit / `git add` / `git commit`。
- **0 改动任何 src/ 文件**(demo-app-backend 和 demo-app-lifecycle 都不动)。
- **0 改动 `lifecycle_cli.rs`**(P7b pre-existing,W2 不碰,V2 也不碰)。
- **Write-set 严格 1 个文件**:`crates/demo-app-lifecycle/reports/V2-VERDICT.md`。
- **NEVER** `git push`。**NEVER** AI attribution。
- **HEAD-guard** before any git touchpoint。HEAD 必须保持 `d2b3b9d`。
- **NEVER** modify SP000065 host files / services(本 task 不涉及 SSH)。
- **禁止**返回 plan / outline / status update / "next I'll ..."。Work continuously 直到 V2-VERDICT.md 写完 + final message 交付。

## Pre-known facts (inline, do not re-verify)

### W2 final message claims (to disprove)

**§1 改动文件清单**(W2 claimed 7 files):
1. `crates/demo-app-backend/Cargo.toml` MODIFY +1 dep line (`demo-app-lifecycle = { path = "../demo-app-lifecycle" }`)
2. `crates/demo-app-backend/src/config.rs` MODIFY +6 (`registry_yaml: String` field + env read)
3. `crates/demo-app-backend/src/main.rs` MODIFY +73 (Runtime asm + spawn + parse_systemd_scope helper + rename rt→reply_topic)
4. `crates/demo-app-backend/src/handlers.rs` MODIFY +40/-255 (lifecycle.* arms + delete 6 docker fns)
5. `crates/demo-app-backend/debian/demo-app-backend.service` MODIFY +1 (`Environment=REGISTRY_YAML=...`)
6. `crates/demo-app-backend/debian/registry-robot.yaml` NEW 144L
7. `crates/demo-app-lifecycle/reports/P8-INTEGRATION-IMPLEMENTATION.md` NEW ~165L

**Net code diff (excl new yaml + report) claimed**: +81/-255
**Git diff stat (from waiter)**: `5 files changed, 239 insertions(+), 331 deletions(-)`
**⚠️ DISCREPANCY**: W2's per-file LoC (+81/-255) does NOT match git diff stat (+239/-331). V2 MUST investigate.

**§2 build results claimed**:
- `cargo check -p demo-app-backend` exit 0
- `cargo build -p demo-app-backend` (debug) exit 0, 35.4s
- `cargo build --target x86_64-unknown-linux-musl -p demo-app-backend` exit 0, 1m35s
- `cargo clippy -p demo-app-backend --no-deps` exit 0, 2 warnings (1 dead_code `docker_restart_timeout_secs`, 1 pre-existing `clippy::double_ended_iterator_last` at handlers.rs:357)

**§3 ESCALATEs claimed**:
- #1 Legacy callers: RETIRE — grep 6 sibling repos, 0 live zenoh-publish caller, hits are const defns + doc comment + unit test + smoke test. Conservative preserve `query_robot_in_container` (grep didn't cover `robot.*` actions).
- #2 Misnomered `start_service`: silently delete (no alias needed).
- #3 Registry yaml: port P5 `registry-sp000065.yaml` + add `robot-stack` group. 8 service_ids, 4 groups, 3 providers.
- #4 Priority: P8 standalone (already decided).

**§4 Preserve/delete list claimed**:
- Deleted 6 fns: `handle_restart_service` / `restart_container` / `exec_in_container` / `handle_start_service` / `handle_stop_service` / `stop_container`
- Preserved 4 fns + 2 handlers: `handle_logs_collect` + `collect_logs` + `handle_robot_status` + `handle_robot_operational` + `query_robot_in_container` + simple handlers (ping/echo/status/query_device)

**§5 Observability claimed**:
- FAIL `BAD_ENVELOPE_BRIDGE` at `handlers.rs:385-393` (`to_lifecycle_env` Err path), phase=request
- FAIL `BAD_ENVELOPE_BRIDGE` at `handlers.rs:428-436` (`from_lifecycle_env` Err path), phase=response (final_failure)
- STATE `lifecycle.audit` already in lifecycle (not added by W2) at `demo-app-lifecycle/src/handlers.rs:166-177`
- Cause preservation via `format!("{e:#}")`
- Correlation propagation via `Envelope.header.id` (UUID v4) preserved through bridge

**§6 Open issues / V2 验证项**(W2 listed 7 + 1 self-ESCALATE):
1. Lifecycle_cli E2E re-run against merged process (V2 job — requires live daemon)
2. Wildcard race verification (V2 job — requires live process)
3. `cargo deb` package build (Cargo.toml [package.metadata.deb].assets NOT extended — V2 followup)
4. `docker_restart_timeout_secs` orphan cleanup (V2 cleanup)
5. `query_robot_in_container` retirement (V2 decision)
6. `demo-app-types` action constants unused (V2 cleanup)
7. Live musl binary cargo-deb (V2 step)
8. **W2 self-ESCALATE**: `Cargo.lock` auto-updated by cargo (side-effect of dep add, outside W2 write-set). Orchestrator ratification requested.

**W2 ESCALATE to orchestrator**:
1. `Cargo.lock` write-set violation (unavoidable cargo behavior)
2. Conservative preserve of `query_robot_in_container` (W1 §6 listed as delete target, W2 deviated)
3. musl build PASS (W1 ESCALATE #7 resolved)
4. P8 priority (already decided)

## Task (5 步)

### Step 1: Read normative + W2 deliverables (~2 min)

Read:
- `workflow/bootstrap.md`
- `workflow/agentflow/observability/{README,context,events,propagation,evidence}.md` (8 checks adversarial checklist)
- W2 final message: extract from `/home/wangdang/work/ai-stack/logs/w2-demo-backend-lifecycle/waiter.out` (lines 17-149)
- W2 P8 report: `demo_app_service/crates/demo-app-lifecycle/reports/P8-INTEGRATION-IMPLEMENTATION.md` (165L)
- W1 report: `demo_app_service/crates/demo-app-lifecycle/reports/RESEARCH-DEMO-BACKEND-LIFECYCLE-INTEGRATION.md` (235L, for Scheme A spec cross-ref)

### Step 2: Verify W2 §1 改动文件清单 (write-set + LoC) (~3 min)

```bash
cd /home/wangdang/work/ai-stack/code/ArgoWatch
git log --oneline -1   # must be d2b3b9d
git status --short demo_app_service/crates/demo-app-backend/ demo_app_service/crates/demo-app-lifecycle/
git diff --stat HEAD -- demo_app_service/crates/demo-app-backend/
git diff --stat HEAD -- demo_app_service/crates/demo-app-lifecycle/src/ demo_app_service/crates/demo-app-lifecycle/examples/
```

**Disprove checks**:
- [ ] 5 modified files match W2's claimed 5? (Cargo.toml, config.rs, main.rs, handlers.rs, demo-app-backend.service)
- [ ] 2 new files match? (debian/registry-robot.yaml, reports/P8-INTEGRATION-IMPLEMENTATION.md)
- [ ] `demo-app-lifecycle/src/` 0 changes? (sha256 sentry verify)
- [ ] `demo-app-lifecycle/examples/lifecycle_cli.rs` is P7b pre-existing 38L diff (NOT from W2)?
- [ ] `Cargo.lock` modified? (W2 self-ESCALATE — verify it's a 1-line package entry addition)
- [ ] Per-file LoC: W2 claimed `Cargo.toml +1, config.rs +6, main.rs +73, handlers.rs +40/-255, service +1`. Run `git diff --numstat HEAD -- <each file>` and compare actual ±LoC to claimed. Flag any discrepancy >±5 LoC.
- [ ] **KEY**: W2 claimed net +81/-255 but git stat says +239/-331. Trace this discrepancy: run `git diff --numstat HEAD` per file, build actual table, compare to W2's §1 table. Identify which file's LoC was mis-reported.

```bash
# sha256 sentry
sha256sum demo_app_service/crates/demo-app-lifecycle/src/runtime/reconcile.rs
# Must be: 74b92f343aa265638e9c9cf79fb69a602978ea1177b2ebc0ff5a68272f72b822
```

### Step 3: Re-run builds + verify W2 §2 build results (~4 min)

**Re-run all builds, do NOT trust W2's claimed exit codes**:

```bash
cd /home/wangdang/work/ai-stack/code/ArgoWatch

# 1. cargo check
cargo check -p demo-app-backend 2>&1 | tee /tmp/v2-check.log
echo "check exit: $?"

# 2. cargo build (debug)
cargo build -p demo-app-backend 2>&1 | tee /tmp/v2-build.log
echo "build exit: $?"

# 3. cargo build musl
cargo build --target x86_64-unknown-linux-musl -p demo-app-backend 2>&1 | tee /tmp/v2-musl.log
echo "musl exit: $?"

# 4. cargo clippy (best-effort)
cargo clippy -p demo-app-backend --no-deps 2>&1 | tee /tmp/v2-clippy.log
echo "clippy exit: $?"
```

**Disprove checks**:
- [ ] cargo check exit 0? (W2 claimed 0)
- [ ] cargo build exit 0? (W2 claimed 0, 35.4s)
- [ ] cargo build --target x86_64-unknown-linux-musl exit 0? (W2 claimed 0, 1m35s, W1 ESCALATE #7 PASS)
- [ ] cargo clippy exit 0? (W2 claimed 0, 2 warnings — verify which warnings)
- [ ] Any new warnings W2 didn't report? (compare /tmp/v2-*.log warning count to W2 §2)

**Bypass vector**: W2 could have fabricated exit codes. Re-running is the countermeasure.

### Step 4: Verify W2 §3-§5 (ESCALATEs + observability + preserve/delete) (~4 min)

#### ESCALATE #1 — Legacy callers (re-run grep)

```bash
# Reproduce W2's grep across 6 sibling repos
for repo in ArgoWatch ArgoGateway ArgoDeploy argopilot argopilottools ArgoDDS; do
  echo "=== $repo ==="
  grep -rn "restart_service\|start_service\|stop_service" "/home/wangdang/work/ai-stack/code/$repo/" 2>/dev/null | grep -v "target/" | grep -v ".git/" | head -20
done
```

**Disprove checks**:
- [ ] Did W2's reported caller hits match? (W2 listed: ArgoWatch const defns + doc + test + smoke; ArgoGateway 0; ArgoDeploy bash script; argopilot bash script; argopilottools 0; ArgoDDS 0)
- [ ] Did W2 miss any LIVE zenoh-publish caller? (search for `.publish.*restart_service` or `action: "restart_service"` patterns — actual publish sites, not just string matches)
- [ ] Is W2's RETIRE decision defensible given grep evidence?

#### ESCALATE #2 — Misnomered `start_service`

```bash
# Verify handle_start_service was actually deleted (not aliased)
grep -n "handle_start_service" demo_app_service/crates/demo-app-backend/src/handlers.rs
# Expected: 0 hits (deleted)
grep -n "start_service" demo_app_service/crates/demo-app-backend/src/handlers.rs
# Expected: 0 hits in dispatch table (retired)
```

**Disprove checks**:
- [ ] `handle_start_service` actually deleted? (0 hits)
- [ ] `start_service` action string absent from dispatch table?
- [ ] No alias forwarder added? (W2 claimed no alias)

#### ESCALATE #3 — Registry yaml

```bash
# Verify registry-robot.yaml exists with claimed content
wc -l demo_app_service/crates/demo-app-backend/debian/registry-robot.yaml
# W2 claimed 144L

# Check service_ids count
grep -c "^- name:" demo_app_service/crates/demo-app-backend/debian/registry-robot.yaml || grep -c "^  - name:" demo_app_service/crates/demo-app-backend/debian/registry-robot.yaml
# W2 claimed 8 service_ids

# Check groups
grep -A1 "^groups:" demo_app_service/crates/demo-app-backend/debian/registry-robot.yaml
# W2 claimed 4 groups including robot-stack

# Check robot-stack group has 4 members
grep -A5 "robot-stack" demo_app_service/crates/demo-app-backend/debian/registry-robot.yaml
```

**Disprove checks**:
- [ ] File exists with ~144L? (W2 claimed 144L)
- [ ] 8 service_ids present? (W2 listed 8)
- [ ] 4 groups present including `robot-stack`?
- [ ] `robot-stack` group has members? (W2 claimed 4)

#### Observability §5 (CRITICAL — 8 traceability checks per evidence.md)

```bash
# Check 1 — Log presence: verify FAIL events at claimed file:line
sed -n '385,393p' demo_app_service/crates/demo-app-backend/src/handlers.rs
# W2 claimed: FAIL BAD_ENVELOPE_BRIDGE at handlers.rs:385-393 (to_lifecycle_env Err path)
sed -n '428,436p' demo_app_service/crates/demo-app-backend/src/handlers.rs
# W2 claimed: FAIL BAD_ENVELOPE_BRIDGE at handlers.rs:428-436 (from_lifecycle_env Err path)

# Check 6 — Cause preservation: grep for banned patterns
grep -n 'format!\s*("\{\}"\s*,\s*e' demo_app_service/crates/demo-app-backend/src/handlers.rs
grep -n '\.map_err\s*(|[^|]*|\s*format!' demo_app_service/crates/demo-app-backend/src/handlers.rs
# Expected: 0 hits (W2 claimed uses format!("{e:#}") which preserves cause)
grep -n 'format!\("{e:#}"\)' demo_app_service/crates/demo-app-backend/src/handlers.rs
# Expected: hits at the bridge Err paths

# Check 2 — Correlation: verify envelope bridge preserves header.id
grep -n "header.id\|header.ref_id" demo_app_service/crates/demo-app-backend/src/handlers.rs
# W2 claimed correlation_id propagation via Envelope.header.id

# Check 4 — Failure semantics: verify FAIL events have all required fields
# Read handlers.rs:385-393 and 428-436, check for: caller→callee, operation, phase, error_class, error_message+cause
```

**8 traceability checks** (per evidence.md, apply each):
- [ ] Check 1 — Log presence: FAIL events at handlers.rs:385-393 + 428-436 actually exist in source?
- [ ] Check 2 — Correlation correctness: every event has correlation_id (header.id)?
- [ ] Check 3 — Identity correctness: events use `service` + `instance_id` (NOT IP)?
- [ ] Check 4 — Failure semantics: FAIL has caller→callee, operation, phase, error_class, error_message+cause?
- [ ] Check 5 — Retry semantics: `attempt` 1-indexed, propagates across hops? (May be N/A for in-process)
- [ ] Check 6 — Cause preservation: no `format!("{}", e)` / `String(e)` patterns?
- [ ] Check 7 — First-failure reconstruction: can you identify first_failure / downstream_failures / final_failure from the code?
- [ ] Check 8 — Scope completeness: `run_id` via env `GAWAIN_RUN_ID`? (May be N/A if W2 didn't wire env var — flag as gap)

#### §4 Preserve/delete list

```bash
# Verify deleted fns are actually gone
for fn in handle_restart_service restart_container exec_in_container handle_start_service handle_stop_service stop_container; do
  echo "=== $fn ==="
  grep -n "fn $fn\|async fn $fn" demo_app_service/crates/demo-app-backend/src/handlers.rs
  # Expected: 0 hits
done

# Verify preserved fns still exist
for fn in handle_logs_collect collect_logs handle_robot_status handle_robot_operational query_robot_in_container handle_ping handle_echo handle_status handle_query_device; do
  echo "=== $fn ==="
  grep -n "fn $fn\|async fn $fn" demo_app_service/crates/demo-app-backend/src/handlers.rs
  # Expected: ≥1 hit
done
```

**Disprove checks**:
- [ ] 6 deleted fns actually absent from handlers.rs?
- [ ] 4 preserved fns + 4 simple handlers actually present?

### Step 5: Write V2-VERDICT.md (~2 min)

Write `demo_app_service/crates/demo-app-lifecycle/reports/V2-VERDICT.md` (~80-150L):

```markdown
# V2 Verdict — W2 demo-app-backend ↔ demo-app-lifecycle integration (Scheme A)

- **Verifier**: V2 (kimi-k3) — adversarial, disprove mandate
- **Worker**: W2 (glm-5.2, session 0bf41e22, ~6.5 min)
- **HEAD**: `d2b3b9d` (unchanged)
- **Overall verdict**: ACCEPT / RE-DISPATCH / ESCALATE

## §1 W2 §1 改动文件清单 — verdict
| Claim | V2 verdict | Evidence |
|---|---|---|
| 7 files in write-set | PASS/FAIL | (git status output) |
| 5 modified files match | PASS/FAIL | (git diff --stat output) |
| 2 new files match | PASS/FAIL | (ls output) |
| demo-app-lifecycle/src/ 0 changes | PASS/FAIL | (sha256 sentry value) |
| lifecycle_cli.rs P7b pre-existing | PASS/FAIL | (git diff --stat) |
| Cargo.lock side-effect | PASS/FAIL | (git diff --numstat) |
| **Per-file LoC discrepancy** | INVESTIGATE | (W2 claimed +81/-255, git says +239/-331 — explain) |

## §2 W2 §2 build results — verdict
| Build | W2 claimed | V2 rerun | Verdict |
|---|---|---|---|
| cargo check | exit 0 | exit N | PASS/FAIL |
| cargo build | exit 0, 35.4s | exit N, Xs | PASS/FAIL |
| cargo build musl | exit 0, 1m35s | exit N, Xm Ys | PASS/FAIL |
| cargo clippy | exit 0, 2 warnings | exit N, W warnings | PASS/FAIL |

## §3 W2 §3 ESCALATEs — verdict
| ESCALATE | W2 verdict | V2 verdict | Evidence |
|---|---|---|---|
| #1 Legacy callers RETIRE | ... | PASS/FAIL | (re-grep results) |
| #2 Misnomer silently delete | ... | PASS/FAIL | (grep results) |
| #3 Registry yaml port | ... | PASS/FAIL | (file content check) |
| #4 P8 standalone | ... | PASS (no decision needed) | — |

## §4 W2 §5 Observability — 8 traceability checks
| Check | What "pass" means | V2 verdict | Evidence |
|---|---|---|---|
| 1 Log presence | FAIL events at file:line exist | PASS/FAIL/N-A | (source excerpt) |
| 2 Correlation | every event has corr_id | PASS/FAIL/N-A | ... |
| 3 Identity | service + instance_id, not IP | PASS/FAIL/N-A | ... |
| 4 Failure semantics | FAIL has all fields | PASS/FAIL/N-A | ... |
| 5 Retry semantics | attempt 1-indexed | PASS/FAIL/N-A | ... |
| 6 Cause preservation | no format!("{}", e) | PASS/FAIL/N-A | (grep result) |
| 7 First-failure reconstruction | first/downstream/final identifiable | PASS/FAIL/N-A | ... |
| 8 Scope completeness | run_id via GAWAIN_RUN_ID | PASS/FAIL/N-A | ... |

## §5 W2 §4 Preserve/delete — verdict
| Claim | V2 verdict | Evidence |
|---|---|---|
| 6 deleted fns absent | PASS/FAIL | (grep results) |
| 4 preserved fns present | PASS/FAIL | (grep results) |
| 4 simple handlers present | PASS/FAIL | (grep results) |

## §6 W2 self-ESCALATEs to orchestrator — V2 recommendation
1. **Cargo.lock write-set violation**: ratify / override? (V2 recommendation + reason)
2. **query_robot_in_container conservative preserve**: ratify / override? (V2 recommendation + reason)
3. **musl build PASS**: confirmed / not confirmed?
4. **P8 priority**: confirmed.

## §7 V2 ESCALATEs (judgment calls V2 made alone)
- (any V2 ESCALATE)

## §8 Open issues for next phase (V2/E2 or W3)
- Live E2E against running daemon (lifecycle_cli re-run + wildcard race verify) — requires robot host or local daemon
- cargo deb packaging (Cargo.toml [package.metadata.deb].assets extension)
- ...

## §9 Files created
- `demo_app_service/crates/demo-app-lifecycle/reports/V2-VERDICT.md` — NNN lines

## §10 Time elapsed
Xs / 900s cap
```

## Output Contract — V2 Final Message

V2 final message 必须包含:
1. **Overall verdict**: ACCEPT / RE-DISPATCH / ESCALATE
2. **§1-§5 摘要** — 每 § verdict 一行(PASS/FAIL/INVESTIGATE)
3. **8 traceability checks 结果** — 8 行,每行 PASS/FAIL/N-A + 一行 evidence
4. **W2 self-ESCALATE × 4 recommendations** — 每条 ratify / override + 一行 reason
5. **LoC discrepancy investigation** — 解释 W2 said +81/-255 vs git +239/-331 的原因
6. **V2 ESCALATEs** — any V2 judgment calls
7. **Files created** — 1 file:line count
8. **Time elapsed** — Xs / 900s

## Hard constraints (recap)

- **15-min hard cap** (`timeout 900s`)。partial 到点必停。
- **0 code modification** — verifier 只读 + 写 V2-VERDICT.md。
- **0 改动任何 src/ 文件** + **0 改动 lifecycle_cli.rs**。
- **0 git push / 0 git commit / 0 git add / 0 AI attribution**。
- **Write-set 严格 1 个文件**(`V2-VERDICT.md`)。
- **HEAD-guard** before any git touchpoint。HEAD 必须保持 `d2b3b9d`。
- **NEVER modify SP000065 host files / services**(本 task 不涉及 SSH)。
- **Adversarial mandate**: disprove, NOT confirm。Find evidence each W2 claim is false。

## Normative reads (8 files, 60s)

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md`
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/README.md`
3. `/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/evidence.md` (8 checks adversarial checklist — read end-to-end)
4. `/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/context.md`
5. `/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/events.md`
6. `/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/propagation.md`
7. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/reports/P8-INTEGRATION-IMPLEMENTATION.md` (W2 report)
8. `/home/wangdang/work/ai-stack/logs/w2-demo-backend-lifecycle/waiter.out` (W2 final message, lines 17-149)

工作语言:中文为主,关键术语/文件路径保留英文。

现在开始:read 8 normative (60s),verify §1 write-set + LoC (3 min),re-run builds (4 min),verify §3-§5 ESCALATE + observability + preserve/delete (4 min),写 V2-VERDICT.md (2 min)。15 min hard cap。
