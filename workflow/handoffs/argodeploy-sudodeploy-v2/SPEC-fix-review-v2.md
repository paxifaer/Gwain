# Fix the accepted medium findings in v2

User directed model: Haiku. Only modify:
`/home/wangdang/work/ai-stack/code/ArgoDeploy-SudoDeploy-deployment-v2/**`

Read the original build and verifier specifications. Fix exactly:

1. Make `scripts/check_image_capabilities.py` probe importability of all
   SudoDeploy source modules required by enabled SudoDeploy skills, under the
   same SUDODEPLOY_PYTHONPATH that start services uses. It must fail clearly,
   without network/pip.
2. Make the SudoDeploy-relevant portion of `real/start_services.sh` fail
   predictably on missing/uninstallable required wheels. Do not broadly refactor
   unrelated ArgoDeploy startup behavior. If a wheel is not required for the
   SudoDeploy flow, document its optional nature and avoid a false success claim.
3. Support `_base_` file inheritance for SudoDeploy skill entries in the YAML
   semantic validation, restricted to paths safely contained under field-config
   and with cycle/missing-file detection. Alternatively reject that form with a
   precise documented restriction only if the real SudoDeploy field schema
   cannot use it. Do not fabricate referenced files.
4. Update docs and tests for the exact behavior.

Verification must include static shell/Python checks; temporary valid/invalid
field YAML fixture checks for inline and `_base_` entries; an isolated image
capability import fixture; and no deployment/container/network actions.

Return Chinese only: changes/lines; tests; residual field prerequisites; files
changed; source untouched confirmation; elapsed; ESCALATE.
