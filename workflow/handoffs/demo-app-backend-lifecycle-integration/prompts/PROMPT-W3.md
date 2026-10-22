# PROMPT-W3 — W3 followup (observability schema + cleanup) for P8 (glm-5.2)

```
Before doing anything else:
1. Read /home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's classifier. Q4=YES (cross-boundary
   zenoh integration) → 必读 agentflow/observability/{README,context,events,
   propagation,evidence}.md。evidence.md 8 checks 是 V3 verifier 的 adversarial
   checklist — 你的目标让 8/8 PASS。
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly 9 files:
   - crates/demo-app-backend/src/handlers.rs              (MODIFY — structured FAIL events)
   - crates/demo-app-backend/src/main.rs                  (MODIFY — GAWAIN_RUN_ID wiring)
   - crates/demo-app-backend/src/config.rs                (MODIFY — add run_id, remove orphan)
   - crates/demo-app-backend/src/observability.rs          (NEW — log_fail! macro or FailEvent)
   - crates/demo-app-backend/debian/demo-app-backend.service  (MODIFY — remove dead env, add GAWAIN_RUN_ID)
   - crates/demo-app-frontend/src/main.rs                 (MODIFY — drop restart_service doc at L43)
   - crates/demo-app-types/src/lib.rs                      (MODIFY — retire 3 constants)
   - crates/demo-app-lifecycle/reports/P8-INTEGRATION-IMPLEMENTATION.md  (MODIFY — annotate §1 LoC)
   - crates/demo-app-lifecycle/reports/W3-FOLLOWUP-REPORT.md  (NEW — W3 report)
   Report every file created/modified with line numbers in your final message.
   ANY file outside this list = contract violation.

HEAD-guard: before any git touchpoint, run `git log --oneline -1 && git status --short`.
HEAD MUST remain `d2b3b9d`. NEVER `git add` / `git commit` / `git push`. NEVER AI attribution.

model_selection:
  model: t9s/glm-5.2
  mode: automatic
  reason: large_refactoring  # structured logging refactor + multi-crate cleanup
```

---

You are **W3 followup worker for P8** — close V2's 4 evidence.md FAIL checks + W3-cleanup items。V2 (session `4bb405e8-914d-4151-b37a-c6463d11beff`, kimi-k3) verdict ESCALATE:机制面 PASS / observability 8 checks (2 PASS / 1 N-A / 1 PARTIAL / **4 FAIL**)。用户 D-124 拍板:**全 followup**(W3 + E2 + W3-cleanup),W3 合并 observability + cleanup。

## CRITICAL: 30-MIN HARD CAP + 0 LIFECYCLE/SRC CHANGES

- **Hard time cap: 30 min wall clock**(`timeout -k 5 1800s`)。
- **0 git push / 0 git commit / 0 git add / 0 AI attribution**。
- **0 改动 `demo-app-lifecycle/src/`*** — 严格 0(同 W2)。
- **0 改动 `demo-app-lifecycle/examples/lifecycle_cli.rs`** — P7b pre-existing,W3 不碰。
- **Write-set 严格 9 个文件**(列 above)。
- **NEVER modify SP000065 host 文件 / services**(本 task 不涉及 SSH)。
- **禁止**返回 plan / outline / status update / "next I'll ..."。Work continuously 直到 9 个 deliverable 文件写完 + final message 交付。

## Pre-known facts (inline — from V2-VERDICT.md, do not re-verify)

### V2 4 FAIL checks (W3 must close)

