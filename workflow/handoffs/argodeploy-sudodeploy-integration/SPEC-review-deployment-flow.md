# Read-only review: end-to-end deployment flow

## Scope

Review the complete deployment design in:
`/home/wangdang/work/ai-stack/code/ArgoDeploy-SudoDeploy-integration`

Trace the actual intended sequence from environment loading through local
verification/preparation, deployment file staging, Docker Compose configuration,
container start services, RoboSkill configuration selection, model assets, and
rollback. This is code review only; do not modify anything.

## Review standards

Find concrete defects, not generic advice. For each finding provide severity,
reproduction/trigger, impact, evidence path+line, and smallest safe remediation.

Explicitly assess:

1. Environment variable consistency between `env.sh`, compose, deploy, prepare,
   start services and the expected container users/paths.
2. Whether `SKILL_CONFIG` has a verified runtime consumer and whether the
   `resolve_skill_config` behavior is actually wired into the deployment flow.
3. Correct staging and use of `field-config`, SAM2, exp_data and vendored wheels.
4. Shell robustness under `set -euo pipefail`, globs, quoting, idempotence,
   destructive/overwriting behavior and rollback.
5. Compose/container lifecycle, volume ownership and dependency/network failure
   modes. Do not run lifecycle commands.
6. Whether validation is sufficient to distinguish an integration candidate from
   a robot-compatible deployment.
7. Security or safety issues relevant to privileged, GPU, robot control, and
   external dependency installation.

## Constraints

- Read-only; write-set none.
- Do not run deploy/install/start/patch/Docker lifecycle/network/SSH/robot commands.
- Do not expose credentials.
- Treat the three known field prerequisites as expected gaps, but report if their
  handling is faulty.

## Output

Chinese report only: executive verdict; ordered deployment flow; findings table
(blocking/high/medium/low); what is safe to test now; what must not be done yet;
minimal remediation order; evidence; Files changed none; checks/elapsed/ESCALATE.
