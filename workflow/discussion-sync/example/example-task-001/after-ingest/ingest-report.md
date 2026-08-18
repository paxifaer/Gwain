# Ingest report — after PROMPT-orch-ingest runs on `sync/001.yaml`

What the Orchestrator printed (PROMPT-orch-ingest §5 Output Format):

```
## Ingest Report

001.yaml: applied (1 decision added; 0 rejected; 0 conflict)

Summary: 1 pending files processed; 1 applied; 0 conflict; 0 rejected.

## Plan Delta

none
```

Notes (not part of the printed report; for the fixture reader):

- The single `D-001` entry was `CONFIRMED` → disposition `ACCEPT` → appended
  to `decisions.md` § Decisions (protocol §3.5 / R-4). `001.yaml` rewritten
  `status: applied` + `applied_at` + `status_notes` (see
  `sync-001-applied.yaml`).
- No `PROPOSED` / `EXPLORATORY` entries were carried (there are none in 001),
  so `0 carried` and `0 transcribed` for that class.
- `## Plan Delta: none` — no worker had assumed mTLS, so D-001 does not
  invalidate any existing step; the same-file ingest fully absorbed the
  decision (PROMPT-orchestrator §3.8). Next Action was re-planned by the
  Orchestrator as documented in `state.md`.