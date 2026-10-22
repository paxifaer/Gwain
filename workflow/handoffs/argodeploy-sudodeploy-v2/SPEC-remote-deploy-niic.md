# Controlled deployment: ArgoDeploy + SudoDeploy v2 to niic host

User explicitly authorized deployment to `niic@192.168.110.65` from:
`/deploy/ArgoDeploy-SudoDeploy-deployment-v2`

User-directed model: Haiku.

## Objective

Deploy the staged v2 candidate to the target host only if preflight establishes
it is complete and safe. Otherwise stop before state-changing deployment and
report the exact blocker.

## Mandatory sequence

1. SSH preflight non-interactively. Confirm hostname/user/path and target
   directory. Do not expose credentials.
2. Run `bash scripts/verify` in the remote candidate. Continue only on exit 0;
   exit 1 or 2 is a hard stop with evidence.
3. Inspect `real/env.sh`, target deployment path, Docker/Compose availability,
   image availability, required devices/GPU information, and current running
   Argo services. Do not stop/restart anything during preflight.
4. Before any deployment mutation, make a timestamped backup under the remote
   deployment root or `/deploy/backups/` of current compose/env/start config and
   record its exact path. Do not use `rm`, `--force`, reset, or overwrite an
   existing backup.
5. Execute the candidate documented deployment command without `--force`.
   Do not improvise flags. Capture output and stop on first failure.
6. Post-deploy: run the candidate's documented container-side import/capability
   checks and verify RoboSkillServer process/config path/service startup. Do not
   perform robot motion, calibration, trajectory, or hardware actuation.
7. On failure after a deployment mutation, use only the documented rollback
   path and report every action; do not guess destructive recovery steps.

## Safety constraints

- No `rm -rf`, git resets, forced deployment, image pulls, network installs,
  or unprompted package upgrades.
- Never run SudoDeploy skills, robot motions, calibrations, or hardware tests.
- Stop and ESCALATE for missing field inputs, image capability failure, service
  ownership ambiguity, differing active deployment path, unavailable backup
  space, or any unexpected destructive operation.

## Output

Chinese: phase-by-phase PASS/FAIL with real evidence; deployment and backup
paths; services changed; post-checks; rollback if used; files changed; elapsed;
ESCALATE.
