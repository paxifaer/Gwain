# Stage deployment candidate v2 to removable deployment disk

User directed model: Haiku.

## Objective

Copy (do not move) the complete candidate:
`/home/wangdang/work/ai-stack/code/ArgoDeploy-SudoDeploy-deployment-v2`
to this new external-disk directory:
`/media/wangdang/My Passport/ArgoDeploy-SudoDeploy-deployment-v2`

It will be used as a removable-disk deployment source on the robot deployment
machine. The workspace original must remain intact.

## Safety / write boundary

- Only write below the exact external target directory above.
- First verify the target does not exist. If it exists, stop and ESCALATE; do
  not merge, overwrite, delete, or rename it.
- Verify available disk space before copying. Stop and ESCALATE if insufficient.
- Do not modify the workspace candidate, old deployment directory, source repos,
  services, Docker, network, SSH, or robot.
- Preserve permissions, symlinks (though none expected), timestamps and all
  included artifacts. Do not copy prohibited artifacts from elsewhere.

## Required validation

1. Compare file count and total size (within filesystem allocation differences).
2. SHA-256 verify: `PROVENANCE.md`, both field-config YAMLs, robot-stack tar,
   and a deterministic sample of exp_data/model files against the workspace
   source. Do not print secrets.
3. On the external copy only, run `bash scripts/verify`; expected result is exit
   code 2 with zero structural failures and only the known missing SudoDeploy
   weight prerequisites.
4. Report external target path, free-space evidence, checks, and confirmation
   workspace source remained unchanged.

## Output

Chinese only: result; files changed (external target creation/copy); size/count;
checks and output; any discrepancy/ESCALATE; elapsed.