| # | Check | V2 evidence | W3 fix target |
|---|---|---|---|
| 1 | Log presence | W2 报 `handlers.rs:385-393` 实为 `:400-408`(偏 ±12);`:428-436` 实为 `:427-435` | W3 改 FAIL events 必须 report 准确 file:line 在 final message;code 中 event 位置不变(只是 line numbers 可能 shift 因新增 structured fields) |
| 2 | Correlation (log-level) | envelope-level `header.id` 保留 ✓,但 log 行无 `corr=` 字段 | W3 在 FAIL log 行加 `corr=<envelope.header.id>` structured field |
| 3 | Identity | 0 hits `service=` / `instance_id=` | W3 在 FAIL log 行加 `service="demo-app-backend"` + `instance_id=<bot_name from config>` |
| 4 | Failure semantics | 缺 `caller=/callee=/phase=/error_class=` | W3 加 `caller="demo-app-backend"` `callee="demo-app-lifecycle"` `phase="request"|"response"` `error_class="SerdeJson"|"BadEnvelopeBridge"` |
| 7 | First-failure reconstruction | PARTIAL — single-row trace trivially 但缺 `phase=` 不可区分 first/final | W3 加 `phase=` 后,single-row trace 仍可重构,但 schema 上 first(final 同 row) 可区分(Phase::Request = first, Phase::Response = final) |
| 8 | Scope completeness | 0 hits `GAWAIN_RUN_ID` 在两 crate src | W3 wire `GAWAIN_RUN_ID` env 到 `Config.run_id`,在 FAIL log 行加 `run_id=<from env>`;demo-app-lifecycle/src/ **不改**(0 改动 mandate)— lifecycle 自身的 run_id wiring 不在 W3 scope,V3 验证时承认 lifecycle 侧 N-A |

### V2 4 ESCALATEs (W3 cleanup items)

1. **W2 per-file LoC table 拆分错** — annotate P8-INTEGRATION-IMPLEMENTATION.md §1 with corrected LoC from V2 §1a:
   - `Cargo.toml` +1/0 ✓
   - `demo-app-backend.service` +1/0 ✓
   - `config.rs` +5/0(W2 claimed +6)
   - `handlers.rs` +102/-322(W2 claimed +40/-255)
   - `main.rs` +130/-9(W2 claimed +73)
   - **net** +239/-331(W2 claimed +81/-255)
2. **FAIL file:line 偏 ±12** — W3 中 event 位置可能 shift,但 final message 必须报准确 file:line(post-W3)
3. **evidence.md canonical-field non-compliance** — W3 main work(see 8 checks above)
4. **`demo-app-frontend/src/main.rs:43` doc-comment 仍示例 `restart_service`** — W3 修:drop `restart_service` example from doc-comment(or 整段重写 example 用 `lifecycle.restart`)

### Additional W3-cleanup items

5. **`demo-app-types` 3 个 action constants retire**: `RESTART_SERVICE` / `START_SERVICE` / `STOP_SERVICE` at `lib.rs:21,23,25` — W2 ESCALATE #1 RETIRE 后,backend 不再用这些 action 串。W3 retire them from `demo-app-types/src/lib.rs`。Verify 0 caller across sibling repos before retire(quick grep,同 W2 ESCALATE #1 pattern)。
6. **`docker_restart_timeout_secs` orphan cleanup**: `Config` field 在 W2 后变 unread(clippy 警告)。W3 删 `config.rs` 中 `docker_restart_timeout_secs` field + `from_env` 中相关 env read + `demo-app-backend.service` 中 `Environment=DOCKER_RESTART_TIMEOUT_SECS=60` line。

### W2 §5 observability injection sites (post-W2, pre-W3)

W2 claimed (但 V2 disprove):
- FAIL `BAD_ENVELOPE_BRIDGE` at `handlers.rs:385-393` (`to_lifecycle_env` Err path), phase=request
- FAIL `BAD_ENVELOPE_BRIDGE` at `handlers.rs:428-436` (`from_lifecycle_env` Err path), phase=response

V2 实测 actual(post-W2):
- to_lifecycle_env Err `error!` at `handlers.rs:400-408`
- from_lifecycle_env Err `error!` at `handlers.rs:427-435`

W3 必须找到这 2 个 Err path,替换 freeform `error!` 为 structured `log_fail!`(或 `tracing::error!` with all canonical fields)。

## Task (5 步)

### Step 1: Read normative + V2 verdict + W2 P8 report (~3 min)

