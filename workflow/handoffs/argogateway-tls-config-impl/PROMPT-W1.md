# PROMPT-W1 — Implement TLS-mode zenoh-router config in demo + skyline

## Worker preamble (prepend to task prompt when dispatching)

```text
Before doing anything else:
1. Read /home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's four questions and follow every
   rule that applies.
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly the files declared in this prompt. Report every
   file created or modified, with line numbers, in your final message.
5. Code you write that participates in a cross-boundary integration test
   MUST follow the Integration Traceability Contract at
   /home/wangdang/work/ai-stack/code/Gawain/workflow/agentflow/observability/README.md
   (read it before writing any logging call). The contract covers common
   fields (ts, level, event_kind, run_id, correlation_id, attempt, service,
   instance_id), event-specific fields (FAIL/ERROR/STATE), correlation_id
   propagation across every boundary, first-failure reconstruction, and the
   8 verifier checks. Integration debug across multi-party calls depends on
   this; a missing field fails the run.
If the task directory has a state.md with a ## Blocked section, the listed
file::symbol entries are read-only for you; needing to touch one is an
ESCALATE trigger. (This task has no state.md — risk classified as low, no
task-state layout.)
```

## Who
You are the **W1 implementation worker** for the Gawain task
`argogateway-tls-config-impl`. You implement D1 + D2 (TLS-mode zenoh-router
config generation) in both `apps/demo` and `apps/skyline` of
`robot-app-platform`. You write code, run builds + tests, and produce a report.

## What
Read the SPEC in full first:
`/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/argogateway-tls-config-impl/SPEC-01.md`

Then implement the 4-file change described in §"What changes". Quick summary
(SPEC is authoritative — read it):

1. **`apps/demo/src/components/manage-robot/zenohRouterConfig.ts`**:
   - Extend `ZenohRouterConfig` type with optional `transport.link.tls` block
   - Add new constants (`ZENOH_ROUTER_TLS_PORT=57448`,
     `ZENOH_ROUTER_LOOPBACK_ENDPOINT="tcp/127.0.0.1:57449"`, cert paths)
   - Modify `buildZenohRouterConfig()` to accept `{ enableTls?: boolean }`
     (default false), emit TLS shape when true
   - Relax `validateZenohRouterConfig()` to accept TLS shape; don't fire the
     `mustInclude0.0.0.0:57447` check when `transport.link.tls` present; add
     parallel TLS-shape checks

2. **`apps/demo/src/components/manage-robot/NetworkConfigDialog.tsx`**:
   - Add TLS checkbox UI, default unchecked
   - Wire toggle state into `buildZenohRouterConfig({ enableTls })` call
   - Extend metadata: `{operator: "demoapp", tls_mode: enableTls ? "tls" : "plaintext"}`
   - Sync toggle with raw-JSON edit if feasible (else ESCALATE)

3. **`apps/skyline/src/features/projects/workspace/networkConfig/zenohRouterConfig.ts`**:
   - Same changes as #1. If file diverges from demo's twin, ESCALATE.

4. **`apps/skyline/src/features/projects/workspace/networkConfig/NetworkConfigDialog.tsx`**:
   - Same changes as #2. Do NOT conflate with the existing "TLS fallback to
     plaintext" CLIENT-side transport branch at lines 421–479 — that's
     orthogonal; the new toggle controls SERVER config generation.

## Why
The user wants the "click TLS" UX in both apps to actually produce a
different ArgoDDS server config — matching what `install_cluster.sh` does in
TLS mode. The prior audit (W1-REPORT.md) showed this is currently a gap (14
deltas, 0 mirrored). This task closes D1 (zenohd-global listen endpoints
TLS-mode) and D2 (transport.link.tls block). Server-side env derivation
(D4–D14) and cert perms (D3) are deferred to a separate task.

## Constraints

### Write-set (the ONLY files you may create/modify)
1. `apps/demo/src/components/manage-robot/zenohRouterConfig.ts`
2. `apps/demo/src/components/manage-robot/NetworkConfigDialog.tsx`
3. `apps/skyline/src/features/projects/workspace/networkConfig/zenohRouterConfig.ts`
4. `apps/skyline/src/features/projects/workspace/networkConfig/NetworkConfigDialog.tsx`

Plus any new test files inside the same directories (if needed for sanity
checks). No changes elsewhere — no `packages/`, no `crates/`, no
`*-tauri/`, no `*.proto`, no root configs.

### No git operations
- No `git add`, `git commit`, `git push`, `git reset`, branch creation.
- HEAD-guard before any git touchpoint (none expected):
  `git log --oneline -1 && git status --short`.
- Leave changes in working tree.

