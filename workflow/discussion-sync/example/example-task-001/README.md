# example-task-001 — worked example of Discussion ↔ Orchestrator sync

This directory is the W2 worked example for the `discussion-sync` protocol. It
runs one tiny task through the full sync life cycle: a human discusses in a
**Discussion Session**, `/sync` extracts a distilled payload, and an
**Orchestrator Session** digests it. Read it chronologically — every file below
is referenced in the order it matters.

Task files (copied from `templates/`):
- `task.md`, `state.md`, `decisions.md`, `evaluation.md` — the initial task
  state, before any sync. The ledger is empty of D-/P-/Q-/X- entries.

---

## Step 1 — Scenario A1 (chitchat): `/sync` writes nothing

Transcript: `transcripts/01-chitchat.md`. The Discussion is pure off-topic
conversation. The human types `/sync` → the Discussion Session behaves as if
`prompts/PROMPT-disc-extractor.md` had been invoked (protocol.md §The `/sync`
User Gesture).

Extractor reads the ledger, drops every statement as `IRRELEVANT`
(PROMPT §3 R-C), finds zero new entries, and per **protocol.md R-1 /
§Idempotency rule 1** (= SPEC §6.6 rule 1) writes **no** `sync/NNN.yaml` and
replies the fixed phrase. Outcome documented in
`expected/after-01-chitchat.md`. This anchors SPEC scenario **A1**.

## Step 2 — Scenario 2 (confirmed decision): payload `sync/001.yaml`

Transcript: `transcripts/02-decision-tls.md`. The user confirms: *"We pick TLS
over mTLS, because the cert lifecycle is simpler. Confirmed."* The extractor:
- classifies the statement `CONFIRMED` (PROMPT §3 R-A),
- assigns fresh `D-001` (protocol §ID Conventions),
- subject `transport.security`, no sibling entry on that subject →
  `revises: null` (protocol.md §Conflict Detection),
- writes the **only** payload this example ever produces:
  `sync/001.yaml` (`status: pending`; one `changes.decisions` entry).

The extractor's reply text is in
`expected/after-02-decision/extractor-reply.md`, and its output
`expected/after-02-decision/extractor-output.yaml` is **byte-identical** to
`sync/001.yaml`. This anchors SPEC scenario **A2**.

## Step 3 — Scenario A3 (exploration): `/sync` again writes nothing

Transcript: `transcripts/03-exploration-quic.md`. The user *explores* QUIC
("should we consider QUIC? unclear, need benchmarks") with no confirmation and
no intent-to-log signal, so the extractor classifies the musing `IRRELEVANT`
per SPEC §14 A-1 (Outcome A′ in `prompts/PROMPT-disc-extractor.md` §6;
protocol.md §Forbidden Categories row), replies the same no-changes text as
Step 1 (SPEC §14 A-2), and writes no file. Anchors SPEC scenario **A3**.

## Step 4 — Orchestrator ingest: `after-ingest/`

At Orchestrator task start the human pastes `prompts/PROMPT-orch-ingest.md`
(protocol.md §The Orchestrator Ingest Gesture, form (a)). Ingest reads
`sync/*.yaml` ascending, keeps only `status: pending` files (§3.2) → here
`sync/001.yaml`. It ACCEPTs `D-001` (§3.4) and:

- rewrites the payload → `after-ingest/sync-001-applied.yaml`
  (`status: applied` + `applied_at` + `status_notes`; §3.6),
- appends D-001 → `after-ingest/decisions.md`,
- reflects the new plan → `after-ingest/state.md`
  (`Status: in_progress`, `Next Action`, a Completed line referencing D-001),
- prints the report → `after-ingest/ingest-report.md` (§5:
  `001.yaml: applied (1 decision added; 0 rejected; 0 conflict)`, Plan Delta none).

---

## What this example demonstrates

One task, three SPEC §8 scenarios: **A1** (chitchat `/sync` → no file),
**A2** (confirmed decision `/sync` → `sync/001.yaml` → ingest → ledger), and
**A3** (exploratory QUIC `/sync` → no payload, classification `IRRELEVANT`
(SPEC §14 A-1/A-2), ledger unchanged).