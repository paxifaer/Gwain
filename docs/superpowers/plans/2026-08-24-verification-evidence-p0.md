# Verification Evidence P0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the smallest executable Gawain verification core that prevents false PASS from mutable candidates, false-green tests, and malformed or unsafe traces.

**Architecture:** A Python 3.11+ package loads a versioned evidence-bundle JSON document and referenced JSONL trace artifacts. JSON Schema enforces the wire shape; focused Python invariants enforce hashes, policy closure, test semantics, trace causality, and secret blocking. The CLI is read-only and returns nonzero for any validation issue.

**Tech Stack:** Python 3.11+, `jsonschema` 4.x, `pytest`, SHA-256, JSON/JSONL

---

### Task 1: Candidate identity, evidence integrity, and hard verdict gate

**Files:**
- Create: `pyproject.toml`
- Create: `gawain_verification/__init__.py`
- Create: `gawain_verification/schema.py`
- Create: `gawain_verification/bundle.py`
- Create: `schemas/evidence-bundle.v1.schema.json`
- Test: `tests/test_bundle_validator.py`

- [ ] **Step 1: Write failing candidate and policy tests**

Create tests using this public API:

```python
from gawain_verification.bundle import compute_candidate_id, validate_bundle


def test_rejects_candidate_id_mismatch(valid_bundle, bundle_root):
    valid_bundle["candidate"]["candidate_id"] = "sha256:" + "0" * 64
    issues = validate_bundle(valid_bundle, bundle_root)
    assert "candidate_id does not match candidate inputs" in issue_messages(issues)


def test_pass_requires_every_required_check(valid_bundle, bundle_root):
    valid_bundle["policy"]["required_checks"].append("trace.complete")
    issues = validate_bundle(valid_bundle, bundle_root)
    assert "required check trace.complete is missing" in issue_messages(issues)


def test_nuance_is_not_a_valid_check_status(valid_bundle, bundle_root):
    valid_bundle["checks"][0]["status"] = "NUANCE"
    issues = validate_bundle(valid_bundle, bundle_root)
    assert any(issue.code == "schema" for issue in issues)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m pytest tests/test_bundle_validator.py -q`

Expected: collection fails because `gawain_verification.bundle` does not exist.

- [ ] **Step 3: Add the versioned bundle schema and minimal validator**

The schema must define these closed enums and objects:

```python
CHECK_STATUSES = {"PASS", "FAIL", "BLOCKED_INFRA", "FLAKY", "NOT_RUN", "ENV_INVALID"}
CLAIM_VERDICTS = {"PROVEN", "DISPROVEN", "INCONCLUSIVE"}
DECISIONS = {"PASS", "FAIL", "BLOCKED_INFRA", "FLAKY", "WAIVED"}


def compute_candidate_id(candidate: dict[str, object]) -> str:
    identity = {
        key: candidate[key]
        for key in ("repository", "base_commit", "tree_hash", "diff_hash")
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
```

`validate_bundle()` must return `list[ValidationIssue]`; it must never silently
rewrite input. Overall PASS requires every required check to exist exactly once
with status PASS, every claim to be PROVEN, and all evidence references to
resolve to verified artifacts.

- [ ] **Step 4: Add evidence path and hash tests, verify RED, then GREEN**

Add tests for `../` traversal, missing artifacts, SHA-256 mismatch, duplicate
artifact IDs, and claim/check references to unknown artifacts. Run the focused
test after adding each behavior and confirm the new test fails before changing
production code.

- [ ] **Step 5: Add typed waiver tests and implementation**

WAIVED must require:

```json
{
  "author_kind": "human",
  "author": "user identity",
  "reason": "specific reason",
  "scope": ["claim-id"],
  "policy_version": "gawain.policy.v1",
  "expires_at": "2026-09-24T00:00:00Z"
}
```

PASS cannot contain a waiver, and WAIVED is never normalized to PASS.

- [ ] **Step 6: Run focused tests**

Run: `python3 -m pytest tests/test_bundle_validator.py -q`

Expected: all bundle tests PASS.

### Task 2: Test manifest semantics that reject false-green runs

**Files:**
- Modify: `schemas/evidence-bundle.v1.schema.json`
- Modify: `gawain_verification/bundle.py`
- Test: `tests/test_test_gate.py`

- [ ] **Step 1: Write failing false-green tests**

Use a parameterized test for these mutations of a valid dynamic test record:

```python
@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("executed_test_count", 0, "executed zero tests"),
        ("executed_test_count", 2, "executed fewer tests than expected"),
        ("ignored_test_count", 1, "required tests were ignored"),
        ("failed_test_count", 1, "test failures are present"),
        ("exit_code", 1, "test command exited nonzero"),
    ],
)
def test_rejects_false_green_result(valid_bundle, bundle_root, field, value, message):
    valid_bundle["tests"][0][field] = value
    issues = validate_bundle(valid_bundle, bundle_root)
    assert message in issue_messages(issues)
```

