# Import safe old-real-deployment baseline into v2

User directed model: Haiku. Only modify:
`/home/wangdang/work/ai-stack/code/ArgoDeploy-SudoDeploy-deployment-v2/**`

Read the old-deploy audit before working. Treat the old external deployment as
read-only. Do not deploy, run Docker lifecycle, network, SSH, robot actions, or
modify either source tree.

## Goal

Use the confirmed compatible portions of the old proven-real-robot package to
make v2's field inputs materially ready, without importing stale service
packages or pretending SudoDeploy was present in the old package.

## Required work

1. Extract/copy old `models/` and `checkpoints/` into v2
   `field-assets/exp_data/{models,checkpoints}/`, retaining and verifying their
   checksum sidecars/manifests where available. Do not copy image archives or
   old gateway/backend debs.
2. Extract `robot-stack.tar.gz` into v2 `packages/robot-stack.tar.gz`; record
   its source and checksum in README/provenance documentation.
3. Extract the full required `skill_base_real.yaml` `_base_` dependency chain
   from the old app archive into v2 `field-config/`, preserving only files
   necessary to resolve references within field-config. Validate it with v2.
4. Derive `field-config/run_config_real_for_demo_roboskill_overwrite.yaml` from
   the old proven-run config but remove the deprecated `${oc.env:SKILL_CONFIG}`
   route. Add the three SudoDeploy `_include_module_` entries and explicit
   `robo.skills` entries for soft force, base visual servo, and FT calibration.
   Use values/types from the supplied SudoDeploy patch skill config wherever
   applicable. Preserve old camera/logger/observer configuration unless it
   conflicts with v2. Any unknown hardware identifier must be marked clearly
   as a field decision—not invented.
5. Ensure the generated field config satisfies v2 semantic validation. Do not
   add SAM2/flow weights; leave asset validation to point them out explicitly.
6. Update Chinese README/provenance with what was copied, source version/checksum,
   what was adapted, and what remains absent (Sudo weights, hardware settings,
   image runtime verification).
7. Verify: shell/Python syntax, v2 `scripts/verify` behavior (structural=0;
   field assets missing exits 2), checksum checks, and YAML semantics.

## Output

Chinese only: files/lines changed, exact checks/output, copied artifacts with
sizes/checksums, adaptations, remaining prerequisites, source untouched
confirmation, Files changed, elapsed, ESCALATE.
