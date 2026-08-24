# Gawain Verifier / Test / Trace Audit

Date: 2026-08-24

Status: accepted direction; first P0 remediation batch in progress on
`feat/verification-evidence-p0`

## Executive decision

Gawain should stop competing with Claude Code, Codex, DeepSeek Harness, and CI
as a task dispatcher. Its durable boundary should be a harness-neutral
**Verification and Evidence Protocol**:

```text
Requirement -> Claim -> TestCase -> Run -> Attempt
                             \-> Span/Event -> Artifact -> Verdict
```

The native harness owns session spawning, model routing, polling, code editing,
and tool execution. Gawain owns candidate identity, evidence provenance,
test/trace contracts, deterministic policy gates, typed verdicts, waivers, and
replay.

This audit treats Markdown claims as intent, not proof. A behavior is considered
implemented only when repository code or captured runtime evidence enforces it.

## Evidence scope

- Gawain tracked repository content: 39 Markdown files and 5 YAML files at the
  time of audit. There was no SDK, validator, collector, test runner, trace
  runtime, or CI gate.
- Runtime handoffs: 11 task directories, 101 files, approximately 1.3 MiB;
  they were all untracked and therefore did not form durable repository
  evidence.
- Claude Code sample: 20 top-level sessions whose titles start with
  `code_integration_for_argogateway`, `argo_service_manager`, or
  `argo_dev_tools`; approximately 141.8 MiB and 56,292 JSONL records, with 130
  compactions before fork de-duplication.
- Execution overlap: 233 shell records containing `claude -p` and 230 native
  Agent/Task calls. Fourteen of twenty sessions had a `forkedFrom` lineage.
- Only four sessions showed a Gawain SessionStart hook, and all four only
  reported that there was no pending sync. No real handoff contained a
  `sync/*.yaml` payload.
- `argo_dev_tools_*` ran from 2026-07-02 through 2026-07-15, before Gawain's
  initial 2026-08-07 commit. Those sessions are a pre-Gawain harness baseline,
  not Gawain adoption evidence.

Historical session evidence is stored outside this repository under the Claude
project directory. The references below use the JSONL filename and record line;
they intentionally do not reproduce credentials or other secret values.

## What already works

The adversarial-verifier idea has produced real value:

- `01ad9e56-f2df-4ba7-a2cf-9f091009b8db.jsonl:72` records an independent
  verifier finding that a failed `/bin/sleep` fixture left a zombie which
  `pgrep -x` misclassified as Running.
- The same session records a verifier catching a worker write outside its
  declared write-set.
- `f15f6c84-aa00-4ed8-a59f-61c55b89626f.jsonl:297` records an outcome audit
  finding that only 3 of 20 real robot targets were end-to-end supported; 14
  were unsupported and 3 partial.
- `93403836-619a-4f3e-8819-1bdd34826787.jsonl:2426` records an adversarial
  review finding that client credentials could be offered to an arbitrary
  server on the configured TLS port.
- Durable handoff files improved recovery after compaction compared with the
  older `argo_dev_tools_*` sessions.

The differentiator is therefore not "more agents." It is the ability to model
real intent, try to disprove a claim, and retain reproducible evidence.

## P0-1: PASS is not bound to an immutable candidate or hard policy

### Intended behavior

The workflow says a verifier disproves worker claims and returns evidence, and
the observability contract says a missing required check fails the run.

### Implemented reality

- Worker, verifier, and orchestrator share the same mutable working tree and
  evidence files.
- `HEAD unchanged` is routinely used as a safety claim even when the candidate
  is a dirty worktree.
- `19e472ca-a88b-4261-9408-2835221b99e6.jsonl:136` reports local code as ready
  to test; line 156 then discovers that the code was never synchronized to the
  target Windows host.
- `b8b607fc-712c-4903-80b9-3bf66a1b4645.jsonl:235` accepts all claims while
  only three of eight mandatory trace checks are PASS and five are downgraded
  to NUANCE.
- In the `sweb_boot40` dogfood, all 40 tasks were internally ACCEPTed while the
  blind official judge resolved 28/40. Two verifier runs also accessed
  forbidden post-base history before their verdicts were discarded.

### Required remediation

1. Define `candidate_id` from repository, base commit, tree hash, and dirty-diff
   hash.
2. Hash every referenced evidence artifact and reject path traversal or missing
   artifacts.
3. Make required checks a closed, typed set. `NUANCE` is not a valid status.
4. Permit overall PASS only when every required check is PASS and every claim
   is PROVEN.
5. Keep human waiver separate from PASS and require author, scope, reason,
   policy version, and expiry.

## P0-2: test output can be green without executing the required experiment

