# Read-only audit: old real robot deployment as a v2 field-input source

User-directed model: Haiku.

Inspect read-only:
`/media/wangdang/My Passport/ArgoDeploy_new_rustbot_xlfxu`

Compare it against field prerequisites and deployment contracts of:
`/home/wangdang/work/ai-stack/code/ArgoDeploy-SudoDeploy-deployment-v2`

Answer whether the old real-robot deployment contains usable sources for:
- `skill_base_real.yaml`
- `run_config_real_for_demo_roboskill_overwrite.yaml`
- SudoDeploy skill modules/config references
- SAM2 / optical-flow weights or reliable references to their source
- `exp_data`
- rustbot/rbmw/bvk/wbcik wheels and installed-image/service conventions

For every candidate artifact, determine compatibility risk against v2: direct
copy, needs merge/adaptation, reference-only, or absent. Detect credentials but
do not disclose them. Do not modify, start, mount, deploy, use Docker lifecycle,
network, SSH, or robot commands.

Output Chinese only: executive answer; artifact matrix with exact paths/versions;
recommended safe extraction order; incompatibilities and blockers; Files changed
none; checks/elapsed/ESCALATE.
