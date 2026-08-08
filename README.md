# Gawain

Orchestrator-first workflow dispatch: one conversation runs multiple independent sub-tasks
across background sessions, keeping its own context for decisions instead of logs.

## Core principle

**The orchestrator is a scheduler, not a worker.** It does exactly three things:
plan, dispatch, judge. All real work — including verification — is dispatched to
isolated worker sessions. Context is the resource being spent; workers absorb stdout,
logs, and test runs inside their own sessions and return only summaries.

## Contents

- [`workflow/workflow.md`](workflow/workflow.md) — the full methodology: prompt design,
  dispatch loop, output contracts, adversarial verification, escalation rules,
  failure modes and anti-patterns.

## Quick guide

1. **Plan** — split the task into self-contained units.
2. **Dispatch** — write a complete prompt (who / what / why / constraints / inputs /
   output contract), launch the worker, leave it alone.
3. **Verify** — dispatch an adversarial verifier that tries to *disprove* the work.
4. **Judge** — the orchestrator's only own task: does the evidence satisfy acceptance?

Escalate when a worker blocks on an uncovered judgment call, a destructive action is
needed, or reports contradict accepted behavior.

## Philosophy

> Tokens are not the limit. Our token budget lets us replace effort, time, and context
> with better use of isolation: more sessions, not more context per session.