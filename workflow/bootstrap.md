# Gawain Bootstrap — read this first

You are an agent working in or under `workflow/Gawain`. This file is the ONLY
must-load entry point. Everything else lazy-loads via the classifier below.
Full rule index: [`rule-map.md`](rule-map.md).

## What Gawain is

An orchestrator-first dispatch workflow. The orchestrator does exactly three
things — Plan, Dispatch, Judge — and never edits code, runs tests, or greps
sources itself. All real work, including verification, runs in isolated worker
sessions. The normative methodology (铁律) is [`workflow.md`](workflow.md).

## Hard constraints (every agent, always)

1. NEVER `git push` unless the human explicitly instructs it in the current session.
2. NEVER add AI attribution to commits — no "Co-Authored-By" AI lines, no bot markers.
3. Workers run non-interactively: you cannot ask the user questions. If your prompt
   leaves a judgment call open, finish what you can and record an ESCALATE in your
   final message instead of guessing.
4. Before any git touchpoint, run the HEAD-guard: `git log --oneline -1 && git status --short`.
5. Your write-set is bounded by your prompt. Report every file you created or modified
   (with line numbers) in your final message. Creating files outside the declared
   write-set is a contract violation.

## Task classifier — four questions, in order

1. **Will you plan / dispatch / judge work?** → Read [`workflow.md`](workflow.md) in
   full before doing anything else.
2. **Does the task have a task-state layout?** (`task.md` + `state.md` + `decisions.md`
   + `evaluation.md` + `sync/`) → Read [`discussion-sync/protocol.md`](discussion-sync/protocol.md).
3. **Does `task.md` contain `risk: high`?** → protocol.md §9 (Reasoning Ledger) is
   mandatory and the layout is not opt-in. Workers: symbols listed in the task's
   `state.md` under `## Blocked` are untouchable; needing to modify one is an
   ESCALATE trigger.
4. **Will you write code that participates in a cross-boundary integration test?**
   (multi-process, multi-machine, multi-protocol calls: frontend↔backend,
   cloud↔robot, RPC, zenoh, Tauri invoke, WebSocket, IPC) → Read
   [`agentflow/observability/README.md`](agentflow/observability/README.md) and the
   component files it points to (`context.md`, `events.md`, `propagation.md`).
   Your code MUST emit FAIL/ERROR/STATE events that satisfy the 8 traceability
   checks in [`agentflow/observability/evidence.md`](agentflow/observability/evidence.md);
   the verifier worker dispatched after you will adversarially check this. Adding
   new mandatory fields/checks is additive; removing or relaxing one is an
   ESCALATE trigger.

No to all four → you are a plain worker; follow your prompt's output contract
(see workflow.md §Output Contract).

## Recovery after Auto-Compact / session restart

**Context memory is not workflow state.** After any compact or fresh start:

1. Re-read this file.
2. Re-run the classifier above; lazy-load whatever it points to.
3. If a task directory exists, reconstruct state from files in this order:
   `task.md` → `state.md` (≤60 lines; it IS the recovery payload) →
   `decisions.md` / `evaluation.md` as needed.
4. Before acting, state your phase and next action in one line
   (e.g. "phase: verify worker W3; next: read its final message").
5. Never infer which rules apply from conversational memory — infer from this
   file, [`rule-map.md`](rule-map.md), and the task's files.

## Runtime Driver (SessionStart hook)

A read-only SessionStart hook (`scripts/gawain-session-start.sh`) runs when a
Claude Code session starts under this repo root. It scans
`workflow/Gawain/workflow/handoffs/*/sync/*.yaml`, lists payloads whose
`status:` is `pending`, and warns about `missing_sync` gaps in numeric IDs.
Its output is injected into the agent's context at startup.

It does NOT auto-ingest: pending payloads are still applied by explicitly
running `prompts/PROMPT-orch-ingest.md` per the bootstrap chain. It does NOT
modify any file, so task state is never mutated by the hook.

Debug / disable: the hook is registered in
`/home/abc/work/ai-stack/.claude/settings.json` under `hooks.SessionStart`.
To disable, delete that block (or the whole `"hooks"` object). To run it
manually: `scripts/gawain-session-start.sh --verbose`.

Apply pending syncs by following
[`discussion-sync/protocol.md`](discussion-sync/protocol.md) and ingesting via
`discussion-sync/prompts/PROMPT-orch-ingest.md`.
