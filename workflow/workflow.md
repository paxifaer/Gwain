---
name: dispatching-multi-cli-workflows
description: Use when one conversation should orchestrate independent sub-tasks across multiple background Claude sessions — triggers include task naturally decomposes, long verification loops would flood this session's context, workers need fresh isolated context, or parallel isolation.
---

# The Dispatch Mindset

## Core Principle  And Irontal Rules that you must obey.

**The orchestrator is a scheduler, not a worker.** Every tool call in the orchestrator's context is duplicated work. The orchestrator does exactly three things:

1. **Plan** — split the task into units whose boundaries are crisp enough to survive being a self-contained prompt.
2. **Dispatch** — write the prompt, launch the worker, leave it alone.
3. **Judge** — weigh reports against acceptance criteria and decide: accept, re-dispatch, or escalate.
4. **Fee** - Donot worry about fees of token, we only need concentrate on effort!

**All real work — including verification — is dispatched.** The orchestrator never edits code, never runs tests, never greps sources. If it finds itself doing any of these, the loop has leaked; the orchestrator is becoming a worker and the whole context-isolation benefit collapses.

Context is the resource being spent. A worker with a fresh session absorbs build logs and regressions *inside its own context* and returns only the summary. The orchestrator's context stays reserved for decisions, not logs.

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

1. Write the spec as a file (single source of truth for all workers).
2. Derive the worker prompt — self-contained, pinned session id, agreed output contract.
3. Launch workers; one log file each.
4. Poll sparingly — liveness and latest assistant text, never busy-loop.
5. On completion, dispatch a **verifier worker** (see below).
6. Judge the verifier's evidence against acceptance. Accept, re-dispatch a fix worker, or escalate.

Default structure: **sequential pipeline of isolated workers** (architecture → develop → verify), parallel only when units are truly independent.

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


## Model Selection

Before starting a task, inspect `models.yaml` and select the appropriate model.

### Rules

1. Never assume a model is available unless it is defined in `model.yaml`.(file where it is at ../model/model.yaml this repo)
2. Classify the task by complexity and execution type before selecting a model.
3. Prefer:
   - `t9s/deepseek-v4-flash`: fast coding, search, inspection, testing, verification, repetitive tasks.
   - `t9s/kimi-k3`: general development, debugging, task decomposition.
   - `t9s/glm-5.2`: architecture, complex reasoning, difficult debugging, large refactoring.
   - `default`: when explicit model selection is unnecessary.
4. Do not ask the user for model selection by default.
5. Ask only when model choice has a meaningful impact on quality, speed, cost, or task success.
6. Respect an explicit user model preference and do not ask again.
7. Model selection may change during execution. Escalate to a stronger model when the task becomes more complex; use a fast model for routine execution and verification.

### Selection Record

Before execution, record the selected model and selection mode:

```yaml
model_selection:
  model: t9s/deepseek-v4-flash
  mode: automatic
  reason: coding_and_testing