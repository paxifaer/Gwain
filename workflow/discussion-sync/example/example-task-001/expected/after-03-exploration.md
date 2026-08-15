# Expected outcome — after transcript 03 (`exploration-quic`)

**Scenario:** SPEC §8 **A3**. The Discussion (transcripts/03-exploration-quic.md)
*explores* QUIC ("should we consider QUIC later? unclear, we don't have
benchmarks") with no confirmation and no explicit intent-to-log signal.

## What the extractor does

1. The ledger at this point already contains `D-001` (from `sync/001.yaml`,
   written during transcript 02).
2. Classifies "should we consider QUIC later?" as **IRRELEVANT** — uncommitted
   musing without an explicit intent-to-log signal. Per SPEC §14 A-1, pure
   uncommitted musing is `IRRELEVANT` and produces **no payload entry**. This
   matches Termination **Outcome A′** (PROMPT-disc-extractor.md §6) and the
   protocol.md §Forbidden Categories row:
   > "should we consider QUIC? not sure yet, need benchmarks" *as uncommitted
   > musing* → classify `IRRELEVANT` per SPEC §14 A-1 → emit **no payload
   > entry**.
3. `EXPLORATORY` is not used: it stays reserved for the exceptional case where
   the user explicitly asks for the musing to be logged ("log this as
   exploratory"). No such signal appears in transcript 03.
4. The musing is also not an `open_questions` entry: SPEC §6.2 Forbidden drops
   "Open questions asked purely for exploration", and protocol.md **R-9** keeps
   `open_questions` for genuine blocking questions only.
5. Zero new ledger-emitting entries remain → protocol.md **R-1**
   (= §Idempotency rule 1): no new file written; text-only reply.

## Extractor reply (Termination Outcome A′ — PROMPT-disc §6)

```
No new task-relevant changes since last sync.
```

## Resulting disk state

- No new `sync/NNN.yaml`. `sync/` still contains exactly `001.yaml`
  (this example's only payload ever). No ledger mutation.

## Why not EXPLORATORY (prior reading, superseded by SPEC §14 A-1)

SPEC §8 A3's original table listed "Entry emitted with `class: EXPLORATORY`".
Under that prior reading the extractor would emit `D-002, class: EXPLORATORY`,
content "consider QUIC later" as a carried (not transcribed) payload entry.
SPEC §14 A-1 supersedes that: uncommitted musing without an explicit
intent-to-log signal is `IRRELEVANT`, not `EXPLORATORY`, and MUST NOT appear
in the payload. The surviving reading is the IRRELEVANT one above.

## Verdict

SPEC §8 **A3** verifier consequence: `decisions.md` must NOT contain a QUIC
decision. This fixture writes no payload, so no QUIC entry exists in the sync
directory, and `decisions.md` stays QUIC-free (SPEC §14 A-2).