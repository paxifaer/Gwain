# Verifier mandate — ArgoDeploy / ArgoSudoDeploy_Patch analysis

You are an adversarial, read-only verifier. Do not edit files or run deployment,
installation, patching, start, Docker, compose, or network-affecting commands.

Read the original acceptance criteria in `SPEC-argodeploy-sudodeploy-analysis.md`.
Inspect the source directories independently and attempt to disprove these analyst
claims:

1. The root `patch_sudodeploy.sh` is a post-deployment installer that copies
   SudoDeploy, changes compose/start_services, installs Python dependencies,
   writes skills/config, and recreates the deployment container.
2. The patch compose differs from `ArgoDeploy/real/compose.yaml` in a
   meaningful `SKILL_CONFIG`/SudoDeploy integration way.
3. The patch writes/targets a skill layout and run-config path that may not
   match the repository's deployed layout, and real startup uses an overwrite
   run configuration.
4. `skill_SP*.yaml` requires `skill_base_real.yaml`, which is absent from both
   patch and target repository.
5. A safe integration should merge source changes into ArgoDeploy rather than
   execute the patch; SAM2 should not be routinely committed to git.

Return Chinese only:
- per claim PASS / PARTIAL / FAIL, with exact evidence paths and line ranges;
- corrected integration direction if a claim is wrong;
- remaining escalation items;
- `Files changed: none`, checks, elapsed.
