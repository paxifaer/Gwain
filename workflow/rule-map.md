# Gawain Rule Map — which rules apply, where they live

Machine-greppable index. Rule text lives ONLY in the authoritative file it is
assigned to — never copy rule bodies into prompts, other docs, or memory.
Entry point for all agents: [`bootstrap.md`](bootstrap.md).

## Cluster map

| # | Cluster | Authoritative source | Applies when | Load when | Priority |
|---|---------|----------------------|--------------|-----------|----------|
| 1 | Orchestrator law (Plan/Dispatch/Judge only; never edit/test/grep) | workflow.md §Core Principle | always | session start | P0 |
| 2 | Prompt design (Who/What/Why/Constraints/Inputs/Output contract) | workflow.md §Prompt Design | dispatching | before dispatch | P0 |
| 3 | Dispatch loop (spec file → workers → poll → verifier → judge) | workflow.md §Dispatch Loop | dispatching | before dispatch | P0 |
| 4 | Worker output contract (files+lines, per-check PASS/FAIL, ESCALATEs) | workflow.md §Output Contract | dispatch + judge | before dispatch | P0 |
| 5 | Adversarial verifier (mandate to disprove, recursion floor) | workflow.md §Verification | verifying | before verify | P0 |
| 6 | Escalation triggers | workflow.md §When to Escalate | always | lazy | P0 |
| 7 | Red flags / failure modes & anti-patterns | workflow.md §Red Flags, §Failure Modes | self-diagnosis | lazy | P1 |
| 8 | High-Risk Gate (H1/H2 hard, S1–S4 soft; risk: high → layout mandatory) | workflow.md §High-Risk Reasoning Gate | plan time, once per task | plan phase | P0 |
| 9 | Model selection | workflow.md §Model Selection + ../model/model.yaml | task start | plan phase | P1 |
| 10 | Sync opt-in, idempotency triad, do-nots | workflow.md §Discussion Session Sync | task opts in | plan phase | P1 |
| 11 | Sync protocol core (closed sets, R-1..R-11, ledger authority) | discussion-sync/protocol.md | sync active | on opt-in | P1 |
| 12 | Reasoning ledger §9 (4-state machine, birth rules, invalidation Step0-6, verdict schema, DER/D prefixes) | discussion-sync/protocol.md §9 | task.md has `risk: high` | on Gate hit | P0 (conditional) |
| 13 | Task-state templates (task/state/decisions/evaluation) | discussion-sync/templates/ | layout in use | on opt-in / Gate hit | P1 |
| 14 | Extractor / ingest prompts (incl. ingest §3.9 sweep) | discussion-sync/prompts/ | running those sessions | at that session start | P1 |
| 15 | Examples (001 sync ingest dry-run, 002 high-risk swerve) | discussion-sync/example/ | learning / dry-run reference | lazy | P2 |
| 16 | Hard constraints + worker preamble + recovery protocol | bootstrap.md, worker-preamble.md | always | session start | P0 |
| 17 | Traceability contract — overview & workflow-policy boundary | agentflow/observability/README.md | worker/verifier entry to traceability | first load | P0 |
| 18 | Traceability contract — context (8 common fields, identity model, IP≠identity, field form) | agentflow/observability/context.md | worker writes integration code | before logging call | P0 |
| 19 | Traceability contract — events (FAIL/ERROR/STATE taxonomy, scene-specific mandatory points, error-passthrough, first-failure principle) | agentflow/observability/events.md | worker writes integration code | before logging call | P0 |
| 20 | Traceability contract — propagation (correlation_id across 6 transports, run_id via env GAWAIN_RUN_ID, attempt semantics) | agentflow/observability/propagation.md | worker writes integration code | before logging call | P0 |
| 21 | Traceability contract — aggregation (per-run log layout, verifier grep paths, retention) | agentflow/observability/aggregation.md | test harness setup | before integration test launch | P1 |
| 22 | Traceability contract — evidence (8 verifier checks, bypass vectors, 12-line worked example, 10-question reconstruction table) | agentflow/observability/evidence.md | verifier session | before verify | P0 |

## File status (normative vs historical)

| Path | Status |
|------|--------|
| workflow/workflow.md | NORMATIVE — methodology 铁律 |
| workflow/bootstrap.md | NORMATIVE — entry point |
| workflow/rule-map.md | NORMATIVE — this index |
| workflow/worker-preamble.md | NORMATIVE — dispatch template |
| workflow/discussion-sync/protocol.md | NORMATIVE — sync protocol + §9 |
| workflow/discussion-sync/templates/ | NORMATIVE — file shapes |
| workflow/discussion-sync/prompts/ | NORMATIVE — role prompts |
| workflow/discussion-sync/ARCHITECTURE.md | EXPLANATORY — design narrative |
| workflow/discussion-sync/example/ | EXAMPLE — dry-run fixtures |
| workflow/agentflow/observability/README.md | NORMATIVE — traceability contract entry + workflow-policy boundary |
| workflow/agentflow/observability/context.md | NORMATIVE — 8 common fields + identity model (IP≠identity) |
| workflow/agentflow/observability/events.md | NORMATIVE — FAIL/ERROR/STATE taxonomy + scene-specific points + first-failure principle |
| workflow/agentflow/observability/propagation.md | NORMATIVE — correlation_id across 6 transports + run_id via env + attempt semantics |
| workflow/agentflow/observability/aggregation.md | NORMATIVE — per-run log layout for verifier replay |
| workflow/agentflow/observability/evidence.md | NORMATIVE — 8 verifier checks + bypass vectors + worked example + 10-question reconstruction table |
| model/model.yaml | NORMATIVE — model registry |
| docs/reasoning.md | HISTORICAL — pre-freeze design record, superseded by protocol.md §9 |
| workflow/handoffs/ | LEGACY-NON-NORMATIVE — old SPEC-*/PROMPT-* convention; do not mine for rules; workflow.md forbids retro-migration |
