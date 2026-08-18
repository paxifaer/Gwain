<!--
evaluation.md — task completion criteria.

USAGE
  Copy this file to <task>/evaluation.md. This file is mostly static; it
  is filled in at task start and consulted at task close by the verifier.

CRITERIA FORMAT
  Each criterion is a single bullet, written so a third party (the V1
  verifier) can check it independently without further context. Avoid
  compound criteria ("X and Y") — split them into two bullets so each
  can PASS/FAIL on its own.

  - [ ] <criterion>

EVALUATION
  At task close, the verifier marks each box PASS or FAIL with evidence
  (file:line, command output, or test name). A task is "done" iff every
  criterion PASSes. Any FAIL blocks task close; the Orchestrator either
  re-dispatches a fix worker or revises the criteria (with a sync payload
  if the task is opted-in).
-->

# Evaluation

- [ ] <criterion 1 — independently checkable>
- [ ] <criterion 2 — independently checkable>
- [ ] <criterion 3 — independently checkable>

## Verdicts

<!--
ENTRY FORMAT (one line per entry, grep-friendly)
  - V-XXX — target: <single ledger ID> — method: <how executed> — expected: <...> — actual: <...> — verdict: <PASS|FAIL> — evidence: <path> — author: <verifier-session-id>

Verdicts may ONLY be written by verifier sessions (never by the worker whose output is being judged); `target:` is mandatory and exactly one ID — an empty or multi-target verdict is invalid; PASS means "the workflow may continue using the target under current evidence", NOT mathematical proof; record both expected and actual — "I checked it" prose is not a verdict.
-->

- (none yet)

## Implementation Map

<!--
ENTRY FORMAT (one line per entry, grep-friendly)
  - <D/C ID> ↔ <file>::<symbol> (line range advisory only)

Written by develop workers; granularity is the function symbol (line numbers drift, keep them advisory only); each high-risk derivation/constraint should eventually map to at least one symbol.
-->

- (none yet)