Read:
- `workflow/bootstrap.md`
- `workflow/agentflow/observability/{README,context,events,propagation,evidence}.md`(8 checks 是 target)
- `demo_app_service/crates/demo-app-lifecycle/reports/V2-VERDICT.md`(V2 verdict + 4 FAIL checks + LoC discrepancy)
- `demo_app_service/crates/demo-app-lifecycle/reports/P8-INTEGRATION-IMPLEMENTATION.md`(W2 report,要 annotate §1)
- `demo_app_service/crates/demo-app-backend/src/handlers.rs`(W2 post-edit,找 2 个 FAIL `error!` sites)
- `demo_app_service/crates/demo-app-backend/src/main.rs` + `config.rs`(GAWAIN_RUN_ID wiring points)
- `demo_app_service/crates/demo-app-frontend/src/main.rs:43`(doc-comment 修)
- `demo_app_service/crates/demo-app-types/src/lib.rs:21,23,25`(3 constants retire)

### Step 2: Create `src/observability.rs` + structured FAIL events (~10 min)

**Step 2a**: 写 `crates/demo-app-backend/src/observability.rs`(NEW):

Define a `log_fail!` macro(或 `struct FailEvent` + helper fn)that emits canonical fields per evidence.md:

```rust
// Pseudocode — W3 实现可调整 style
#[macro_export]
macro_rules! log_fail {
    ($rt:expr, $envelope:expr, $phase:expr, $error_class:expr, $error:expr, $op:expr) => {
        tracing::error!(
            run_id = %$rt.run_id,
            corr = %$envelope.header.id,
            service = "demo-app-backend",
            instance_id = %$rt.bot_name,
            caller = "demo-app-backend",
            callee = "demo-app-lifecycle",
            op = %$op,
            phase = %$phase,
            error_class = %$error_class,
            error_message = %format!("{e:#}", e = $error),
            cause = %format!("{e:#}", e = $error),
            "lifecycle envelope bridge failed"
        );
    };
}
```

OR use direct `tracing::error!` with all fields at each FAIL site(更简单,无 macro,DRY via local helper fn if needed)。

W3 自己选 macro vs direct style — 但 8/8 evidence.md checks 必须满足。

**Step 2b**: Modify `handlers.rs`:
- Find `to_lifecycle_env` Err path(post-W2 around `:400-408`)— replace freeform `error!` with `log_fail!`(or structured `error!`)
- Find `from_lifecycle_env` Err path(post-W2 around `:427-435`)— same
- Both sites 必须有:`run_id=`, `corr=`, `service=`, `instance_id=`, `caller=`, `callee=`, `op=`, `phase=`, `error_class=`, `error_message=`, `cause=`
- `phase` 值:`Phase::Request` for to_lifecycle_env(去程),`Phase::Response` for from_lifecycle_env(回程)
- `error_class`:`"SerdeJson"` or `"BadEnvelopeBridge"`(W3 选一,consistent)
- `cause` 用 `format!("{e:#}")` 保留 cause chain(同 W2)

**Step 2c**: Modify `main.rs`:
- 在 `main()` early init: `let run_id = std::env::var("GAWAIN_RUN_ID").unwrap_or_else(|_| "prod".to_string());`
- Pass `run_id` into `Config`(via `from_env` or main 直接 set)
- Initialize `tracing` with `run_id` as default field(可选 — via `tracing_subscriber::fmt::format()` or env filter)

**Step 2d**: Modify `config.rs`:
- 加 `pub run_id: String` field to `Config`
- 在 `from_env` 加 `run_id: env::var("GAWAIN_RUN_ID").unwrap_or_else(|_| "prod".to_string())`
- 删 `pub docker_restart_timeout_secs: ...` field + env read

### Step 3: Sibling crates cleanup (~5 min)

