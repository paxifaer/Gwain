# Adversarial verifier — standalone integration candidate

Read `SPEC-build-integration.md`. Inspect, read-only, the candidate:
`/home/wangdang/work/ai-stack/code/ArgoDeploy-SudoDeploy-integration`
and the two source directories named in the spec.

Try to disprove all acceptance criteria. In particular verify:

1. Candidate is standalone and source trees were not modified.
2. No git metadata, checkpoint, virtual environment, cache, or forbidden patch/
   install/mount script slipped into the candidate.
3. The compose/start_services/deploy changes are internally consistent and do
   not run a patch mechanism at deployment time.
4. The validation scripts are non-destructive and the three required field
   configuration/assets correctly fail rather than being silently fabricated.
5. The result does not accidentally claim genuine robot compatibility before
   required field inputs and image behavior are confirmed.

Do not edit files or run any deploy/install/start/patch/Docker lifecycle/network
command. You may run read-only inspection and the candidate's documented static
verification commands. Return Chinese only: per-criterion PASS/PARTIAL/FAIL with
path/line evidence, a concise defect list prioritized by severity, exact checks
run/output, files changed none, elapsed, ESCALATEs.
