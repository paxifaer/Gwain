# Transcript 02 — Scenario A2 (SPEC §8 A2): confirmed decision

Discussion Session for `example-task-001`. The human makes ONE confirmed
decision: use TLS (not mTLS) for example-app transport, with a reason.

```
Human:  Let's settle the transport question for example-app before we spin any worker.
Human:  I've watched mTLS teams drown in cert ops — every client needs a CA, and rotation gets heavy.
Assistant:  Agreed — TLS with short-lived certificates covers our intra-cluster threat model and keeps rotation simple.
Human:  We pick TLS over mTLS, because the cert lifecycle is simpler. Confirmed.
  /sync
```

The `/sync` gesture runs the extractor. Expected: a single
`changes.decisions` entry, new `D-001`, `class: CONFIRMED`,
`revises: null`, `status: pending`, written to
`sync/001.yaml`. See `expected/after-02-decision/`.