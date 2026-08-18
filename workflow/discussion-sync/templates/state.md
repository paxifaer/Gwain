<!--
state.md — short, mutable snapshot of task progress.

USAGE
  Copy this file to <task>/state.md and keep it current.
  This file is mutated by ingest (which appends CONFIRMED `progress` and
  `open_questions` entries to the relevant sections) AND by the
  Orchestrator during task execution (which updates Status / In Progress /
  Blocked / Next Action as work proceeds).

CAP
  This file MUST stay ≤ 60 lines. If it grows past the cap, archive the
  Completed and Blocked history to <task>/state.archive.md and restart
  state.md with only In Progress / Next Action / Open Questions carried
  forward. The cap exists so a glance at state.md is always informative;
  history lives in the archive, not in the live file.

ENTRY FORMAT
  - P-XXX — <what was done> — <evidence path or link>
  - Q-XXX — <unresolved question>
  Status (one word): idle | in_progress | blocked | done
-->

# State

## Status

idle

## Reasoning State

<!-- Derived projection. Written ONLY by the orchestrator (mechanical rewrite after each ingest / invalidation run). Read-only for workers. Frontier-only: list only leaf derivations (those with no valid dependents); interior nodes lazy-load from decisions.md. Whole file must stay ≤ 60 lines. -->
- Goal: see task.md
- Valid Assumptions: (one line each: A-XXX — content — source) or (none)
- Valid Derivations (frontier): (DER-XXX — one-line conclusion) or (none)
- Needs Review: (ID — reason: <triggering upstream ID>) or (none)
- Invalid: (ID — reason: <one phrase>) or (none)
- Open Verifications: (V-XXX → target ID) or (none)
- Proposed Pending: (ID — awaiting user confirmation / verdict) or (none)

## Completed

- (none yet)

## In Progress

- (none)

## Blocked

<!-- Populated by orchestrator: file::symbol symbols mapped (via evaluation.md ## Implementation Map) to invalid/needs_review ledger targets. Workers MUST NOT modify listed symbols; ESCALATE if the task requires touching them. -->
- (none)

## Next Action

(one line — the single next thing the Orchestrator should do)

## Open Questions

- (none)
