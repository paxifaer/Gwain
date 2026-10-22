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
| 9 | febe-contract — front/back integration contract workflow (requirements freeze, user-approved acceptance, adversarial close) | [skills/febe-contract/SKILL.md](../skills/febe-contract/SKILL.md) | frontend↔backend / cross-boundary tasks | task start | P0 |
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
| workflow/discussion-sync/（2026-10-22 已删除） | REMOVED — zero adoption + P0 defects (see docs/audits/2026-08-24-verifier-test-trace-audit.md); acceptance format superseded by skills/febe-contract/templates/ |
| workflow/agentflow/observability/README.md | NORMATIVE — traceability contract entry + workflow-policy boundary |
| workflow/agentflow/observability/context.md | NORMATIVE — 8 common fields + identity model (IP≠identity) |
| workflow/agentflow/observability/events.md | NORMATIVE — FAIL/ERROR/STATE taxonomy + scene-specific points + first-failure principle |
| workflow/agentflow/observability/propagation.md | NORMATIVE — correlation_id across 6 transports + run_id via env + attempt semantics |
| workflow/agentflow/observability/aggregation.md | NORMATIVE — per-run log layout for verifier replay |
| workflow/agentflow/observability/evidence.md | NORMATIVE — 8 verifier checks + bypass vectors + worked example + 10-question reconstruction table |
| skills/febe-contract/ | NORMATIVE — front/back integration contract skill (requirements freeze, templates, adversarial checklist) |
| model/（2026-10-22 已删除） | REMOVED — model routing belongs to the harness (AGENTS.md / dispatch rules), not Gawain |
| docs/reasoning.md（2026-10-22 已删除） | REMOVED — historical design record |
| workflow/handoffs/ | LEGACY-NON-NORMATIVE — old SPEC-*/PROMPT-* convention; do not mine for rules; workflow.md forbids retro-migration |