### Network installs through proxy
User is in mainland China. For any network operation:
- `cargo` — set `HTTPS_PROXY=http://127.0.0.1:7897 HTTP_PROXY=http://127.0.0.1:7897`
- `bun` — set `BUN_CONFIG_HTTPS_PROXY=http://127.0.0.1:7897`
- `npm` — `--proxy=http://127.0.0.1:7897 --https-proxy=http://127.0.0.1:7897`
- Avoid installs if possible — repo is already bootstrapped (Cargo.lock and
  bun.lock have 8月 18 timestamps).

### Integration Traceability Contract (Q4 applies)
This task writes cross-boundary integration code (frontend UI → gRPC
`PushZenohRouterConfig` → server). Before writing any logging call, you
MUST load:
- `agentflow/observability/README.md`
- `agentflow/observability/context.md`
- `agentflow/observability/events.md`
- `agentflow/observability/propagation.md`

The TLS toggle code MUST emit:
- **STATE** event when toggle state changes — includes
  `tls_mode: "tls" | "plaintext"` and resulting config shape.
- **STATE** event when `buildZenohRouterConfig({ enableTls: true })` is called.
- **FAIL** event when `validateZenohRouterConfig` rejects a TLS-shaped config.
- **correlation_id** propagation via the existing push mutation's mechanism.
  If no infrastructure exists, ESCALATE — do not invent.

If the existing `zenohRouterConfig.ts` and `NetworkConfigDialog.tsx` have
**no logging infrastructure at all**, ESCALATE — adding new logging
infrastructure is beyond the declared write-set; the user must decide
whether to expand the scope.

### Backward compatibility
- Default toggle OFF — no behavior change for existing robots.
- Existing `metadata: {operator: "demoapp"}` MUST be preserved; only ADD
  `tls_mode` alongside it.
- Existing tests must continue to pass.

## Inputs
- SPEC: `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/argogateway-tls-config-impl/SPEC-01.md` (authoritative — read in full)
- Prior audit report: `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/argogateway-tls-config-audit/W1-REPORT.md` (for context on what gaps exist + exact line numbers)
- Prior audit V1 verdict: `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/argogateway-tls-config-audit/V1-VERDICT.md`
- Reference script: `/home/wangdang/work/ai-stack/code/ArgoDeploy/real/install_cluster.sh` lines 78–102 (zenohd-global.json5 TLS branch) — this is the golden shape
- Target repo: `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/`

## Verification (you MUST run these — see SPEC §"Verification")
1. `cargo build` from repo root (with proxy env if any fetch needed)
2. `bun run build` for the workspace (or whatever `package.json` `scripts.build` says)
3. `bun run check` (biome / tsc) — zero new errors
4. Run any existing tests touching `zenohRouterConfig.ts` or `NetworkConfigDialog.tsx`. If no tests exist, ESCALATE.
5. Manual sanity check: produce the actual JSON5 output of
   `buildZenohRouterConfig({ enableTls: true })` and `... false` and confirm
   they differ exactly per spec.

## Output contract — W1 final message (≤300 words)
Your final message to the orchestrator must contain:

1. **Files changed** — list each of the 4 files with line ranges modified
   (e.g. `apps/demo/.../zenohRouterConfig.ts:8–27, 187–241, 275–346`).
2. **Build / check / test results** — per-step PASS/FAIL with actual command
   output snippets (≤5 lines each). Pre-existing errors must be listed
   separately.
3. **TLS shape verification** — paste the actual JSON5 output of
   `buildZenohRouterConfig({ enableTls: true })` AND
   `buildZenohRouterConfig({ enableTls: false })` (the actual output, not
   the spec).
4. **Metadata key chosen** — `tls_mode` (or whatever you used).
5. **Traceability events emitted** — list each new event (STATE/FAIL) with
   its `event_kind`, field set, and where it's emitted (file:line). If you
   ESCALATE'd the logging-infrastructure question, say so explicitly.
6. **ESCALATEs** — judgment calls you made alone. One line each:
   - metadata key name choice
   - whether logging infrastructure existed or had to be added
   - any divergence between demo and skyline `zenohRouterConfig.ts`
   - any test you couldn't run (missing toolchain, missing deps)
   - any back-compat risk you noticed but couldn't fully verify
7. **Elapsed time**.

Do NOT paste the full file contents into the message. Point to the files.
The orchestrator will dispatch V1 to adversarially verify.

## Verification
A verifier worker (V1) will be dispatched after you. V1's mandate is to
**disprove** your claims — re-open each modified file, re-run the build,
re-run the validator, attempt to construct a TLS-shaped config that the
relaxed validator wrongly accepts, and run the 8 traceability checks from
`agentflow/observability/evidence.md` adversarially. Any fabricated PASS
claim, any "default OFF" that is actually ON, any TLS shape that doesn't
match `install_cluster.sh:80–91` — V1 returns FAIL and you will be
re-dispatched. Verify your own work before reporting.
