# Expected outcome — after transcript 01 (`chitchat` only)

**Scenario:** SPEC §8 **A1**. The Discussion (transcripts/01-chitchat.md) is
pure chitchat / off-topic banter.

## What the extractor does

1. Reads the ledger — `task.md`, `decisions.md`, `state.md`, and every
   `sync/*.yaml` (PROMPT-disc-extractor.md §1-§2). At this point there are no
   D-/P-/Q-/X- entries anywhere.
2. Scans the recent Discussion. Every statement is classified
   `IRRELEVANT` — not task-relevant. Per protocol.md §Entry Classes &
   Dispositions, `IRRELEVANT` entries MUST NOT appear in the payload at all.
   PROMPT-disc-extractor.md §3 **R-C** → they are dropped silently.
3. Zero new entries remain.

## Why no file is written

SPEC §6.6 rule 1 (= protocol.md §Idempotency rule 1; also protocol.md R-1),
normative:

> If the extractor finds zero new content to add, it MUST NOT write any
> `sync/NNN.yaml` file. It replies to the user with text like "no new
> task-relevant changes since last sync" and updates nothing on disk.

## Extractor reply (Termination Outcome A — PROMPT-disc §6)

```
No new task-relevant changes since last sync.
```

## Resulting disk state

- No `sync/NNN.yaml` is created; `sync/` remains empty at this point.
- `task.md`, `decisions.md`, `state.md` are untouched (R-G — extractor
  mutates nothing but its at-most-one new sync file).
- R-9 also covers this: chitchat / social content is never emitted.

## Verdict

Anchors the expected outcome of SPEC §8 scenario **A1**.