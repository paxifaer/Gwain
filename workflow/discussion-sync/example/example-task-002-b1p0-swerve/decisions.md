<!--
decisions.md — copied from templates/decisions.md and filled for example-task-002-b1p0-swerve.
Steady-state snapshot: every entry is at status `valid`; no revision chains, no
needs_review / invalid entries. See templates/decisions.md for the entry-format
contract (per-section templates above each section).
Five sections per §9: Decisions / Constraints / Rejected / Assumptions / Derivations.
-->

# Decisions

<!-- user-authored, born valid; basis lists the derivations/assumptions that justify the choice -->

- D-001 — adopt the soft slip-penalty twist filter (not a hard-constraint QP) — user-confirmed per design doc §3.4 insight (fighting is drive-vs-current-angle incompatibility, not steering-rate) — basis: [DER-003] — status: valid

# Constraints

<!-- invariant implementation rules; each carries a verify: code-inspection target -->

- C-001 — steering targets are computed from the REFERENCE twist v_ref, never from the filtered twist v* — decoupling requires steering to chase the user's intent, not the safety-filtered value — verify: code inspection base_b1p0.rs::run (steering branch reads drive_mat * v_ref) — status: valid
- C-002 — drive commands are computed from the FILTERED twist v* — guarantees emitted wheel speeds respect the slip penalty — verify: code inspection base_b1p0.rs::run (drive branch reads drive_mat * v_cmd) — status: valid
- C-003 — the slip-penalty matrix A is built from the CURRENT steering angles δ_curr, not the steering targets — a stale or target-driven A would penalize the wrong geometry — verify: code inspection base_b1p0.rs::run (ata build reads self.current_steering) — status: valid
- C-004 — the closest-heading flip must not alter the slip-penalty input — flip is steering-side bookkeeping; A depends only on δ_curr — verify: code inspection base_b1p0.rs::run (flip branch never mutates self.current_steering or v_ref) — status: valid

# Rejected

- (none yet)

# Assumptions

<!-- one-sentence premises; born valid because source: spec -->

- A-001 — N swerve modules, currently N = 4, with module positions (r_x,i, r_y,i) fixed by chassis geometry — source: spec — status: valid
- A-002 — steering motors run Profile Position mode (slow) while drive motors run Velocity mode (fast), under a dual-rate 20 Hz policy / 120 Hz control architecture — source: spec — status: valid
- A-003 — wheel angle δ = −p_enc / k_shaft with k_shaft = 1.0, and steering has no [-π, π] hard limit — source: spec — status: valid
- A-004 — slip-penalty weight λ is a fixed tunable constant per build — source: spec — status: valid

# Derivations

<!-- single-conclusion entries with from/by/verify; all promoted to valid via Verdict PASS in evaluation.md ## Verdicts -->

- DER-001 — contact-point velocity u = M·v with M the 2N×3 block [[1,0,-r_y,i],[0,1,r_x,i]] — from: [A-001] — by: rigid-body kinematics — verify: fixture v=(1,0,0) ⇒ all u_x,i=1, u_y,i=0 — status: valid
- DER-002 — no-sideslip row a_i = (−sinδ_i, cosδ_i, r_y,i·sinδ_i + r_x,i·cosδ_i)ᵀ, so slip s_i = a_iᵀv — from: [A-001, A-002] — by: projecting body velocity at wheel i onto its lateral axis — verify: fixture at δ=0, v=(1,0,0) ⇒ a_iᵀv = 0 for all wheels — status: valid
- DER-003 — with N=4 the system A v = 0 is generically over-constrained (rank 3), so only the trivial solution exists during steering transients — from: [DER-002, A-001] — by: rank counting of N=4 equations in 3 unknowns — verify: numeric — random δ fixture ⇒ A has full column rank — status: valid
- DER-004 — slip-penalty filter optimum v* = (Q + λAᵀA)⁻¹ Q v_ref in closed form — from: [DER-002, DER-003] — by: normal equations of the penalized least-squares objective — verify: numeric — (Q + λAᵀA) SPD on fixtures, all eigenvalues > 0 — status: valid
- DER-005 — closest-heading flip maps target θ* to δ_cmd inside [δ_meas−π, δ_meas+π] using the unwrapped encoder reading — from: [A-003, DER-001] — by: modulo equivalence class choice under no-hard-limit steering — verify: fixture p_enc = 5.5π ⇒ δ_cmd = −0.5π — status: valid
