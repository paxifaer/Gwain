<!--
task.md — task definition for an opting-in task.

USAGE
  Copy this file to <task>/task.md and fill in the fields.
  This file is mostly static; ingest mutates it ONLY by appending CONFIRMED
  `requirements` entries to the § Requirements list (R-XXX).
  Goal / Scope / Acceptance Criteria should not change after task start; if
  they do, that's a new task, not a mutation of this one.

FIELD
  task_id: the kebab-case identifier matching the <task> directory name.
  This ID is referenced by every sync payload (sync_id.task_id) and by
  ingest when it scans the ledger.
-->

task_id: <task-id>

# <Task Title>

## Goal

One paragraph: what this task accomplishes and why it matters. State the
outcome, not the work.

## Scope

What this task touches and what it deliberately does NOT touch. A reviewer
should be able to read this section and decide whether a proposed change
is in- or out-of-scope without further clarification.

## Requirements

Requirements are R-XXX entries, one per line, format:
`- R-XXX — <requirement content> — <reason / source>`

When a sync payload contains a CONFIRMED `requirements` entry and ingest
dispositions it ACCEPT, ingest appends the entry here using the next free
R-XXX number.

- R-001 — <example requirement> — <why>

## Acceptance Criteria

Bullet list of independently-checkable criteria. Each criterion must be
verifiable by a third party (the V1 verifier) without further context.

- [ ] <criterion 1>
- [ ] <criterion 2>
- [ ] <criterion 3>
