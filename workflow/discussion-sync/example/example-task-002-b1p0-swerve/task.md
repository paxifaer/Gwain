<!--
task.md — copied from templates/task.md and filled for example-task-002-b1p0-swerve.
Static-ish: ingest mutates ONLY by appending CONFIRMED `requirements` to the
§ Requirements list (R-XXX). See templates/task.md.
`risk: high` triggers the §9 High-Risk Reasoning Ledger for this task.
-->

task_id: example-task-002-b1p0-swerve
risk: high — triggers: H1, H2

# B1P0 swerve slip-filter + closest-heading flip + heading-projection drive

## Goal

Implement, inside the B1P0 base's 20 Hz policy tick, the slip-penalty twist filter, the closest-heading steering flip, and the heading-projection drive, per rb_drivers/doc/swerve_kinematic_filter_design.md, so the controller emits only the component of the commanded twist the current wheel angles can execute without sideslip while steering tracks the IK target unimpeded.

## Scope

Covers: the 20 Hz policy-tick math in rb_drivers/src/base_b1p0.rs (drive_mat construction, slip-penalty 3x3 LU solve, IK + closest-heading flip, heading-projection drive) and any helpers it legitimately needs from rb_drivers/src/swerve_filter.rs.
Does NOT cover: slew-rate limiting, zero-twist guard, waypoint interpolation, the 120 Hz control tick, odometry / SE(2) integration, CAN drivers (RobStride, EYou), or the sim-side Python port.

## Requirements

- R-001 — the policy tick MUST compute the filtered twist v* = (Q + λAᵀA)⁻¹ Q v_ref using A built from the CURRENT steering angles δ_curr — design doc §4.1/§4.2: fighting is caused by drive-vs-current-angle incompatibility, not by steering change magnitude
- R-002 — steering targets MUST be computed from v_ref (NOT from v*), with the closest-heading flip picking θ or wrap(θ+π) according to |wrap(θ − δ_curr)| > π/2 — design doc §5.1/§6 Step 6: decoupling requires steering to chase the user's reference, drive to stay safe
- R-003 — drive wheel speeds MUST be the projection of M·v* onto the CURRENT heading (cosδ_curr, sinδ_curr), divided by wheel radius — design doc §5.2/§6 Step 8: the sign then emerges from the dot product, no explicit flip-aware sign term

## Acceptance Criteria

- [ ] fixture v_ref=(1,0,0) with δ_curr=0 for all wheels yields v* == v_ref (design doc §4.6 example 2)
- [ ] fixture v_ref=(0,v_y,0) with δ_curr=0, λ=1, N=4 yields v*_y = v_y/5 and v*_x = 0 (design doc §4.6 example 1)
- [ ] numeric check: (Q + λAᵀA) is symmetric positive-definite (all eigenvalues > 0) on a randomized δ_curr fixture (design doc §4.2 positive-definiteness paragraph)
- [ ] fixture p_enc = 5.5π yields δ_cmd = −0.5π via the closest-heading flip (design doc §5.1 modulo choice under §9 wrap rule)
- [ ] code inspection: the steering branch reads `drive_mat * v_ref`, the drive branch reads `drive_mat * v_cmd`, and the A-matrix build reads `self.current_steering` (design doc §6 Steps 5/6/8 decoupling)
