# ArgoDeploy + SudoDeploy deployment candidate v2

model_selection:
  model: haiku
  mode: user_directed
  reason: user explicitly requested Haiku for future Claude Code workers

risk: normal — deployment source assembly; no control, kinematics, dynamics,
scheduling, or concurrency algorithm changes.

## Product target

Create a standalone, maintainable deployment candidate at:
`/home/wangdang/work/ai-stack/code/ArgoDeploy-SudoDeploy-deployment-v2`

It must turn the useful SudoDeploy patch behavior into a repeatable,
ArgoDeploy-compatible source deployment, not a runtime patch. It must preserve
original source directories unchanged and make the actual RoboSkill load path
explicit and verifiable.

## Source inputs (read-only)

- `/home/wangdang/work/ai-stack/code/ArgoDeploy`
- `/home/wangdang/下载/ArgoSudoDeploy_Patch`
- Existing v1 candidate is reference-only. Do not copy its integration scripts
  blindly; specifically avoid its dead `SKILL_CONFIG` composition design.

## Write boundary

Only write under `/home/wangdang/work/ai-stack/code/ArgoDeploy-SudoDeploy-deployment-v2/**`.
Do not modify sources, run a deployment, start services, Docker lifecycle,
network, SSH, or robot commands.

## Required design

1. Build a standalone derived ArgoDeploy source tree (no symlinks, no `.git`,
   caches, venvs, build artifacts, checkpoints, or patch/mount/install helper
   scripts from the patch). Include needed SudoDeploy source under
   `packages/SudoDeploy/`.
2. Integrate source-level SudoDeploy volume mounting and deployment staging in
   `real/` scripts. Use deliberate user/path variables consistently; don't
   overwrite source `env.sh` at runtime.
3. **Do not add `SKILL_CONFIG` unless there is a demonstrated runtime consumer.**
   The authoritative load mechanism must be the exact run-config passed by
   `start_services.sh` to `roboskill_server_v2`.
4. Define field-provided inputs under `field-config/`:
   - `skill_base_real.yaml`
   - `run_config_real_for_demo_roboskill_overwrite.yaml`
   The preparation flow must copy the latter to the exact config path used by
   startup and validate both YAML syntax and that the overwrite config includes
   all three SudoDeploy module references plus the needed `robo.skills` entries.
   Never fabricate either file.
5. Define external assets under `field-assets/`: SAM2 checkpoint, optical-flow
   checkpoints, and `exp_data`. Do not include weights. Preparation/verification
   must state exactly which assets are mandatory for which enabled skills;
   deployment must fail before Compose when a selected skill needs an absent
   asset.
6. Dependencies: identify SudoDeploy Python modules that must be visible in the
   actual container and either stage/install them deliberately or provide an
   explicit image-capability check. Never use `pip ... || true` for a required
   dependency. Do not assume internet during robot deployment.
7. Create `verify` (no writes) and `prepare --check` scripts. They must
   distinguish structural defects (exit 1) from missing field prerequisites
   (exit 2), do YAML semantics—not only substring grep—and do not access a
   container/robot. `prepare` without `--check` may stage deployment files but
   must refuse destructive overwrite without an explicit `--force` argument.
8. Create Chinese README: flow diagram, directory contract, exact local checks,
   field inputs, deployment boundary, post-deploy container checks to run later,
   and rollback.

## Acceptance checks

- All shell scripts pass `bash -n`.
- The local validator passes structural checks on a clean candidate and returns
  exit 2 for currently absent field inputs, naming each one.
- A temporary supplied minimal valid field config can prove that YAML semantic
  checks accept the required modules/skills; a config missing a module or skill
  must fail.
- Tests demonstrate no package/checkpoint/cache/git metadata is shipped.
- No claim of tested robot compatibility before container and robot verification.

## Worker output contract

Chinese only: design summary; files/line ranges; exact checks and outputs;
known field prerequisites; any source ambiguity; Files changed; confirmation
source directories untouched; elapsed; ESCALATE.
