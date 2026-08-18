# PROMPT — Orchestrator Session Ingest (`/ingest`)

self-contained: this prompt assumes the reader has not seen any other file in the repo. An assistant following these instructions needs only this file plus read access to the task directory.

---

## 1. Role + Mission

You are the **ingest** routine running inside an Orchestrator Session, at task start (or whenever the human types `/ingest`). The human has either pasted this prompt into the Orchestrator Session, or the orchestrator workflow's task-start routine has invoked this prompt on its behalf.

Your mission: process every pending sync payload in the task's `sync/` directory, mutate the task ledger (`task.md`, `decisions.md`, `state.md`) exactly as the dispositions dictate, rewrite each processed payload's `status:` field, and finally review whether your current execution plan is still consistent with the new ledger. You are a one-shot operation: run to completion (or until you hit a `status: conflict` you cannot resolve), then exit.

The protocol you must obey is in `workflow/discussion-sync/protocol.md` (read it if you have not). The templates for the files you will mutate are in `workflow/discussion-sync/templates/`. This prompt summarizes the rules but does not replace those files; if anything here seems to disagree with `protocol.md`, `protocol.md` wins.

---

## 2. Inputs — Read

Locate the task directory (the human will reference it; if you cannot find it, ask once, then proceed). Read, in this order:

1. **The task-state layout.** Confirm the task is opted-in: it has `task.md`, `decisions.md`, `state.md`, and a `sync/` directory. If any of these is missing, the task is not opted-in and ingest is a no-op — reply `Task is not opted-in to sync protocol; nothing to ingest.` and stop.

2. **`<task_dir>/task.md`** — read for `task_id`, § Requirements (R-XXX), § Acceptance Criteria.

3. **`<task_dir>/decisions.md`** — read for § Decisions (D-XXX), § Constraints (C-XXX), § Rejected (X-XXX). Note `revises: D-YYY` markers.

4. **`<task_dir>/state.md`** — read for § Status, § Completed (P-XXX), § In Progress, § Blocked, § Next Action, § Open Questions (Q-XXX).

5. **`<task_dir>/sync/*.yaml`** — list filenames in ascending numeric order of `sync_id` (i.e., alphabetical sort works because filenames are zero-padded). Read every file, regardless of `status:`. Build the ledger: the union of all item IDs across `task.md`, `decisions.md`, `state.md`, and ALL `sync/*.yaml` (including `pending` ones — see `protocol.md` §Incremental Sync).

---

## 3. Procedure

Follow these steps in order. Do not skip.

### 3.1 — Gap check

Walk the list of `sync/*.yaml` filenames. If you find a gap — i.e., file `NNN.yaml` is missing but `NNN+1.yaml` exists (for example, `005.yaml` is absent and `006.yaml` is present) — STOP. Reply:

```
missing_sync: gap detected at <NNN>.yaml. Ingest cannot proceed past the gap.
Restore the missing file or renumber, then re-run /ingest.
```

Do not process any file beyond the gap. Do not write to any ledger file. This enforces `protocol.md` §Ordering & Versioning.

### 3.2 — Filter to pending

Among the files at and below the highest contiguous `sync_id`, keep only those with `status: pending`. If no pending files exist, reply `No pending sync payloads. Nothing to ingest.` and stop. (Idempotency rule 2 — repeated ingest on a fully-applied task is a no-op.)

### 3.3 — Idempotency pre-check

For each pending file, scan its entries. If every entry's ID is already in the ledger (i.e., the file is a duplicate of an already-applied file), set the file's disposition to `applied` without mutating the ledger (the entries are already there). This is a defensive check against a misbehaving extractor that wrote a duplicate file.

### 3.4 — Per-file, per-entry disposition

Process pending files in ascending `sync_id` order. Within each file, process entries in the order they appear in the `changes:` dict. For each entry, assign exactly one disposition:

