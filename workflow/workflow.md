---
name: dispatching-multi-cli-workflows
description: Use when one conversation should orchestrate independent sub-tasks across multiple background Claude sessions — triggers include task naturally decomposes, long verification loops would flood this session's context, workers need fresh isolated context, or parallel isolation.
---

Entry point: fresh agents and post-compact recovery start at [`bootstrap.md`](bootstrap.md); the full rule index is [`rule-map.md`](rule-map.md). This file remains the normative methodology.

# The Dispatch Mindset

## Core Principle  And Irontal Rules that you must obey.

**The orchestrator is a scheduler, not a worker.** Every tool call in the orchestrator's context is duplicated work. The orchestrator does exactly three things:

1. **Plan** — split the task into units whose boundaries are crisp enough to survive being a self-contained prompt.
2. **Dispatch** — write the prompt, launch the worker, leave it alone.
3. **Judge** — weigh reports against acceptance criteria and decide: accept, re-dispatch, or escalate.
4. **Fee** - Donot worry about fees of token, we only need concentrate on effort!

**All real work — including verification — is dispatched.** The orchestrator never edits code, never runs tests, never greps sources. If it finds itself doing any of these, the loop has leaked; the orchestrator is becoming a worker and the whole context-isolation benefit collapses.

Context is the resource being spent. A worker with a fresh session absorbs build logs and regressions *inside its own context* and returns only the summary. The orchestrator's context stays reserved for decisions, not logs.

A worker with a fresh session may delegate bounded supporting work to Subagents during task execution.

```text
Scheduler → Worker → Subagent(s)
```

* **Scheduler** assigns the primary task.
* **Worker** owns the task and decides how to execute it.
* **Subagent** handles bounded supporting work such as exploration, search, analysis, experiments, or other context-heavy operations.
* The Worker remains responsible for evaluating Subagent results, integrating them, verifying the outcome, and reaching convergence.
* Subagents inherit the Worker's relevant permissions and constraints and must not be used to bypass workflow governance.
* Delegation is optional: use Subagents when they improve context isolation, efficiency, or reliability; do not delegate simple work unnecessarily.

> **The Scheduler decides who owns the task; the Worker decides whether and how to delegate supporting work.**


## Prompt Design — The Worker Can't Ask Back

A worker session reads the prompt once and runs to completion. It can't ask clarifying questions, share your conversation history, or see anything the prompt didn't say. The prompt must contain everything:

| Slot | Contents |
|---|---|
| Who | "You are the Develop workflow for feature X" |
| What | exact files, exact changes or the bug's symptoms |
| Why | what acceptance means — how success is judged |
| Constraints | read-only zones, permission whitelist/blacklist, time cap |
| Inputs | paths to read, prior handoffs, fixtures |
| Output contract | exact final-message shape (files changed, line numbers, per-test PASS/FAIL, regressions, escalations, elapsed) |

Any ambiguity the prompt leaves open gets resolved by the model, not by you. Every judgment call you're willing to make: resolve it in advance. Every one you want to keep: list as an escalation trigger.

## Dispatch Loop

1. Write the spec as a file (single source of truth for all workers): in the task directory when the task-state layout exists, otherwise in `handoffs/<task-name>/` of the working repo (one `SPEC-*.md` per task).
2. Derive the worker prompt — self-contained, pinned session id, agreed output contract; prepend the standard block from [`worker-preamble.md`](worker-preamble.md).
3. Launch workers; one log file each.
4. Poll sparingly — liveness and latest assistant text, never busy-loop.
5. On completion, dispatch a **verifier worker** (see below).
6. Judge the verifier's evidence against acceptance. Accept, re-dispatch a fix worker, or escalate.

Default structure: **sequential pipeline of isolated workers** (architecture → develop → verify), parallel only when units are truly independent.

## High-Risk Reasoning Gate

Most tasks fail from bad code; a minority fail from invalidated upstream reasoning silently propagating into correct-looking code. For that minority, use the task-state layout with frozen, user-approved acceptance criteria (see [`skills/febe-contract/SKILL.md`](../skills/febe-contract/SKILL.md)); the old reasoning-ledger subsystem (discussion-sync §9) was removed on 2026-10-22. The orchestrator decides ONCE, at Plan time, whether a task is high-risk:

Hard triggers — any one makes the task high-risk:
- The task will produce or modify formal derivations (equations, closed-form solutions, optimization objectives).
- The task modifies core control / kinematics / dynamics / scheduling / concurrency algorithms.

Soft indicators — two or more make it high-risk:
- Results will chain through ≥2 derivation levels.
- One wrong intermediate result would silently invalidate ≥2 downstream consumers.
- The task is expected to span sessions or subagent handoffs.
- Design "wiring" constraints (which signal feeds which computation) must survive implementation.

