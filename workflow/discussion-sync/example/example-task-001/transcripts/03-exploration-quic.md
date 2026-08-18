# Transcript 03 — Scenario A3 (SPEC §8 A3): exploratory QUIC

Discussion Session — the user *explores* QUIC without committing. No
confirmation, no benchmark, no decision, no explicit intent-to-log signal.

```
Human:  One more thought while I'm here — should we consider QUIC for example-app's transport later?
Assistant:  QUIC would change protocol negotiation and we have no latency measurements for it.
Human:  Right — unclear, we don't have benchmarks. Decide later.
  /sync
```

The `/sync` gesture runs the extractor against the ledger (which by now
includes `D-001` from `sync/001.yaml`). The QUIC musing is uncommitted
exploration with no explicit intent-to-log signal, so it is classified
`IRRELEVANT` per SPEC §14 A-1 and no payload entry is emitted. Expected
extractor behavior and the protocol citations that force it are documented in
`expected/after-03-exploration.md`.