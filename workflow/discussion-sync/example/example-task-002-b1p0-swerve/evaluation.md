<!--
evaluation.md — copied from templates/evaluation.md and filled for example-task-002-b1p0-swerve.
Top checklist stays UNCHECKED until task close; Verdicts are verifier-written;
Implementation Map is develop-worker-written. See templates/evaluation.md.
-->

# Evaluation

- [ ] fixture v_ref=(1,0,0) with δ_curr=0 for all wheels yields v* == v_ref (design doc §4.6 example 2); grep fixtures dir for der004-related fixture run log
- [ ] fixture v_ref=(0,v_y,0) with δ_curr=0, λ=1, N=4 yields v*_y = v_y/5 and v*_x = 0 (design doc §4.6 example 1)
- [ ] numeric check: (Q + λAᵀA) is symmetric positive-definite (all eigenvalues > 0) on a randomized δ_curr fixture (design doc §4.2)
- [ ] fixture p_enc = 5.5π yields δ_cmd = −0.5π via the closest-heading flip (design doc §5.1 + §9)
- [ ] code inspection of base_b1p0.rs::run confirms steering branch reads drive_mat * v_ref, drive branch reads drive_mat * v_cmd, and the A build reads self.current_steering (design doc §6 Steps 5/6/8)

## Verdicts

<!-- Written ONLY by verifier sessions; one target per verdict. -->

- V-001 — target: DER-001 — method: fixture — expected: v=(1,0,0) ⇒ all u_x,i=1 and all u_y,i=0 — actual: 6 wheels × (1,0) matched to 1e-12 tolerance — verdict: PASS — evidence: rb_drivers/fixtures/der001_pure_translation.json (example path) — author: example-verifier-session
- V-002 — target: DER-002 — method: fixture — expected: δ=0 and v=(1,0,0) ⇒ a_iᵀv = 0 for every wheel — actual: max |a_iᵀv| = 0.0 across all 6 wheels — verdict: PASS — evidence: rb_drivers/fixtures/der002_zero_sideslip_forward.json (example path) — author: example-verifier-session
- V-003 — target: DER-003 — method: numeric — expected: rank(A) = 3 for randomized δ ∈ (−π, π]^4 — actual: minimum singular value 0.37 across 128 seeds, never below 0.05 — verdict: PASS — evidence: logs/der003_rank_fixture.log (example path) — author: example-verifier-session
- V-004 — target: DER-004 — method: numeric — expected: eigs(Q + λAᵀA) all > 0 across the same 128 δ fixtures — actual: min eigenvalue 1.0 (Q lower bound), max 14.6, zero failures — verdict: PASS — evidence: logs/der004_spd_eigs.log (example path) — author: example-verifier-session
- V-005 — target: DER-005 — method: fixture — expected: p_enc = 5.5π ⇒ δ_cmd = −0.5π — actual: δ_cmd = −0.5π exactly — verdict: PASS — evidence: rb_drivers/fixtures/der005_unwrap_flip.json (example path) — author: example-verifier-session

## Implementation Map

<!-- file::symbol granularity; line numbers advisory only. -->

- DER-001 ↔ base_b1p0.rs::new (advisory L88-123; drive_mat construction inline at L108-123 emits rows [1,0,-ry] / [0,1,rx] per wheel)
- DER-002 ↔ base_b1p0.rs::run (advisory L540-546; ata build reads self.current_steering and forms a = (-si, ci, ri))
- DER-004 ↔ base_b1p0.rs::run (advisory L548-552; computes q_diag + ata * slip_lambda and LU-solves for v_cmd)
- DER-005 ↔ base_b1p0.rs::run (advisory L554-566; closest-heading flip inline — NOTE: swerve_filter.rs::select_flip at L80 exists but is a legacy sector-QP helper with hysteresis and is NOT called from run; see deviation note in worker report)
- C-001 ↔ base_b1p0.rs::run (advisory L554-566; vs_ref = drive_mat * v_ref drives steering targets)
- C-002 ↔ base_b1p0.rs::run (advisory L569-575; vs_cmd = drive_mat * v_cmd drives driving_w projection)
- C-003 ↔ base_b1p0.rs::run (advisory L540-546; A build reads self.current_steering[i] only)

## Open Verifications

- V-006 → DER-004 — re-run the SPD / eigenvalue fixture after the next slip_lambda retune, to reconfirm the closed-form solve stays well-conditioned at the new λ
