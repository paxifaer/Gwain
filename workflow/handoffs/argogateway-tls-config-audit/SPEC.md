# SPEC-01 — ArgoGateway TLS-mode config audit (robot-app-platform vs install_cluster.sh)

## Task type
Code investigation / gap analysis. **No code edits.** Output is a written report only.

## Background (context, not source)
Prior session `code_integration_for_argogateway_tls_deploy` (Claude Code session id
`5e6aa030-0e81-4186-80d4-dc5d14c9f275`, 2026-08-19) worked on ArgoGateway TLS
deploy. During that work the question came up: when the user toggles "TLS" in the
`robot-app-platform` frontend UI, does the generated ArgoDDS configuration actually
differ between TLS mode and plaintext mode — or does it just flip a flag without
adjusting the surrounding config the way `install_cluster.sh` does?

The reference script `install_cluster.sh` is known to branch its config generation
on TLS vs plaintext. The frontend may or may not mirror that branching.

## Question to answer (the only question)
**Does `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform` correctly
produce different ArgoDDS configuration when the user enables TLS, in all the
places where `/home/wangdang/work/ai-stack/code/ArgoDeploy/real/install_cluster.sh`
also branches on TLS?**

Sub-questions:
- Q1. What does `install_cluster.sh` do differently in TLS mode vs plaintext mode?
  Enumerate every config delta (file path, key, value, env var, port, cert path,
  feature toggle, command-line flag, etc.).
- Q2. Where in `robot-app-platform` is the ArgoDDS / ArgoGateway config generated
  or edited? (Frontend code: Rust crates, TS packages, Tauri commands, UI event
  handlers — wherever the "click TLS" action lands.)
- Q3. For each TLS-mode delta from Q1, does `robot-app-platform` mirror it when
  the user toggles TLS? If yes, where? If no, mark as a gap.
- Q4. Are there TLS-mode concerns that `install_cluster.sh` does NOT handle but
  `robot-app-platform` does? (Symmetric gaps — note them but they are not the
  primary question.)

## Inputs (read-only)
- `/home/wangdang/work/ai-stack/code/frontend/robot-app-platform/` (whole tree; start
  from `AGENTS.md` and `CLAUDE.md` if present, then search for argodds / argogateway
  / tls / config generation code paths)
- `/home/wangdang/work/ai-stack/code/ArgoDeploy/real/install_cluster.sh` (golden
  reference — what the frontend *should* be consistent with)
- Any `argo_tls.rs` file in the workspace (mentioned in prior session)

## Write-set (ONLY these files may be created/modified by W1)
- `/home/wangdang/work/ai-stack/code/Gawain/workflow/handoffs/argogateway-tls-config-audit/W1-REPORT.md`

No other file writes. No code edits. No `git` operations. No network. No tests run.

## Output contract — W1-REPORT.md structure
The report MUST contain these sections, in this order:

1. **Summary** — 3–5 sentences. Direct answer to "is there a gap?" with a one-line
   verdict (`GAP` / `NO-GAP` / `PARTIAL`).
2. **Method** — exact files read, exact grep patterns used, exact line ranges
   examined. Verifier must be able to reproduce by following these steps.
3. **Q1 — install_cluster.sh TLS branches** — table with columns:
   `delta_id | file:line | what changes in TLS mode | what changes in plaintext mode`
4. **Q2 — robot-app-platform config-generation surface** — list of code locations
   (file:line) where ArgoDDS config is built, sent, or persisted. Note which ones
   reference TLS at all.
5. **Q3 — Gap matrix** — table with columns:
   `delta_id (from Q1) | mirrored in robot-app-platform? (YES/NO/PARTIAL) | location (file:line) | evidence (snippet ≤3 lines)`
6. **Q4 — Symmetric gaps** — bullet list, may be empty.
7. **Recommendations** — for each `NO`/`PARTIAL` in Q3, describe what should be
   added/changed in `robot-app-platform`. **Describe, do not edit.** No code blocks
   longer than 5 lines. The user will decide whether to dispatch a follow-up
   Develop worker.
8. **ESCALATEs** — any judgment call W1 made alone (e.g. ambiguous code that
   could be read two ways, missing context that the user must clarify).

The report is the entire deliverable. W1's final message to the orchestrator
must be ≤200 words and point to the report file.

## Acceptance criteria (how V1 will judge W1)
V1 will adversarially check, for each Q1 delta and each Q3 verdict, that the
claimed file:line actually exists and the quoted snippet is accurate. Any
fabricated line, any mis-attributed snippet, any Q3 `YES` that is actually `NO`
in the source — V1 returns FAIL and the orchestrator re-dispatches W1.

## Risk classification
- **Risk: low.** Investigation only; no code edits; no control/kinematics/
  dynamics algorithms; no derivations.
- **High-Risk Reasoning Gate:** not triggered. Task-state layout not required.
- **Cross-boundary integration test code:** none written. Traceability contract
  not triggered.
- Convention used: standard `SPEC-*.md` + `PROMPT-W*` (opt-out of task-state
  layout — task has no Discussion overhead, single investigation worker).

## Dispatch plan
- W1: investigation worker (general-purpose Agent, foreground).
- V1: verifier worker (general-purpose Agent, adversarial mandate), dispatched
  after W1 returns.
- Recursion floor: 2 free agents (W1, V1) + 1 judgment (orchestrator).