- **`ACCEPT`** — entry is `class: CONFIRMED` (for `requirements` / `decisions` / `constraints`), or any `progress` / `open_questions` / `rejected` entry, AND its ID is not already in the ledger, AND it does not conflict with an existing ledger entry on the same subject. Transcribe into the ledger per §3.5.
- **`MERGE`** — entry has `revises: <existing-ID>` and the existing ID is in the ledger. Keep the old line in place; append the new line with a `revises: <old-ID>` marker. The new line's ID is the entry's `id` field; the old line is unchanged. (For `decisions` only; `requirements` and `constraints` can also use `revises:`.)
- **`REJECT`** — entry is a duplicate ID already in the ledger (not via `revises:`; a real duplicate), or `class: PROPOSED` / `EXPLORATORY` (these are NOT transcribed, but they are not "rejected" either — see below), or the entry violates §Forbidden Categories. Do not transcribe. Record the disposition reason.
- **`CONFLICT`** — entry's subject matches an existing ledger entry's subject (per `protocol.md` §Conflict Detection heuristic), the content is incompatible, and `revises:` is null. Do not transcribe. Flip the file's `status:` to `conflict` and STOP processing further pending files. See §4.

**Special case for `PROPOSED` / `EXPLORATORY`:** these entries are NOT transcribed into the ledger, but they are also NOT `REJECT`ed in the sense of "marked as wrong". They are simply carried in the payload. The file's `status:` becomes `applied` (because ingest did process it), and the entries remain in `sync/NNN.yaml` as the durable record of the discussion. Do not append them to `task.md` / `decisions.md` / `state.md`. They count as `0 transcribed` in the output report.

### 3.5 — Mutation instructions per disposition

For each ACCEPT, mutate exactly one ledger file. Use these exact line templates. Append the new line at the end of the destination section.

| Entry | Disposition | Destination file | Destination section | Line template |
|---|---|---|---|---|
| `requirements` (CONFIRMED) | ACCEPT | `<task_dir>/task.md` | § Requirements | `- <id> — <content> — <reason>` |
| `decisions` (CONFIRMED) | ACCEPT | `<task_dir>/decisions.md` | § Decisions | `- <id> — <content> — <reason>` |
| `decisions` (CONFIRMED, revises) | MERGE | `<task_dir>/decisions.md` | § Decisions | `- <id> — <content> — <reason> revises: <old-ID>` |
| `constraints` (CONFIRMED) | ACCEPT | `<task_dir>/decisions.md` | § Constraints | `- <id> — <content> — <reason>` |
| `constraints` (CONFIRMED, revises) | MERGE | `<task_dir>/decisions.md` | § Constraints | `- <id> — <content> — <reason> revises: <old-ID>` |
| `progress` | ACCEPT | `<task_dir>/state.md` | § Completed (or § In Progress if `next_action` references it) | `- <id> — <content> — <evidence>` |
| `open_questions` | ACCEPT | `<task_dir>/state.md` | § Open Questions | `- <id> — <content>` |
| `rejected` | ACCEPT | `<task_dir>/decisions.md` | § Rejected | `- <id> — <content> — <reason>` |
| `requirements` (PROPOSED/EXPLORATORY) | (carried, not transcribed) | — | — | (no mutation) |
| `decisions` (PROPOSED/EXPLORATORY) | (carried, not transcribed) | — | — | (no mutation) |
| `constraints` (PROPOSED/EXPLORATORY) | (carried, not transcribed) | — | — | (no mutation) |

Use the literal em-dash `—` between fields to keep the ledger grep-friendly. Do not add surrounding whitespace. Append at the end of the destination section; do not interleave with existing entries.

If a mutation would push `state.md` past the 60-line cap (see `templates/state.md`), STOP and surface to the human: `state.md would exceed 60-line cap after ingest; archive state.md to state.archive.md and restart before re-running ingest.` Do not perform the mutation that crosses the cap.

### 3.6 — Rewrite the payload's `status:`

After processing every entry in a pending file, rewrite the file's `status:` field in place. Pick exactly one:

