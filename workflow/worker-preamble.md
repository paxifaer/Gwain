# Worker Preamble — paste at the top of every Gawain worker prompt

Orchestrator: prepend this block, replacing `<GAWAIN_REPO>` with the actual
checkout path (e.g. `~/work/ai-stack/workflow/Gawain`), then add the
task-specific slots (Who/What/Why/Constraints/Inputs/Output contract) per
workflow.md §Prompt Design.

```text
Before doing anything else:
1. Read <GAWAIN_REPO>/workflow/bootstrap.md
   (and rule-map.md if it points you to more files).
2. Classify this task per bootstrap.md's three questions and follow every
   rule that applies.
3. You run non-interactively. Open judgment calls → record an ESCALATE in
   your final message; never try to ask the user.
4. Your write-set is exactly the files declared in this prompt. Report every
   file created or modified, with line numbers, in your final message.
5. Code you write that participates in a cross-boundary integration test
   MUST follow the Integration Traceability Contract at
   <GAWAIN_REPO>/workflow/agentflow/observability/README.md
   (read it before writing any logging call). The contract covers common
   fields (ts, level, event_kind, run_id, correlation_id, attempt, service,
   instance_id), event-specific fields (FAIL/ERROR/STATE), correlation_id
   propagation across every boundary, first-failure reconstruction, and the
   8 verifier checks. Integration debug across multi-party calls depends on
   this; a missing field fails the run.
If the task directory has a state.md with a ## Blocked section, the listed
file::symbol entries are read-only for you; needing to touch one is an
ESCALATE trigger.
```

## Traceability contract — single source of truth

The full code-level logging spec lives in the
[`agentflow/observability/`](agentflow/observability/README.md) submodule:

| File | What it covers |
|---|---|
| [`agentflow/observability/README.md`](agentflow/observability/README.md) | Contract entry; 8 verifier checks at a glance; submodule boundary with workflow policy |
| [`agentflow/observability/context.md`](agentflow/observability/context.md) | 8 common fields; identity model (IP ≠ identity); field form |
| [`agentflow/observability/events.md`](agentflow/observability/events.md) | FAIL/ERROR/STATE taxonomy; scene-specific mandatory log points; error-passthrough rule; **first-failure principle** (first_failure vs downstream_failures vs final_failure) |
| [`agentflow/observability/propagation.md`](agentflow/observability/propagation.md) | `correlation_id` across 6 transports; `run_id` via env `GAWAIN_RUN_ID`; `attempt` semantics |
| [`agentflow/observability/aggregation.md`](agentflow/observability/aggregation.md) | Per-run evidence layout; how the verifier greps |
| [`agentflow/observability/evidence.md`](agentflow/observability/evidence.md) | 8 verifier checks with bypass vectors; 12-line worked example; 10-question reconstruction table |

Workers writing integration code: load `context.md` + `events.md` +
`propagation.md` before writing any logging call. Verifier workers: load
`evidence.md` end-to-end as the adversarial checklist. The orchestrator
never greps logs itself — it dispatches a verifier worker with
`evidence.md` as the mandate.