Also add separate tests for required/observed level mismatch and missing dynamic
evidence.

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m pytest tests/test_test_gate.py -q`

Expected: failures show that false-green test semantics are not implemented.

- [ ] **Step 3: Implement the minimal test gate**

The schema must require:

```text
id, required_level, observed_level, expected_outcome, status,
command, cwd, environment_fingerprint, expected_test_count,
executed_test_count, passed_test_count, failed_test_count,
ignored_test_count, exit_code, oracle, evidence
```

`required_level` and `observed_level` use the same closed enum and must be equal;
the validator must not pretend that browser evidence covers Tauri desktop or
real-device E2E. PASS is satisfied only by:

```python
expected_outcome == "PASS" and status == "PASS"
```

A negative test is satisfied only by:

```python
expected_outcome == "REJECT" and status == "EXPECTED_REJECT"
```

Dynamic levels (`component`, `integration`, `browser`, `desktop`, `deployment`,
`real_device_e2e`) require at least one referenced trace or test-report artifact.

- [ ] **Step 4: Run focused tests**

Run: `python3 -m pytest tests/test_test_gate.py -q`

Expected: all test-gate tests PASS.

### Task 3: Versioned causal trace validation and secret blocking

**Files:**
- Create: `schemas/trace-event.v1.schema.json`
- Create: `gawain_verification/trace.py`
- Modify: `gawain_verification/bundle.py`
- Test: `tests/test_trace_validator.py`

- [ ] **Step 1: Write failing trace-schema and graph tests**

Tests must exercise this API:

```python
from gawain_verification.trace import validate_trace_file


def test_rejects_missing_parent_span(valid_bundle, trace_file, bundle_root):
    replace_parent(trace_file, "f" * 16)
    issues = validate_trace_file(trace_file, valid_bundle, bundle_root)
    assert "parent span does not exist" in issue_messages(issues)


def test_rejects_span_without_terminal_event(valid_bundle, trace_file, bundle_root):
    remove_event_kind(trace_file, "SPAN_END")
    issues = validate_trace_file(trace_file, valid_bundle, bundle_root)
    assert "span has no SPAN_END" in issue_messages(issues)
```

Add tests for invalid 24-bit trace IDs, duplicate event IDs, multiple roots,
missing SPAN_START, cross-run/candidate/test contamination, and event-specific
FAIL/ERROR/STATE fields.

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m pytest tests/test_trace_validator.py -q`

Expected: collection fails because `gawain_verification.trace` does not exist.

- [ ] **Step 3: Add trace schema and graph validation**

Every event requires:

```text
schema_version, event_id, ts, level, event_kind, run_id,
candidate_id, test_case_id, trace_id, span_id, parent_span_id,
operation_id, attempt, service, instance_id, sequence
```

Use 32 lowercase hex characters for `trace_id` and 16 for span IDs. Event kinds
are `SPAN_START`, `STATE`, `FAIL`, `ERROR`, and `SPAN_END`. Each distinct span
must have exactly one start and one end; each trace must have exactly one root;
all non-root parents must exist.

- [ ] **Step 4: Write failing secret tests**

Add nested keys named `password`, `passwd`, `token`, `api_key`, `secret`,
`private_key`, `authorization`, and `cookie`, plus PEM private-key material in a
string. Confirm each test fails for the intended reason.

- [ ] **Step 5: Implement recursive secret blocking**

Exact sensitive keys are rejected unless their string value is one of
`[REDACTED]`, `<redacted>`, or `***`. Any string containing a private-key PEM
header is rejected. Do not attempt heuristic mutation or redaction inside the
validator; producers must redact before persistence.

- [ ] **Step 6: Run focused tests**

Run: `python3 -m pytest tests/test_trace_validator.py -q`

Expected: all trace tests PASS.

### Task 4: CLI, examples, and repository integration

**Files:**
- Create: `gawain_verification/cli.py`
- Create: `gawain_verification/__main__.py`
- Create: `examples/verification-core/evidence-bundle.json`
- Create: `examples/verification-core/trace.jsonl`
- Modify: `README.md`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

```python
def test_cli_returns_zero_for_valid_bundle(valid_example_path):
    result = subprocess.run(
        [sys.executable, "-m", "gawain_verification", "validate", str(valid_example_path)],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0
    assert "VALID" in result.stdout


def test_cli_returns_one_and_lists_issues_for_invalid_bundle(invalid_bundle_path):
    result = subprocess.run(
        [sys.executable, "-m", "gawain_verification", "validate", str(invalid_bundle_path)],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "INVALID" in result.stderr
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m pytest tests/test_cli.py -q`

Expected: CLI module is missing.

- [ ] **Step 3: Implement read-only CLI and valid example**

The command is:

```text
python3 -m gawain_verification validate <evidence-bundle.json>
```

It prints a short VALID summary on success. On failure it prints stable
`<code>: <location>: <message>` issue lines to stderr and exits 1. Parse or I/O
failure exits 2. It never changes the bundle or artifacts.

- [ ] **Step 4: Document the new boundary**

README must call the validator a P0 foundation rather than a complete verifier.
It must state explicitly that dispatch remains legacy and that clean-room
execution, remote collectors, fault injection, and OTel export are later work.

- [ ] **Step 5: Run complete verification**

Run:

```bash
python3 -m pytest -q
python3 -m gawain_verification validate examples/verification-core/evidence-bundle.json
python3 -m compileall -q gawain_verification
git diff --check
```

Expected: all tests PASS, example reports VALID, compileall and diff check exit
zero.

## Plan self-review

- Spec coverage: all three selected P0s have failing tests, implementation,
  focused verification, and a full integration command.
- Scope control: no scheduler, model router, daemon, dashboard, collector, or
  observability backend is introduced.
- Type consistency: bundle, test, trace, verdict, and CLI field names are fixed
  in this plan and shared by all tasks.
- Deferred work is explicitly documented in the audit rather than silently
  treated as fixed.
