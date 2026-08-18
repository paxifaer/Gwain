# Extractor reply — after transcript 02 (`decision-tls`)

**Scenario:** SPEC §8 **A2**.

**Payload written:** `expected/after-02-decision/extractor-output.yaml`
(byte-identical to `sync/001.yaml` — the one and only sync payload this
example produces on disk).

**What the extractor did**
- The human explicitly confirmed: *"We pick TLS over mTLS, because the cert
  lifecycle is simpler. Confirmed."* → classified `CONFIRMED`
  (PROMPT-disc-extractor.md §3 R-A).
- Subject `transport.security` (protocol.md §Conflict Detection). No other
  entry exists on that subject, so `revises: null` and no conflict.
- Fresh ID `D-001` (protocol.md §ID Conventions — ledger was empty).
- Written to `sync/001.yaml` with `status: pending`
  (protocol.md §Sync Payload Schema).

**Reply to the human** (PROMPT-disc §6, Termination Outcome B):

```
Sync payload /home/abc/work/ai-stack/workflow/Gawain/workflow/discussion-sync/example/example-task-001/sync/001.yaml created. Changes: 1 decision.
```

This is the only extractor reply that wrote a file in the whole example
(scenarios A2 only).