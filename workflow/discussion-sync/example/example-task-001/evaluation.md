<!--
evaluation.md — copied from templates/evaluation.md and filled for example-task-001.
Each criterion is independently checkable by the V1 verifier.
-->

# Evaluation

- [ ] decisions.md § Decisions holds exactly one D-001 ("use TLS (not mTLS) for example-app transport") with a reason; grep `decisions.md` for `D-001`
- [ ] sync/001.yaml byte-identical to expected/after-02-decision/extractor-output.yaml; both parse as YAML with valid `changes.decisions[0]` entry (id/class/content/reason/revises)
- [ ] after-ingest/state.md Status is no longer `idle`, and after-ingest/decisions.md § Decisions contains the D-001 line (PASS/FAIL read independently)