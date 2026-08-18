<!--
task.md — copied from templates/task.md and filled for example-task-001.
Static-ish: ingest mutates ONLY by appending CONFIRMED `requirements` to the
§ Requirements list (R-XXX). See templates/task.md.
-->

task_id: example-task-001

# example-app transport choice

## Goal

Decide whether `example-app`'s service-to-service transport should use TLS (with cert rotation), and document the decision, so the Orchestrator session can implement the choice without re-deriving the transport discussion.

## Scope

Covers: the transport security choice (TLS vs mTLS) for `example-app`, and the record of that decision in `decisions.md`.
Does NOT cover: transport protocol selection (TCP / QUIC / HTTP), any implementation code, deployment config, or other components' security posture.

## Requirements

- R-001 — example-app transport MUST use TLS (no plaintext) for service-to-service traffic — baseline security prerequisite discussed with user
- R-002 — the confirmed transport choice (and its reason) MUST be recorded as a D-XXX entry in decisions.md — the output of this task is a documented decision
- R-003 — the decision MUST be confirmed by the user in the Discussion before the entry may be transcribed — only CONFIRMED entries land in the ledger

## Acceptance Criteria

- [ ] decisions.md § Decisions contains exactly one D-001 entry stating "use TLS (not mTLS) for example-app transport" with a reason, and no competing decision on the same subject
- [ ] sync/001.yaml parses as YAML, conforms to templates/sync-NNN.yaml, is `status: pending`, and byte-matches the extractor output in expected/after-02-decision/extractor-output.yaml
- [ ] After ingest, sync/001.yaml is rewritten `status: applied` and decisions.md / state.md are updated accordingly (D-001 present; Status no longer `idle`)