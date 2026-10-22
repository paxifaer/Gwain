# Haiku adversarial verification: deployment candidate v2

Read `SPEC-build-v2.md` first. Independently inspect:
`/home/wangdang/work/ai-stack/code/ArgoDeploy-SudoDeploy-deployment-v2`
and the two source directories read-only.

Try to disprove every required design and acceptance criterion. Focus on:

1. Whether the actual config passed by `start_services.sh --config` is the
   sole authoritative configuration path, with no residual dead SKILL_CONFIG
   route.
2. Whether the field YAML semantic parser truly validates YAML inheritance,
   enabled SudoDeploy modules/skills, and selected-skill assets rather than just
   finding strings.
3. Whether validation exit semantics and `prepare --check` are genuinely
   non-destructive and distinguish structural vs field-prerequisite issues.
4. Whether all source/candidate paths, volume ownership, staging, and container
   PYTHONPATH/module imports are internally consistent.
5. Whether wheel/dependency/asset handling has any hidden false-success path,
   including optional versus mandatory skills.
6. Whether prohibited assets/metadata/caches/old patch mechanisms remain.
7. Whether README claims exceed static evidence.

Run only static checks and isolated `/tmp` fixtures. Do not edit the candidate,
sources, containers, robots, or network. Return Chinese: verdict per criterion
with exact evidence; blockers/high/medium/low findings; checks/output; remaining
field prerequisites; Files changed none; elapsed; ESCALATE.
