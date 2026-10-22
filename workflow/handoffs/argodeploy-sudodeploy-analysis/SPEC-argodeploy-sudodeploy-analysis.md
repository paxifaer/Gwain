# ArgoDeploy / ArgoSudoDeploy_Patch read-only integration analysis

model_selection:
  model: default
  mode: automatic
  reason: deployment_analysis_and_task_decomposition

risk: normal — read-only analysis; no control, kinematics, dynamics, scheduling, or concurrency algorithm is changed.

## Objective

Explain what `/home/wangdang/下载/ArgoSudoDeploy_Patch` changes or provides, how it relates to the real deployment at `/home/wangdang/work/ai-stack/code/ArgoDeploy/real`, and give a safe, concrete integration procedure for `/home/wangdang/work/ai-stack/code/ArgoDeploy`.

## Acceptance criteria

1. Inventory the patch contents by functional role, identifying its entry points and runtime/deployment dependencies.
2. Compare the patch's deployment scripts/configuration with `ArgoDeploy/real` and identify exact integration targets, conflicts, and missing prerequisites.
3. Distinguish files that should be copied, merged, invoked, or explicitly not integrated, with path-level evidence.
4. Produce an ordered integration plan with validation and rollback steps; it must be non-destructive and must not assume a production robot is available.
5. Surface uncertain or unsafe choices as `ESCALATE` rather than choosing silently.

## Constraints

- Read-only. Do not modify any project, patch, deployment, git, service, container, or system file.
- Do not run deploy/install/start/patch scripts; static inspection only.
- Treat both directories as potentially dirty user worktrees. Do not reset, checkout, clean, or create commits.
- Do not expose credentials or tokens if encountered; redact them in the report.

## Inputs

- `/home/wangdang/work/ai-stack/code/ArgoDeploy/real`
- `/home/wangdang/work/ai-stack/code/ArgoDeploy`
- `/home/wangdang/下载/ArgoSudoDeploy_Patch`
- `/home/wangdang/work/ai-stack/code/Gawain/workflow/bootstrap.md`
- `/home/wangdang/work/ai-stack/code/Gawain/workflow/rule-map.md` as directed by bootstrap

## Output contract

Return a concise Chinese report containing:

1. `结论` (one-paragraph executive summary).
2. `补丁做了什么` (functional components and entry points).
3. `与 ArgoDeploy/real 的关系` (path-level mapping and incompatibilities).
4. `建议集成方案` with numbered, ordered, reversible steps, each naming exact source and destination paths plus validation and rollback.
5. `风险与前置条件`.
6. `证据` listing inspected paths and relevant script/config symbols or line ranges.
7. `Files changed: none`, checks performed, elapsed time, and `ESCALATE` items.