### Implemented reality

- `93403836-619a-4f3e-8819-1bdd34826787.jsonl:2596` records an invalid spec
  command, a filter executing only 3 of 5 intended tests, and tests depending
  on another test's process-global CryptoProvider side effect.
- The same session at line 3345 confirms two purported long-running E2E files
  defaulted to `0 passed / 0 failed / 6 ignored`.
- Browser checks were repeatedly used where the required path was Tauri
  desktop -> Gateway -> Backend -> real device.
- Static verification was ACCEPTed while dynamic E2E was blocked or deferred.
- Failure-only behavior was accepted without a force-trigger path. A later E2E
  report captured zero FAIL events because the failure branch was unreachable.

### Required remediation

1. Require a machine-readable test record with exact required and observed
   layer, command, environment, expected count, executed count, ignored count,
   exit code, oracle, and raw evidence.
2. Reject PASS for zero tests, count shortfall, ignored required tests, nonzero
   exit, failed tests, or required/observed layer mismatch.
3. Represent negative tests as `expected_outcome=REJECT` plus
   `status=EXPECTED_REJECT`, rather than overloading PASS.
4. A dynamic acceptance must reference dynamic evidence. Static inspection
   cannot substitute for browser, desktop, deployment, or real-device E2E.

## P0-3: trace is a prose convention, not a causal or safe evidence format

### Contract inconsistencies

- `correlation_id` versus `corr`.
- `operation` versus `op`.
- `caller->callee` versus separate `caller` and `callee` fields.
- JSON logging is allowed while verification requires `grep field=`.
- A Python example logs `str(e)` while the verifier bans loss of the cause
  chain.
- There is no `span_id`, `parent_span_id`, terminal event, schema version, or
  reliable nested-retry/fan-out model.

### Runtime evidence

- Application events were sometimes written only to a browser console and not
  the persistent evidence sink.
- `19e472ca-a88b-4261-9408-2835221b99e6.jsonl:223` records concurrent appends
  interleaving trace characters.
- Historical JSONL records contain literal credential-bearing tool inputs, and
  compaction summaries can copy them. Values are intentionally omitted here.

### Required remediation

1. Define a versioned JSON trace-event schema using W3C-compatible 128-bit
   `trace_id`, 64-bit `span_id`, and `parent_span_id`.
2. Bind every event to run, candidate, test case, operation, service instance,
   attempt, and sequence.
3. Require exactly one root span and one start/end pair per span; parent spans
   must exist.
4. Require event-specific fields for STATE, FAIL, ERROR, and SPAN_END.
5. Block sensitive keys and private-key material before trace evidence is
   accepted.

## Recorded P0 issues deferred from the first implementation batch

These remain P0 defects, but they are not selected for the first executable
verification-core slice because the sync protocol has zero observed adoption:

- Discussion ingest adds pending IDs to its ledger and then treats those same
  IDs as duplicates (`workflow/discussion-sync/prompts/PROMPT-orch-ingest.md`,
  steps 1 and 3.1).
- High-risk A-/DER- reasoning objects lose fields because extractor, sync
  schema, and ingest templates do not share a data model.
- Invalidation says a valid node requires all dependencies to be valid, while
  also stopping propagation at `needs_review`.
- Bootstrap and worker preamble contain stale paths, hook claims, and classifier
  counts.

These should be disabled or fixed before discussion-sync is advertised as an
active safety control.

## First-batch acceptance criteria

The first P0 implementation is accepted only when:

1. A deterministic validator rejects candidate hash mismatch, evidence hash
   mismatch, unsafe paths, missing required checks, non-PROVEN claims, and an
   invalid waiver.
2. It rejects false-green test records: zero executed, count shortfall, ignored
   required tests, failed/nonzero-exit runs, layer substitution, and missing
   dynamic evidence.
3. It validates versioned JSONL traces and rejects missing parents, missing
   terminal events, cross-run/candidate/test contamination, duplicate event
   identity, and sensitive values.
4. All rejection behaviors have tests that were observed failing before the
   implementation was added.

## Measures for later ablation

- false-accept and false-reject rate against a blind external oracle;
- INCONCLUSIVE rate;
- candidate/test/deploy identity coverage;
- raw-evidence and environment-fingerprint completeness;
- zero/ignored-test rejection rate;
- dynamic and force-trigger evidence coverage;
- trace reconstruction and replay success;
- post-PASS same-path P0/P1 rework rate;
- secret-contamination rate;
- time and cost per PROVEN claim.

The existing SWE-bench 300 report compares two execution environments using
the same Gawain workflow. It is useful environment evidence but is not an
ablation proving Gawain's incremental value.
