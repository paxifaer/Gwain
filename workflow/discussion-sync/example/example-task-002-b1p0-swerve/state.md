<!--
state.md — copied from templates/state.md and filled for example-task-002-b1p0-swerve.
Cap: ≤ 60 lines. Reasoning State below is the orchestrator-written projection —
frontier-only; interior nodes lazy-load from decisions.md.
-->

# State

## Status

in_progress

## Reasoning State

<!-- Derived projection. Written ONLY by the orchestrator (mechanical rewrite after each ingest / invalidation run). Read-only for workers. Frontier-only: list only leaf derivations (those with no valid dependents); interior nodes lazy-load from decisions.md. Whole file must stay ≤ 60 lines. -->
- Goal: see task.md
- Valid Assumptions:
  - A-001 — N=3 modules, positions (r_x,i, r_y,i) fixed by chassis geometry — spec
  - A-002 — steering Profile-Position, drive Velocity, 20 Hz policy / 120 Hz control — spec
  - A-003 — δ = −p_enc / k_shaft, k_shaft = 1.0, no [-π,π] hard limit — spec
  - A-004 — λ is a fixed tunable per-build constant — spec
- Valid Derivations (frontier):
  - DER-004 — closed-form slip-penalty optimum v* = (Q + λAᵀA)⁻¹ Q v_ref
  - DER-005 — closest-heading flip picks δ_cmd in [δ_meas−π, δ_meas+π] under unwrapped encoder
- Needs Review: (none)
- Invalid: (none)
- Open Verifications: (V-006 → DER-004)
- Proposed Pending: (none)

## Completed

- P-001 — reasoning ledger populated: A-001..A-004 assumptions, DER-001..DER-005 derivations, C-001..C-004 constraints, D-001 decision, all derivations promoted to valid via Verdict PASS V-001..V-005 — evidence: decisions.md, evaluation.md ## Verdicts

## In Progress

- (none)

## Blocked

<!-- Populated by orchestrator: file::symbol symbols mapped (via evaluation.md ## Implementation Map) to invalid/needs_review ledger targets. Workers MUST NOT modify listed symbols; ESCALATE if the task requires touching them. -->
- (none)

## Next Action

Dispatch develop worker for drive-projection implementation per DER-004 / DER-005 (heading projection formula and closest-heading flip inline in BaseB1p0::run).

## Open Questions

- (none)