**Step 3a**: Modify `demo-app-frontend/src/main.rs:43`:
- Read current doc-comment(around line 43,W2 ESCALATE #1 grep found `restart_service` example there)
- Drop `restart_service` from example,replace with `lifecycle.restart`(or remove the example entirely if simpler)
- Match style of surrounding doc-comments

**Step 3b**: Modify `demo-app-types/src/lib.rs:21,23,25`:
- Quick grep across sibling repos for `actions::RESTART_SERVICE|actions::START_SERVICE|actions::STOP_SERVICE` — verify 0 caller(should be 0 since W2 already verified `restart_service|start_service|stop_service` zenoh action 串 0 live caller)
- If 0 caller:retire the 3 constants from `lib.rs:21,23,25`(delete lines)
- If ≥1 caller:ESCALATE(do NOT delete,记录 in W3-FOLLOWUP-REPORT.md)

**Step 3c**: Modify `demo-app-backend/debian/demo-app-backend.service`:
- Remove `Environment=DOCKER_RESTART_TIMEOUT_SECS=60` line(dead env post-cleanup)
- 可选:Add `Environment=GAWAIN_RUN_ID=prod`(default for non-test deploy)— or leave to runtime env

### Step 4: Annotate P8 report + write W3-FOLLOWUP-REPORT (~5 min)

**Step 4a**: Modify `P8-INTEGRATION-IMPLEMENTATION.md` §1:
- 加 sub-section "§1a LoC correction (per V2 verdict)" — list corrected per-file LoC from V2 §1a(表 above in pre-known facts)
- 注明 W2 原 per-file table 是 hand-estimate,git stat `+239/-331` 是 authoritative

**Step 4b**: Write `W3-FOLLOWUP-REPORT.md`(NEW,~80-150L):

```markdown
# W3 Followup — observability schema compliance + cleanup

- **Worker**: W3 (glm-5.2)
- **HEAD**: `d2b3b9d` (unchanged)
- **Target**: close V2's 4 FAIL evidence.md checks + 4 V2 ESCALATEs + 2 cleanup items
- **Net diff**: +XXX / −XXX LoC across 9 files

## §1 9-file write-set 改动清单
| # | File | Action | LoC | Summary |
|---|---|---|---|---|

## §2 evidence.md 8 checks target — W3 self-assessment
| # | Check | V2 verdict | W3 fix | W3 self-check |
|---|---|---|---|---|
| 1 | Log presence | FAIL ±12 | (accurate file:line in final msg) | PASS/FAIL |
| 2 | Correlation log-level | FAIL | (add corr= field) | PASS/FAIL |
| 3 | Identity | FAIL | (add service/instance_id) | PASS/FAIL |
| 4 | Failure semantics | FAIL | (add caller/callee/phase/error_class) | PASS/FAIL |
| 5 | Retry | N-A | (no retry in bridge) | N-A |
| 6 | Cause preservation | PASS | (preserve format!("{e:#}")) | PASS |
| 7 | First-failure | PARTIAL | (phase= distinguishes first/final) | PASS/FAIL |
| 8 | Scope completeness | FAIL | (wire GAWAIN_RUN_ID) | PASS/FAIL |

## §3 V2 4 ESCALATEs resolution
1. P8 LoC annotate → done at P8-INTEGRATION-IMPLEMENTATION.md §1a
2. FAIL file:line ±12 → accurate file:line reported in §1
3. evidence.md canonical-field non-compliance → W3 main work(see §2)
4. frontend doc-comment → done at demo-app-frontend/src/main.rs:43

## §4 Additional cleanup
5. demo-app-types 3 constants retire → done / ESCALATE
6. docker_restart_timeout_secs orphan cleanup → done

## §5 cargo check / build / musl build / clippy results
| Command | Exit | Notes |
|---|---|---|

## §6 Files created/modified (9 file:line count)

## §7 Open issues / V3 验证项

## §8 Time elapsed
```

### Step 5: Build + test (~5 min)

```bash
cd /home/wangdang/work/ai-stack/code/ArgoWatch

# 1. cargo check
cargo check -p demo-app-backend 2>&1 | tail -30
echo "check exit: $?"

# 2. cargo build
cargo build -p demo-app-backend 2>&1 | tail -30
echo "build exit: $?"

# 3. cargo build musl
cargo build --target x86_64-unknown-linux-musl -p demo-app-backend 2>&1 | tail -30
echo "musl exit: $?"

# 4. cargo clippy
cargo clippy -p demo-app-backend --no-deps 2>&1 | tail -30
echo "clippy exit: $?"

# 5. cargo check sibling crates (demo-app-frontend / demo-app-types)
cargo check -p demo-app-frontend 2>&1 | tail -20
cargo check -p demo-app-types 2>&1 | tail -20

# 6. Self-grep evidence.md 8 checks
grep -n "run_id\|corr=\|service=\|instance_id=\|caller=\|callee=\|phase=\|error_class=" demo_app_service/crates/demo-app-backend/src/handlers.rs | head -30
grep -n "GAWAIN_RUN_ID" demo_app_service/crates/demo-app-backend/src/*.rs
grep -n "format!\s*(\"\{\}\"\s*," demo_app_service/crates/demo-app-backend/src/handlers.rs  # banned pattern, expect 0
```

**W3 self-check exit codes**:全 0 = ready for V3 verify。Any fail → ESCALATE in final message。

## Output Contract — W3 Final Message

W3 final message 必须包含:
1. **§1 9-file 改动清单** — 每 file:line range + before/after LoC + 简述
2. **§2 evidence.md 8 checks W3 self-assessment** — 8 行,每行 PASS/FAIL/N-A + 一行 evidence(grep output or source excerpt)
3. **§3 V2 4 ESCALATEs resolution** — 4 行,每行 done/ESCALATE + 一行 evidence
4. **§4 2 cleanup items** — done/ESCALATE + evidence
5. **§5 build results** — 5 个 build command 的 exit code + 关键 tail
6. **§6 accurate file:line for FAIL events**(post-W3, post-line-shift)
7. **§7 Files created/modified** — 9 file:line count
8. **§8 Time elapsed** — Xs / 1800s
9. **§9 ESCALATE to orchestrator** — 任何 W3 自己无法解决的 judgment call

## Hard constraints (recap)

- **30-min hard cap** (`timeout 1800s`)。partial 到点必停。
- **0 git push / 0 git commit / 0 git add / 0 AI attribution**。
- **0 改动 `demo-app-lifecycle/src/`*** — 严格 0。
- **0 改动 `demo-app-lifecycle/examples/lifecycle_cli.rs`** — P7b pre-existing,W3 不碰。
- **0 改动 SP000065 host 文件**。
- **Write-set 严格 9 个文件**(列 above)。
- **HEAD-guard** before any git touchpoint。HEAD 必须保持 `d2b3b9d`。
- **8/8 evidence.md checks target**:W3 self-check PASS for all 8,等 V3 adversarial verify。
- **musl build 失败要 ESCALATE**,不能 silently skip。
- **CLAUDE.md §2 Simplicity First**:log_fail! macro vs direct structured `error!` — 选简单那个(2 个 FAIL site 可能不需要 macro,直接 structured `error!` 即可)。
- **CLAUDE.md §3 Surgical Changes**:只动 9 个 declared files,不 refactor 邻近代码。

## Normative reads (8 files, 60s)

1. `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md`
2. `/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/README.md`
3. `/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/evidence.md` (8 checks adversarial checklist)
4. `/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/context.md` (8 common fields)
5. `/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/events.md` (FAIL/ERROR/STATE taxonomy)
6. `/home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/propagation.md` (correlation_id across boundaries)
7. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/reports/V2-VERDICT.md` (V2 verdict)
8. `/home/wangdang/work/ai-stack/code/ArgoWatch/demo_app_service/crates/demo-app-lifecycle/reports/P8-INTEGRATION-IMPLEMENTATION.md` (W2 report, to annotate)

工作语言:中文为主,关键术语/文件路径保留英文。

现在开始:read 8 normative (60s),create observability.rs + structured FAIL (10 min),sibling cleanup (5 min),annotate P8 + write W3 report (5 min),build + self-grep (5 min)。30 min hard cap。
