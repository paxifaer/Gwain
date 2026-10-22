# Authorized forced deployment after remote weight discovery

User explicitly authorized forced deployment to `niic@192.168.110.65` and
provided the remote sudo credential in the current task context. Do not echo or
record the credential.

User-directed model: Haiku.

## Remote sources
- Candidate: `/deploy/ArgoDeploy-SudoDeploy-deployment-v2`
- SAM2: `/deploy/ArgoSudoDeploy_Patch/sam2.1_hiera_large.pt`
- NeuFlow: `/deploy/ArgoSudoDeploy_Patch/SudoDeploy/tools/neuflow_v2/checkpoints/neuflow_mixed.pth`
- Existing deployment: `/home/niic/deploy/beta1.1-release`

## Mandatory sequence
1. Reconfirm source size/hash and candidate path. Copy SAM2 into candidate
   field-assets as `sam2_ckpt.pt` and NeuFlow as `neuflow_mixed.pth`. Do not
   overwrite a different existing destination silently: compare hashes first;
   if differing, ESCALATE.
2. Run candidate `bash scripts/verify`; continue only on exit 0.
3. Inspect the actual deployment command/script and establish the exact
   environment needed so `sudo` does not accidentally redirect DEPLOYPATH to
   `/root`. Use the existing `/home/niic/deploy/beta1.1-release` target only.
4. Create a timestamped, non-overwriting backup of existing deployment compose,
   env, start-services and config files under `/home/niic/deploy/backups/`.
   Record exact path. Do not back up/copy unbounded datasets.
5. Execute the candidate documented forced deployment using sudo, with only the
   explicit deployment environment required by step 3. Do not use any other
   destructive command than the candidate's documented force behavior.
6. Post-deploy checks: candidate/target tree exists; compose service/container
   state; container-side capability/import check; confirm RoboSkillServer is
   started with the intended overwrite config. Do not execute skills, motion,
   calibration, or hardware actions.
7. If a post-mutation failure occurs, use only documented rollback/backups; if
   the proper rollback is unclear, stop and ESCALATE rather than improvising.

## Output
Chinese phase report with real evidence, backup/deploy path, copied hashes,
services changed, post-checks, rollback if any, Files changed, elapsed and
ESCALATE.