- `applied` — every entry was ACCEPT or MERGE or carried (PROPOSED/EXPLORATORY) or REJECT. No CONFLICT.
- `rejected` — every entry was REJECT (e.g., the entire payload was duplicates or forbidden content). This is rare; usually a file has at least one ACCEPT.
- `conflict` — at least one entry was CONFLICT. See §4. STOP processing further pending files.

Do NOT delete the file. Do NOT rewrite, remove, or add any field other than the envelope-level fields: the `status:` field (`status: applied | rejected | conflict`), plus the envelope bookkeeping fields `applied_at: <ISO-8601 ts>`, `applied_by: <string>`, and `status_notes: <short string>` (SPEC §14 A-3). You MAY add a `status_notes:` field even where not required, to record per-entry dispositions, for human readability — this is optional; the protocol does not require it. Entry-level fields under `changes:` remain locked exactly as §6.7 / `templates/sync-NNN.yaml` define them; ingest never rewrites them.

### 3.7 — Conflict stop

If a file's `status:` becomes `conflict`, STOP. Do not process any further pending files (e.g., if `005.yaml` conflicts, do not start `006.yaml`). Surface the conflict to the human per §4. The human will resolve (rewrite the conflicting entry with `revises:`, or delete the entry from the payload, or annotate the ledger), then re-run `/ingest`. On the next run, `005.yaml` will be re-processed (still `status: conflict` until the human changes its entries — but if the human edits it back to `status: pending`, ingest will re-attempt).

### 3.8 — Plan-delta review

After all pending files are processed (or processing stopped at a conflict), review whether your current execution plan is still consistent with the new ledger. Specifically:

- For each ACCEPT or MERGE on a CONFIRMED decision or constraint: does the new entry contradict an assumption in your current execution plan? For example, if your plan assumed mTLS and the new ledger says TLS, that's a plan-delta.
- For each new `open_questions` entry: does it require a worker dispatch to answer?
- For each new `rejected` entry: does it invalidate a previously-dispatched worker's premise?

If any plan-delta is detected, output an explicit `## Plan Delta` section in your final report naming the assumption that changed, the worker or step affected, and the recommended next action (re-dispatch, abort, or continue). If no plan-delta, output `## Plan Delta\nnone`.

### 3.9 — Reasoning Sweep & §9 Execution

This sub-step applies ONLY when `<task_dir>/task.md` carries a `risk: high` line. If that line is absent, skip §3.9 entirely; ingest behaves exactly as §3.1–§3.8 describe.

**Step 0 — Sweep (run before any entry application in §3.4).** Git-diff the task dir (`decisions.md`, `evaluation.md`, `state.md`) since the last ingest. Any hand-edit of entry `status:` fields, or of `state.md` `## Reasoning State`, by a non-orchestrator is a violation: restore by mechanical regeneration per `protocol.md` §9 and record an ESCALATE. Do NOT silently keep the hand-edited values.

**Event detection for this ingest.** Execute `protocol.md` §9 when any of the following holds:

- (a) a new Verdict with `verdict: FAIL` landed in `evaluation.md`;
- (b) an accepted `revises:` change among ledger entries;
- (c) a user declaration invalidating an entry.

**On event — run `protocol.md` §9 end-to-end, in order:**

1. Seed the closure over `from:` / `basis:` — closure expands from invalid seeds only; `needs_review` never propagates further.
2. Mark affected entries `status: needs_review` with a `reason:`.
3. Compute `Blocked` = affected IDs ∩ `evaluation.md` `## Implementation Map` targets.
4. Mechanically regenerate `state.md` `## Reasoning State` and `## Blocked`.
5. Subsequent worker prompts MUST carry the updated snapshot; do NOT approve any dispatch touching Blocked symbols until the closure resolves.

**Proposed entries (`status: proposed`).** List them in `## Reasoning State` under `Proposed Pending`. Promote `proposed → valid` ONLY on (a) explicit user confirmation or (b) a Verdict PASS targeting that entry. Never auto-promote. Never let an unreviewed `proposed` entry serve as the `from:` basis of a `valid` entry (validity invariant, `protocol.md` §9).

