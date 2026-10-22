# Fix verifier findings in the standalone candidate

Only modify `/home/wangdang/work/ai-stack/code/ArgoDeploy-SudoDeploy-integration/**`.
Never modify the two original source directories.

Read the original build spec and fix these accepted verifier findings:

1. Remove `packages/RoboSkillServer/compiled_cache.db` and prevent it from
   being considered a supported candidate asset (ignore/document it as a build
   cache). Also remove copied `packages/RoboSkillServer/tmp/**` image/test
   residue if it is not needed for deployment.
2. Make `real/deploy.sh` robust when top-level `packages/rustbot-*.whl` or
   `packages/rbmw-*.whl` are absent under `set -euo pipefail`. Preserve normal
   behavior when present. The candidate must still use the vendored SudoDeploy
   wheels when available; failure must be explicit only if a required wheel is
   actually unavailable for the requested flow.
3. Make `scripts/verify_integration.sh` and/or `scripts/prepare_deploy.sh`
   truly validate that the field-provided overwrite YAML contains all required
   SudoDeploy `_include_module_` entries. Do not fabricate the YAML.
4. Resolve the documented-vs-actual `exp_data` validation discrepancy: either
   add a non-destructive explicit verification check, or correct documentation
   precisely. Prefer an explicit check only if it does not turn the existing
   expected three field prerequisites into an unclear result.
5. Remove duplicate/inaccurate README layout entries found by the verifier.

Required verification: shell syntax, static verification script, and a focused
test showing deploy.sh progresses past optional missing top-level wheel globs
without invoking deployment or Docker lifecycle commands. Do not run deploy,
install, start, patch, Docker lifecycle, network, SSH, or robot commands.

Return Chinese only: changes with line references; checks/output; residual
expected prerequisite failures; files changed; confirmation source dirs untouched;
elapsed and ESCALATEs.