Rules:
- Judge by task structure, never by "the agent feels the task is complex".
- Default is the normal workflow. The user may force either direction.
- Record the decision as one line in task.md (or in the spec file for tasks without the task-state layout), e.g. `risk: high — triggers: H1, S3`.
- High-risk tasks MUST use the task-state layout (task.md / state.md / decisions.md / evaluation.md) — for them it is mandatory, not opt-in — and freeze user-approved acceptance criteria up front per [`skills/febe-contract/SKILL.md`](../skills/febe-contract/SKILL.md).
- Workers of high-risk tasks receive a Reasoning State snapshot inside their prompt and MUST NOT modify symbols listed in state.md `## Blocked`; needing to touch one is an escalation trigger.

## Output Contract — The Worker Writes For You

The worker's final message is not a chat; it's the payload. Demand:

- Files changed with line numbers and what changed
- Per-check results with actual output snippets
- Regression per-case PASS/FAIL
- Elapsed time and ESCALATEs (judgment calls the worker made alone)

Anything else is noise that costs the orchestrator's tokens.

## Verification Is Also a Worker

Do not verify by hand. The claim-checking greps and test reruns are real work — dispatch them as a **verifier session**.

The verifier's prompt contains:
- The acceptance criteria (from the original spec)
- The worker's reported changes (the file+line claims from its final message)
- A mandate to **disprove, not confirm**: "Find evidence that each claim is false." Adversarial framing kills the confirmation bias a "please verify" prompt breeds.

The verifier returns per-claim verdicts with evidence (actual grep output, actual test counts). The orchestrator then does the only thing it must do itself: **judge** — does this evidence satisfy acceptance?

**Recursion floor:** at minimum there are two free agents (worker, verifier) and one judgment (your decision). Spawning a third session to verify the verifier is reserved for high-stakes acceptances.

## Integration Traceability Contract

When a worker writes code that participates in a cross-boundary integration
test (multi-process, multi-machine, multi-protocol calls: frontend↔backend,
cloud↔robot, RPC, zenoh, Tauri invoke, WebSocket, IPC), the code MUST emit
FAIL/ERROR/STATE events that satisfy the Integration Traceability Contract
at [`agentflow/observability/`](agentflow/observability/README.md).

The submodule owns the *how* — field model (8 common fields + event-specific),
propagation (correlation_id across 6 transports, run_id via env, attempt
semantics), event taxonomy, **first-failure principle** (first_failure vs
downstream_failures vs final_failure), and the 8 verifier checks. The
workflow layer owns the *policy* — when to log, which scenes require which
points, whether real dependencies are exercised, whether a FAIL is a test
failure. The boundary is documented in the submodule's README.

The verifier worker dispatched after an integration-test task uses
[`agentflow/observability/evidence.md`](agentflow/observability/evidence.md)
as its adversarial checklist (8 traceability checks, each with a bypass
vector a strong worker might use to fake compliance and the countermeasure
that catches it). The orchestrator never greps logs itself — the
traceability check is dispatched as a verifier session, same as any other
verification work (see §Verification above).

Adding a new mandatory field or check is additive only and requires bumping
the "8 verifier checks" count in both `agentflow/observability/README.md`
and `evidence.md`. Removing or relaxing a check is an ESCALATE trigger
per `bootstrap.md` — the contract is intentionally sticky.

## When to Escalate

- Worker or verifier is blocked on a judgment call the prompt didn't cover
- A destructive or irreversible action is needed (overwrites, resets, schema drops, prod migrations)
- Reports contradict accepted behavior in an unexpected way (was it the change, or the acceptance?)

## Red Flags — Re-evaluate

- Orchestrator editing code or running greps (worker's job)
- Orchestrator verifying claims itself (verifier's job)
- Verifier prompted to "confirm" rather than "disprove"
- Prompt longer than the spec it came from — split the task
- More than ~5 workers active at once (attention exhausted)

## Failure Modes & Anti-Patterns

| Failure | Antidote |
|---|---|
| Worker fixes the wrong thing | prompt contained only the what, missed the why (acceptance) |
| Orchestrator context still flooded | demand output contract; workers return summaries not logs |
| Orchestrator "just quickly checks" | that's verification — dispatch a verifier |
| Verifier echoes the worker | it was told to confirm; re-prompt with adversarial mandate |
| Two workers merge-conflict | boundaries weren't independent — pipeline them |
| Micromanaging a live worker | prompt was wrong — kill it, improve prompt, relaunch |
| One mega-worker does everything | that's just a bigger conversation, context problem intact |
| Sharing context by name | workers can't see your session — files with contents, not "as discussed" |


## Model Selection (removed 2026-10-22)

Model routing belongs to the harness (see the repo's `AGENTS.md` / dispatch rules);
Gawain no longer maintains a model registry.

## Discussion Session Sync (removed 2026-10-22)

The sync subsystem (protocol, extractor/ingest prompts, templates, examples) was
deleted after the 2026-08-24 audit recorded zero adoption plus P0 defects. Use
`task.md` / `state.md` / `evaluation.md` for task state and
[`skills/febe-contract/templates/acceptance.md`](../skills/febe-contract/templates/acceptance.md)
for acceptance criteria.