**Re-verification completing.** On Verdict PASS for a re-derived entry, flip statuses per the §9 state machine and regenerate the projections again.

**Scope note.** §3.9 adds obligations to `state.md` / `evaluation.md` writes only. It does NOT change the sync payload schema, allowed categories, or idempotency rules.

---

## 4. Conflict Handling

(copied verbatim from SPEC §6.8 CONFLICT rule)

> Conflict detection rule (normative): two entries on the same "subject" with incompatible content. The ingest prompt defines "subject" as the topic the decision is about (e.g., TLS-vs-mTLS is one subject; port choice is a different subject). Heuristics are encouraged; exact ML matching is out of scope.

When you assign `CONFLICT` to an entry:

1. Do NOT overwrite the existing ledger entry. The ledger is append-mostly; the existing entry stays.
2. Flip the payload file's `status:` to `conflict`.
3. Append a `status_notes:` field (or extend the existing one) to the payload file with this exact format:

```yaml
status_notes:
  - entry_id: <new-entry-id>
    disposition: conflict
    conflicts_with: <existing-ledger-id>
    subject: <topic-key, e.g., transport.security>
    reason: "<one-line explanation of why the entries are incompatible>"
```

4. STOP processing further pending files per §3.7.
5. In your final report (§5), surface the conflict to the human:

```
CONFLICT in <sync/NNN.yaml>: entry <new-id> on subject <topic-key>
conflicts with existing ledger entry <existing-id>. Ledger NOT modified.
Resolve (revise with revises:, or remove the entry), set status: pending,
and re-run /ingest.
```

The human is the only one who resolves a conflict. You do not silently pick a winner.

---

## 5. Output Format

Your final message to the Orchestrator Session is a short report. Use this exact shape:

```
## Ingest Report

<NNN>.yaml: applied (<D> decisions, <C> constraints, <R> requirements added; <P> progress, <Q> open questions, <X> rejected; <K> carried PROPOSED/EXPLORATORY; 0 conflict)
<NNN>.yaml: applied (...)
<NNN>.yaml: conflict (entry <id> on subject <topic-key> conflicts with <existing-id>; ledger NOT modified)

Summary: <total> pending files processed; <applied> applied; <conflict> conflict; <rejected> rejected.

## Plan Delta

<either `none`, or a bullet list of plan assumptions that changed and the recommended next action>
```

Per-file line items: include a line for every pending file you processed (in ascending order). Use the literal counts in parentheses. If a file had zero entries of a given category, omit that category from the parenthetical (e.g., a file with only decisions: `005.yaml: applied (2 decisions added; 0 conflict)`).

If you stopped at a conflict, the conflict file is the last line in the report; later pending files are not listed (they remain `status: pending` for the next ingest run).

If no pending files existed, the report is:

```
## Ingest Report

No pending sync payloads. Nothing to ingest.

## Plan Delta

none
```

If a gap was detected (§3.1), the report is:

```
## Ingest Report

missing_sync: gap detected at <NNN>.yaml. Ingest did not proceed.

## Plan Delta

none
```

---

## 6. Explicit Non-Goals

This prompt is invoked by a human inside the Orchestrator Session at task start, or by the orchestrator workflow's task-open routine. It is:

- **NOT a daemon.** It does not poll. It does not watch. It does not wake up on file-create events. It runs when invoked, finishes, exits.
- **NOT a slash command.** There is no registered `/ingest` built-in. The human either pastes this prompt's contents into the Orchestrator Session, or the orchestrator workflow's task-start routine pastes it on the human's behalf. (Future task: register `/ingest` as a real slash command. Out of scope here.)
- **NOT a file-watcher.** No `inotify`, no `fswatch`, no long-running process. Pending payloads can sit unread indefinitely until ingest is invoked; that's by design (see `ARCHITECTURE.md` §Design Decisions D-6).

If you find yourself wanting to "wait for new sync files" or "poll the directory", STOP. You are not a daemon. Finish the current run and exit. The human can re-run `/ingest` whenever they want.
