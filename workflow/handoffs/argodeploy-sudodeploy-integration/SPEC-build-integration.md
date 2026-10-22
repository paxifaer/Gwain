# Build a standalone ArgoDeploy + SudoDeploy integration candidate

model_selection:
  model: t9s/kimi-k3
  mode: automatic
  reason: deployment_integration_and_validation

risk: normal — deployment asset assembly only; no core control, kinematics, dynamics, scheduling, or concurrency algorithms are modified.

## Objective

Create a new, standalone candidate directory at:
`/home/wangdang/work/ai-stack/code/ArgoDeploy-SudoDeploy-integration`

It must be an additive, source-controlled-style integration candidate derived
from `ArgoDeploy`, incorporating the compatible, safe parts of
`ArgoSudoDeploy_Patch`. It must not modify either source directory.

## Acceptance criteria

1. The candidate contains a complete ArgoDeploy deployment source tree necessary
   for the `real/` deployment flow, plus SudoDeploy deployment assets in a clear
   location.
2. It integrates SudoDeploy at source level: compose volume and `SKILL_CONFIG`,
   `start_services.sh` PYTHONPATH/dependencies, and a reproducible deployment
   preparation path. Do not include or execute the patch script as the mechanism.
3. It never silently fabricates unavailable field configuration. Missing
   `skill_base_real.yaml` and the overwrite run configuration must have explicit
   validation failures/documentation and a documented provisioning location.
4. Do not copy `sam2.1_hiera_large.pt` (or other model checkpoints) into the
   candidate. Provide an explicit external-asset location and validation message.
5. Include a local, non-destructive verification command/script that validates
   shell syntax, compose rendering if Docker Compose is available, configuration
   prerequisites, and source-tree consistency without connecting to a robot or
   starting containers.
6. Add concise Chinese README documenting layout, integration deltas, setup
   prerequisites, local verification, deployment boundary, and rollback.

## Constraints

- Write-set: only `/home/wangdang/work/ai-stack/code/ArgoDeploy-SudoDeploy-integration/**`.
- Source read-only: never modify `/home/wangdang/work/ai-stack/code/ArgoDeploy/**`
  or `/home/wangdang/下载/ArgoSudoDeploy_Patch/**`.
- Do not run deploy/install/start/patch scripts, Docker compose up/down/build,
  network commands, SSH, or commands affecting a robot/service/container.
- Do not copy `.git` directories, large model checkpoints (`*.pt`, `*.ckpt`),
  Python virtual environments, caches, or build artifacts.
- Preserve existing source semantics unless a change is required by this spec.
- No commits, resets, clean, checkout, or other destructive Git actions.

## Inputs

- `/home/wangdang/work/ai-stack/code/ArgoDeploy`
- `/home/wangdang/下载/ArgoSudoDeploy_Patch`
- prior analysis spec: `../argodeploy-sudodeploy-analysis/SPEC-argodeploy-sudodeploy-analysis.md`
- verification findings: `../argodeploy-sudodeploy-analysis/PROMPT-verify.md`

## Required design decisions

- Use the candidate directory as a standalone derived tree. Copy the required
  ArgoDeploy source assets excluding forbidden artifacts; do not use symlinks to
  hide integration deltas.
- Place SudoDeploy under `packages/SudoDeploy/` and make real deployment assets
  refer to `NewDeploy/SudoDeploy`.
- Treat `skill_base_real.yaml` and
  `run_config_real_for_demo_roboskill_overwrite.yaml` as user/field-provided
  inputs under `field-config/` (not fabricated defaults). The verifier must
  report them missing until supplied.
- Treat the SAM2 checkpoint as a field-provided external input under
  `field-assets/sam2.1_hiera_large.pt`; do not create/copy it.

## Output contract

Return Chinese only:
1. Summary of the created layout and integration changes.
2. Files created/modified with line references.
3. Exact local verification commands and PASS/FAIL output excerpts.
4. Explicit remaining field prerequisites / ESCALATEs.
5. Confirmation that source directories were untouched and no deployment action
   was run; elapsed time.
