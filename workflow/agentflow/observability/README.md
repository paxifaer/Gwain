# AgentFlow Observability — Integration Traceability Contract

This submodule is the **single source of truth** for code-level traceability
in code produced by Gawain-dispatched workers. It is the *execution
capability*: structured logging that lets a verifier reconstruct a
multi-machine, multi-process call chain after it fails — without
OpenTelemetry, Elasticsearch, Loki, Kafka, or any new database/service.

## Boundary with Gawain workflow policy

This submodule owns **HOW** to emit traceable logs. It does NOT own:

- WHEN workers log (recording triggers, mandatory log points per scene) —
  workflow policy, see `workflow.md §Verification` and the scene-specific
  tables in [`events.md`](events.md).
- WHETHER real external dependencies are exercised (no mocks/fakes) —
  workflow policy, see `workflow.md §Dispatch Loop` and the testing rule.
- WHETHER a FAIL constitutes a test failure — workflow policy, decided
  by the verifier worker per the original task's acceptance criteria.
- WHETHER the worker's test suite passes — workflow policy, judged by
  the orchestrator per `workflow.md §Output Contract`.
- WHETHER the verifier accepts — workflow policy, judged by the
  orchestrator per `workflow.md §Verification`.

The contract this submodule exposes to the workflow layer is:

> **When a worker writes code that participates in a cross-boundary
> integration test, the code MUST emit FAIL/ERROR/STATE events that
> satisfy the 8 traceability checks in [`evidence.md`](evidence.md).**

## Naming convention — language-agnostic interface

Workers write logging code in whatever language the task requires
(Rust/Python/JS/Go/…). This submodule defines a **naming convention**,
not a runtime library. The convention is exposed as logical interface
names workers MUST honor in their logging calls:

| Interface | What the worker logs | Event kind |
|---|---|---|
| `agentflow.log.start_operation` | STATE event: `from_state=idle to_state=in_progress` + business trigger + fresh `correlation_id` (or `from_state=no_corr to_state=corr_assigned` if inbound had none) | STATE |
| `agentflow.log.propagate` | Cross-boundary call carries `correlation_id` via the transport-specific mechanism in [`propagation.md`](propagation.md) | (implicit — verified at the next hop) |
| `agentflow.log.fail` | FAIL event with common + FAIL-specific fields from [`field-model.md`](context.md) | FAIL |
| `agentflow.log.error` | ERROR event with common + ERROR-specific fields | ERROR |
| `agentflow.log.state` | STATE event with common + STATE-specific fields | STATE |

These are NOT function calls. They are labels the verifier greps for
when reconstructing a run. Workers may implement them via `tracing::`
macros, Python `logging.exception`, JS `console.error` with structured
args, or any other framework — the field set in [`context.md`](context.md)
is what must appear, not the call shape.

## 8 verifier checks at a glance

The verifier worker adversarially checks these 8 dimensions. The full
checklist with bypass vectors is in [`evidence.md`](evidence.md).

| # | Check | What "pass" means |
|---|---|---|
| 1 | Log presence | Every scene-specific mandatory log point in `events.md` appears with a real `file:line`. |
| 2 | Correlation correctness | Every event in the trace has `correlation_id`. If inbound had none, a `corr_assigned` STATE event exists. |
| 3 | Identity correctness | Events use `service` + `instance_id` (+ `device_id` on robot scene) as stable identity. `peer_addr` is supplementary only, never the primary key. IP is NEVER identity. |
| 4 | Failure semantics | Every FAIL event has `caller→callee`, `operation`, `phase`, `error_class`, `error_message+cause`. `phase=retry_exhausted` on budget exhaustion. |
| 5 | Retry semantics | `attempt` field is 1-indexed, propagates across hops, downstream services do NOT increment it. |
| 6 | Cause preservation | No `String(error)` / `format!("{}", e)` / `str(e)` patterns in source. Every error chain preserves `cause` + stack. |
| 7 | First-failure reconstruction | Verifier can identify `first_failure`, `downstream_failures`, `final_failure` from logs alone (see [`events.md#first-failure`](events.md#first-failure)). |
| 8 | Scope completeness | All services in the run share `run_id` from env `GAWAIN_RUN_ID`. No service logged `run_id=prod` during an integration test run. |

A missing check fails the run.

## File index

| File | Component | What it defines |
|---|---|---|
| [`context.md`](context.md) | 上下文 / Context | Identity model (8 common fields + scene-specific stable IDs); IP NOT identity; field form |
| [`events.md`](events.md) | 事件 / Events | FAIL/ERROR/STATE taxonomy; level rules; scene-specific mandatory log points; error-passthrough rule; **first-failure principle** |
| [`propagation.md`](propagation.md) | 传播 / Propagation | `correlation_id` across 6 transports; `run_id` via env; `attempt` semantics |
| [`aggregation.md`](aggregation.md) | 汇聚 / Aggregation | Per-run evidence organization; log layout for verifier replay |
| [`evidence.md`](evidence.md) | 证据 / Evidence | 8 verifier checks with bypass vectors; 12-line worked example; 10-question reconstruction table |

## Who must read what

- **Worker writing integration code** → read `context.md` + `events.md` +
  `propagation.md` before writing any logging call.
- **Verifier worker** → read `evidence.md` end-to-end; cross-reference
  `events.md` for scene-specific mandatory points.
- **Orchestrator** → never greps logs itself. Dispatches a verifier
  worker with `evidence.md` as the adversarial checklist.
- **Task spec writer** → when defining acceptance criteria for a
  cross-boundary integration task, link this README as the
  traceability requirement.

## What this submodule deliberately does NOT provide

- No runtime library, no SDK, no daemon, no file-watcher.
- No log aggregation backend. No log shipper. No schema registry.
- No opinion on log format (text key=value vs JSON vs structured
  fields — see `context.md §field-form`). The verifier greps field
  names, not JSON paths.
- No opinion on retry policy. `attempt` is per-hop at the entry
  service; per-hop retry budget is a P1 out-of-scope concern.

## Versioning

This contract is additive only. Once a verifier check ships, it stays.
Adding a new mandatory field requires bumping this README's "8
verifier checks" count and updating `evidence.md` — both are
normative. Removing or relaxing a check requires explicit user
approval (it's an ESCALATE trigger per `bootstrap.md`).
