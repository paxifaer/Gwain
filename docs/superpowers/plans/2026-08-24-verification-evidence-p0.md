# Gawain Verification Core P0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only, harness-neutral verification core that rejects mutable or mismatched candidates, false-green test records, unsafe evidence, broken causal traces, and unsupported READY verdicts.

**Architecture:** A small Python 3.11+ package validates one sealed evidence bundle. Focused modules own canonical identity, authorization/environment checks, artifacts, test semantics, traces, and verdict derivation; the CLI only loads files and reports deterministic issues. The runtime never edits Candidate repositories and contains no scheduler or repair loop.

**Tech Stack:** Python 3.11+, standard library, `jsonschema` 4.x, `pytest`, JSON/JSONL, SHA-256

**Design source:** `docs/superpowers/specs/2026-08-24-gawain-service-manager-pilot-design.md`

---

## File map

| File | Responsibility |
|---|---|
| `pyproject.toml` | Package metadata, dependencies, pytest configuration, CLI entrypoint |
| `.gitignore` | Python caches and local evidence runs only |
| `gawain_verification/issues.py` | Stable `ValidationIssue` type and issue collector |
| `gawain_verification/canonical.py` | Canonical JSON and SHA-256 identity functions |
| `gawain_verification/schema.py` | Load and apply bundled JSON Schemas |
| `gawain_verification/identity.py` | Contract, Candidate Set, Permit, environment/deployment validation |
| `gawain_verification/artifacts.py` | Safe relative paths, file digests, manifest and evidence references |
| `gawain_verification/test_gate.py` | Exact test-count, layer, outcome, and oracle rules |
| `gawain_verification/secrets.py` | Recursive sensitive-key and private-key-material rejection |
| `gawain_verification/trace.py` | JSONL parsing plus W3C causal graph validation |
| `gawain_verification/verdict.py` | Closed verdict derivation and human-waiver separation |
| `gawain_verification/bundle.py` | Pure orchestration API over the focused validators |
| `gawain_verification/cli.py`, `__main__.py` | Read-only `validate` command and exit codes |
| `schemas/*.json` | Versioned machine-readable bundle and trace wire contracts |
| `tests/` | Unit and CLI regression coverage; replaces the aborted untracked drafts |
| `examples/verification-core/` | One sealed valid bundle and trace for consumer smoke testing |

The existing untracked `tests/conftest.py` and `tests/test_bundle_validator.py` are aborted drafts from the pre-design attempt. This plan deliberately adopts and rewrites them; it does not touch `workflow/handoffs/` or unrelated untracked files.

### Task 1: Package skeleton, stable issues, and canonical identities

**Files:**
- Create: `pyproject.toml`
- Modify: `.gitignore`
- Create: `gawain_verification/__init__.py`
- Create: `gawain_verification/issues.py`
- Create: `gawain_verification/canonical.py`
- Rewrite: `tests/conftest.py`
- Create: `tests/test_identity.py`

- [ ] **Step 1: Replace the aborted fixture with Contract and multi-component Candidate Set fixtures**

Use these canonical shapes in `tests/conftest.py`:

```python
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from gawain_verification.canonical import content_id


@pytest.fixture
def valid_contract() -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": "gawain.verification-contract.v1",
        "device_id": "SP000065",
        "service_id": "gawain-canary",
        "unit": "gawain-canary.service",
        "systemd_scope": "user",
        "action": "Restart",
        "required_test_cases": ["P-01", "N-01", "N-02", "N-03", "N-04", "N-05"],
    }
    body["contract_id"] = content_id("contract", body)
    return body


@pytest.fixture
def valid_candidate() -> dict[str, object]:
    components = [
        {
            "name": "frontend",
            "repository": "ssh://git.example/frontend.git",
            "base_commit": "a" * 40,
            "head_commit": "b" * 40,
            "tree_hash": "c" * 64,
            "diff_hash": "d" * 64,
            "build_recipe_id": "sha256:" + "e" * 64,
            "build_artifact_sha256": "sha256:" + "f" * 64,
        },
        {
            "name": "gateway",
            "repository": "ssh://git.example/gateway.git",
            "base_commit": "1" * 40,
            "head_commit": "2" * 40,
            "tree_hash": "3" * 64,
            "diff_hash": "4" * 64,
            "build_recipe_id": "sha256:" + "5" * 64,
            "build_artifact_sha256": "sha256:" + "6" * 64,
        },
    ]
    candidate: dict[str, object] = {
        "schema_version": "gawain.candidate-set.v1",
        "components": components,
    }
    candidate["candidate_id"] = content_id("candidate", candidate)
    return candidate


@pytest.fixture
def bundle_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def cloned(value):
    return copy.deepcopy(value)
```

- [ ] **Step 2: Write identity tests before package code exists**

Create `tests/test_identity.py`:

```python
from gawain_verification.canonical import canonical_json, content_id


def test_canonical_json_is_key_order_independent() -> None:
    assert canonical_json({"b": 2, "a": 1}) == b'{"a":1,"b":2}'


def test_content_id_ignores_its_own_identity_field(valid_contract) -> None:
    original = valid_contract["contract_id"]
    valid_contract["contract_id"] = "sha256:" + "0" * 64
    assert content_id("contract", valid_contract) == original


def test_candidate_component_order_is_canonical(valid_candidate) -> None:
    original = valid_candidate["candidate_id"]
    valid_candidate["components"].reverse()
    assert content_id("candidate", valid_candidate) == original


def test_duplicate_component_name_is_rejected(valid_candidate) -> None:
    from gawain_verification.identity import validate_candidate

    valid_candidate["components"].append(valid_candidate["components"][0].copy())
    assert "duplicate_component" in {i.code for i in validate_candidate(valid_candidate)}
```

- [ ] **Step 3: Run the focused test and confirm RED**

Run: `python3 -m pytest tests/test_identity.py -q`

Expected: collection fails with `ModuleNotFoundError: No module named 'gawain_verification'`.

- [ ] **Step 4: Add package metadata and stable issue type**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[project]
name = "gawain-verification"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["jsonschema>=4.23,<5"]

[project.optional-dependencies]
test = ["pytest>=8,<10"]

[project.scripts]
gawain-verify = "gawain_verification.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Create `gawain_verification/issues.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True, order=True)
class ValidationIssue:
    code: str
    location: str
    message: str


def issue(code: str, location: str, message: str) -> ValidationIssue:
    return ValidationIssue(code=code, location=location, message=message)
```

Export `ValidationIssue` from `gawain_verification/__init__.py`.

- [ ] **Step 5: Implement canonical JSON and identity computation**

Create `gawain_verification/canonical.py`:

```python
from __future__ import annotations

import hashlib
import json
from typing import Any


IDENTITY_FIELDS = {
    "contract": "contract_id",
    "candidate": "candidate_id",
    "permit": "permit_id",
    "bundle": "bundle_id",
}


def _normalized(kind: str, value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result.pop(IDENTITY_FIELDS[kind], None)
    if kind == "candidate":
        result["components"] = sorted(result.get("components", []), key=lambda item: item["name"])
    return result


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def content_id(kind: str, value: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json(_normalized(kind, value)))
```

Add `validate_candidate()` in `gawain_verification/identity.py`; it checks a non-empty component list, unique names, exact digest formats, and `candidate_id == content_id("candidate", candidate)` without mutating input.

- [ ] **Step 6: Run tests and commit**

Run: `python3 -m pytest tests/test_identity.py -q`

Expected: all identity tests pass.

Commit:

```bash
git add pyproject.toml .gitignore gawain_verification tests/conftest.py tests/test_identity.py
git commit -m "feat(verification): add canonical contract and candidate identities"
```

### Task 2: Contract, Permit, `full_access`, and deployed-environment gate

**Files:**
- Create: `schemas/verification-contract.v1.schema.json`
- Create: `schemas/evidence-bundle.v1.schema.json`
- Create: `gawain_verification/schema.py`
- Modify: `gawain_verification/identity.py`
- Create: `tests/test_authorization_gate.py`

- [ ] **Step 1: Write failing authorization and deployment tests**

Create `tests/test_authorization_gate.py` with these cases:

```python
from datetime import datetime, timezone

from gawain_verification.identity import validate_identity_gate


NOW = datetime(2026, 8, 25, 3, 0, tzinfo=timezone.utc)


def codes(contract, candidate, permit, environment):
    return {i.code for i in validate_identity_gate(contract, candidate, permit, environment, now=NOW)}


def test_full_access_does_not_replace_permit(valid_contract, valid_candidate, valid_environment):
    assert "missing_permit" in codes(valid_contract, valid_candidate, None, valid_environment)


def test_full_access_does_not_allow_wrong_device(valid_contract, valid_candidate, valid_permit, valid_environment):
    valid_permit["full_access"] = True
    valid_environment["device_id"] = "SP000056"
    assert "device_identity_mismatch" in codes(valid_contract, valid_candidate, valid_permit, valid_environment)


def test_expired_permit_is_rejected(valid_contract, valid_candidate, valid_permit, valid_environment):
    valid_permit["not_after"] = "2026-08-25T02:59:59Z"
    assert "permit_expired" in codes(valid_contract, valid_candidate, valid_permit, valid_environment)


def test_installed_digest_must_match_candidate(valid_contract, valid_candidate, valid_permit, valid_environment):
    valid_environment["installed_components"][0]["sha256"] = "sha256:" + "0" * 64
    assert "installed_digest_mismatch" in codes(valid_contract, valid_candidate, valid_permit, valid_environment)
```

Extend `tests/conftest.py` with a Permit scoped to `SP000065`, action `Restart`, service `gawain-canary`, and an environment whose installed component digests match Candidate Set build artifact digests.

- [ ] **Step 2: Run the focused test and confirm RED**

Run: `python3 -m pytest tests/test_authorization_gate.py -q`

Expected: import or assertion failures because the gate is not implemented.

- [ ] **Step 3: Add closed JSON Schemas**

The Contract schema must use `additionalProperties: false`, require the fields from §5.1 of the design, and require `action` to be a non-empty string. The verification core is harness- and Pilot-neutral: the Pilot Contract chooses `Restart`, while the Permit independently authorizes that exact action. The bundle schema must require these top-level keys:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://gawain.local/schemas/evidence-bundle.v1.schema.json",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version", "run_id", "contract", "candidate", "permit",
    "environment", "artifacts", "tests", "claims", "traces", "verdict"
  ],
  "properties": {
    "schema_version": {"const": "gawain.evidence-bundle.v1"},
    "run_id": {"type": "string", "pattern": "^run-[A-Za-z0-9._-]+$"},
    "contract": {"type": "object"},
    "candidate": {"type": "object"},
    "permit": {"type": "object"},
    "environment": {"type": "object"},
    "artifacts": {"type": "array"},
    "tests": {"type": "array"},
    "claims": {"type": "array"},
    "traces": {"type": "array"},
    "verdict": {"type": "object"},
    "waivers": {"type": "array"},
    "human_acceptance": {"type": "object"}
  }
}
```

`gawain_verification/schema.py` loads schemas with `importlib.resources`, calls `Draft202012Validator.iter_errors`, and returns stable `schema_error` issues sorted by JSON path.

- [ ] **Step 4: Implement the exact authorization gate**

The Permit shape is:

```python
{
    "schema_version": "gawain.execution-permit.v1",
    "permit_id": "sha256:...",
    "issuer_kind": "human",
    "issuer": "operator identity",
    "device_ids": ["SP000065"],
    "service_ids": ["gawain-canary"],
    "actions": ["Restart", "DeployFixture", "InjectFault", "Rollback"],
    "not_before": "2026-08-25T00:00:00Z",
    "not_after": "2026-08-26T00:00:00Z",
    "full_access": True,
}
```

`validate_identity_gate()` must independently check Contract ID, Candidate ID, Permit ID, human issuer, current time window, exact target device/service/action, environment host identity, Gateway endpoint, and every installed digest. `full_access` skips only optional software policy checks passed as `software_gate_violations`; it never suppresses any issue above.

- [ ] **Step 5: Run tests and commit**

Run:

```bash
python3 -m pytest tests/test_identity.py tests/test_authorization_gate.py -q
```

Expected: all tests pass.

Commit:

```bash
git add schemas gawain_verification/schema.py gawain_verification/identity.py tests
git commit -m "feat(verification): enforce permit and deployed identity gate"
```

### Task 3: Content-addressed artifact manifest and safe references

**Files:**
- Create: `gawain_verification/artifacts.py`
- Create: `tests/test_artifact_gate.py`
- Modify: `schemas/evidence-bundle.v1.schema.json`

- [ ] **Step 1: Write failing artifact attacks**

Create tests for absolute paths, `..`, duplicate artifact IDs, missing files, symlinks escaping bundle root, byte-size mismatch, digest mismatch, and unknown evidence references:

```python
from gawain_verification.artifacts import validate_artifacts


def test_symlink_escape_is_rejected(valid_artifact_bundle, tmp_path):
    outside = tmp_path.parent / "secret.txt"
    outside.write_text("not evidence", encoding="utf-8")
    link = tmp_path / "artifacts" / "escape"
    link.symlink_to(outside)
    valid_artifact_bundle["artifacts"][0]["path"] = "artifacts/escape"
    assert "artifact_path_escape" in {i.code for i in validate_artifacts(valid_artifact_bundle, tmp_path)}


def test_unknown_claim_reference_is_rejected(valid_artifact_bundle, tmp_path):
    valid_artifact_bundle["claims"][0]["evidence"] = ["missing-id"]
    assert "unknown_evidence_ref" in {i.code for i in validate_artifacts(valid_artifact_bundle, tmp_path)}
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run: `python3 -m pytest tests/test_artifact_gate.py -q`

Expected: module import fails.

- [ ] **Step 3: Implement path and digest checks without following unsafe links**

Use this boundary in `artifacts.py`:

```python
def resolve_artifact(root: Path, relative: str) -> tuple[Path | None, ValidationIssue | None]:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        return None, issue("unsafe_artifact_path", relative, "artifact path must be a safe relative POSIX path")
    candidate = root.joinpath(*pure.parts)
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (FileNotFoundError, ValueError):
        return None, issue("artifact_path_escape", relative, "artifact is missing or resolves outside bundle root")
    if candidate.is_symlink():
        return None, issue("artifact_symlink", relative, "artifact paths may not be symlinks")
    return resolved, None
```

Hash files in 1 MiB chunks, compare both `bytes` and `sha256`, build an ID map, then validate every reference from tests, claims, traces, environment, and deployment records.

- [ ] **Step 4: Run tests and commit**

Run: `python3 -m pytest tests/test_artifact_gate.py -q`

Expected: all artifact tests pass.

Commit:

```bash
git add gawain_verification/artifacts.py schemas/evidence-bundle.v1.schema.json tests/test_artifact_gate.py tests/conftest.py
git commit -m "feat(verification): validate content-addressed evidence artifacts"
```

### Task 4: False-green test and oracle gate

**Files:**
- Create: `gawain_verification/test_gate.py`
- Create: `tests/test_test_gate.py`
- Modify: `schemas/evidence-bundle.v1.schema.json`

- [ ] **Step 1: Write the failing count and outcome matrix**

Use a valid record with `required_level=observed_level=tauri`, one expected and executed test, zero ignored/failed, `expected_outcome=PASS`, `status=PASS`, and both `tauri-interaction` and `application-trace` evidence. Mutate it with:

```python
import pytest

from gawain_verification.test_gate import validate_tests


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("executed_test_count", 0, "zero_tests_executed"),
        ("executed_test_count", 2, "test_count_mismatch"),
        ("ignored_test_count", 1, "required_test_ignored"),
        ("failed_test_count", 1, "test_failures_present"),
        ("exit_code", 1, "test_command_failed"),
    ],
)
def test_false_green_is_rejected(valid_test_bundle, field, value, code):
    valid_test_bundle["tests"][0][field] = value
    assert code in {i.code for i in validate_tests(valid_test_bundle)}


def test_negative_case_requires_expected_reject(valid_test_bundle):
    record = valid_test_bundle["tests"][0]
    record["expected_outcome"] = "REJECT"
    record["status"] = "PASS"
    assert "negative_test_not_rejected" in {i.code for i in validate_tests(valid_test_bundle)}
```

- [ ] **Step 2: Add layer-substitution and dynamic-evidence tests**

The exact layer enum is `unit`, `component`, `integration`, `browser`, `tauri`, `deployment`, `real_device_e2e`. Required and observed levels must be equal. Required evidence kinds are:

```python
REQUIRED_EVIDENCE_KINDS = {
    "browser": {"browser-interaction"},
    "tauri": {"tauri-interaction", "application-trace"},
    "deployment": {"deployment-record", "installed-digest"},
    "real_device_e2e": {"device-state", "application-trace"},
}
```

Write one failing test per mapping entry and a test proving browser evidence cannot satisfy Tauri.

- [ ] **Step 3: Run the focused test and confirm RED**

Run: `python3 -m pytest tests/test_test_gate.py -q`

Expected: module import fails.

- [ ] **Step 4: Implement the closed test record gate**

Each record requires `id`, `required_level`, `observed_level`, `expected_outcome`, `status`, `command`, `cwd`, `environment_fingerprint`, all five counts, `exit_code`, a non-empty structured `oracle`, and evidence IDs. Enforce:

```python
positive_ok = record["expected_outcome"] == "PASS" and record["status"] == "PASS"
negative_ok = record["expected_outcome"] == "REJECT" and record["status"] == "EXPECTED_REJECT"
counts_ok = (
    record["expected_test_count"] > 0
    and record["executed_test_count"] == record["expected_test_count"]
    and record["passed_test_count"] + record["failed_test_count"] + record["ignored_test_count"]
        == record["executed_test_count"]
    and record["failed_test_count"] == 0
    and record["ignored_test_count"] == 0
    and record["exit_code"] == 0
)
```

For a negative case, `passed_test_count` still counts the harness assertion that the rejection occurred; the observed application rejection is expressed by `status=EXPECTED_REJECT`, not by a nonzero harness exit.

- [ ] **Step 5: Run tests and commit**

Run: `python3 -m pytest tests/test_test_gate.py -q`

Expected: all test-gate tests pass.

Commit:

```bash
git add gawain_verification/test_gate.py schemas/evidence-bundle.v1.schema.json tests
git commit -m "feat(verification): reject false-green and substituted tests"
```

### Task 5: W3C causal trace and secret gate

**Files:**
- Create: `schemas/trace-event.v1.schema.json`
- Create: `gawain_verification/secrets.py`
- Create: `gawain_verification/trace.py`
- Create: `tests/test_trace_gate.py`

- [ ] **Step 1: Build a valid trace fixture and failing graph tests**

The fixture uses one 32-hex trace ID, two spans, one root, one child, and exactly one `SPAN_START`/`SPAN_END` per span. Every event includes:

```python
{
    "schema_version": "gawain.trace-event.v1",
    "event_id": "evt-0001",
    "ts": "2026-08-25T03:00:00.000Z",
    "level": "INFO",
    "event_kind": "SPAN_START",
    "run_id": "run-pilot-001",
    "contract_id": "sha256:...",
    "candidate_id": "sha256:...",
    "test_case_id": "P-01",
    "attempt_id": "attempt-1",
    "operation_id": "0123456789abcdef0123456789abcdef",
    "trace_id": "0123456789abcdef0123456789abcdef",
    "span_id": "0123456789abcdef",
    "parent_span_id": None,
    "service": "frontend.renderer",
    "instance_id": "skyline-test-1",
    "sequence": 1,
    "attributes": {},
}
```

Write failing tests for invalid trace/span widths, duplicate event ID, duplicate sequence, multiple roots, missing parent, parent cycle, missing start/end, duplicate start/end, cross-run/candidate/contract/test contamination, and `operation_id != trace_id`.

- [ ] **Step 2: Write failing event-specific and secret tests**

`STATE` requires `from_state` and `to_state`; `FAIL` requires caller, callee, phase, error class/message/cause; `ERROR` requires error class/message/cause; `SPAN_END` requires status in `OK|ERROR|CANCELLED|TIMEOUT`.

Parameterize sensitive keys `password`, `passwd`, `token`, `api_key`, `secret`, `private_key`, `authorization`, and `cookie` at multiple nesting levels. Add PEM strings beginning `-----BEGIN PRIVATE KEY-----` and `-----BEGIN RSA PRIVATE KEY-----`.

- [ ] **Step 3: Run the focused test and confirm RED**

Run: `python3 -m pytest tests/test_trace_gate.py -q`

Expected: module import fails.

- [ ] **Step 4: Implement recursive secret rejection**

Use exact normalized keys and allow only explicit redaction sentinels:

```python
SENSITIVE_KEYS = frozenset({
    "password", "passwd", "token", "api_key", "secret",
    "private_key", "authorization", "cookie",
})
REDACTED = frozenset({"[REDACTED]", "<redacted>", "***"})
PEM_HEADERS = ("-----BEGIN PRIVATE KEY-----", "-----BEGIN RSA PRIVATE KEY-----")
```

Return issues; never mutate or redact persisted evidence inside the validator.

- [ ] **Step 5: Implement trace parsing and graph validation**

`validate_trace_file(path, expected_context)` reads UTF-8 JSONL line by line, reports line-numbered parse/schema issues, blocks secrets before adding an event to the graph, then validates uniqueness, exactly one root, parent existence, acyclicity, start/end cardinality, sequence monotonicity, context equality, and operation continuity.

- [ ] **Step 6: Run tests and commit**

Run: `python3 -m pytest tests/test_trace_gate.py -q`

Expected: all trace tests pass.

Commit:

```bash
git add schemas/trace-event.v1.schema.json gawain_verification/secrets.py gawain_verification/trace.py tests
git commit -m "feat(verification): validate causal traces and block secrets"
```

### Task 6: Closed verdict state machine and separate human acceptance

**Files:**
- Create: `gawain_verification/verdict.py`
- Create: `tests/test_verdict.py`
- Modify: `schemas/evidence-bundle.v1.schema.json`

- [ ] **Step 1: Write the verdict table as failing parameterized tests**

```python
import pytest

from gawain_verification.verdict import derive_verdict


@pytest.mark.parametrize(
    ("facts", "expected"),
    [
        ({"aborted": True}, "ABORTED"),
        ({"environment_valid": False}, "ENV_INVALID"),
        ({"infra_blocked": True}, "BLOCKED_INFRA"),
        ({"evidence_complete": False}, "INCONCLUSIVE"),
        ({"candidate_failed": True}, "FAIL"),
        ({"all_obligations_proven": True}, "READY_FOR_HUMAN_ACCEPTANCE"),
    ],
)
def test_closed_verdict_precedence(facts, expected):
    baseline = {
        "aborted": False,
        "environment_valid": True,
        "infra_blocked": False,
        "evidence_complete": True,
        "candidate_failed": False,
        "all_obligations_proven": False,
    }
    baseline.update(facts)
    assert derive_verdict(**baseline) == expected
```

Add tests rejecting claimed `PASS`, `ACCEPTED`, or `WAIVED`; READY with a waiver; READY with a missing required test; and automatic population of `human_acceptance`.

- [ ] **Step 2: Run the focused test and confirm RED**

Run: `python3 -m pytest tests/test_verdict.py -q`

Expected: module import fails.

- [ ] **Step 3: Implement verdict precedence and waiver validation**

Use only:

```python
VERDICTS = frozenset({
    "FAIL", "INCONCLUSIVE", "BLOCKED_INFRA", "ENV_INVALID",
    "ABORTED", "READY_FOR_HUMAN_ACCEPTANCE",
})
```

`derive_verdict()` uses the precedence encoded in the test table. `validate_verdict()` recomputes facts from validated tests/claims/environment/traces rather than trusting booleans from the Candidate. Waivers require human author, scope, reason, policy version, and timezone-aware expiry, remain separate from verdict, and make READY impossible. `human_acceptance` is optional input authored later by a human and never synthesized by this package.

- [ ] **Step 4: Run tests and commit**

Run: `python3 -m pytest tests/test_verdict.py -q`

Expected: all verdict tests pass.

Commit:

```bash
git add gawain_verification/verdict.py schemas/evidence-bundle.v1.schema.json tests/test_verdict.py
git commit -m "feat(verification): derive fail-closed acceptance verdicts"
```

### Task 7: Bundle orchestration, CLI, and sealed example

**Files:**
- Create: `gawain_verification/bundle.py`
- Create: `gawain_verification/cli.py`
- Create: `gawain_verification/__main__.py`
- Rewrite: `tests/test_bundle_validator.py`
- Create: `tests/test_cli.py`
- Create: `examples/verification-core/evidence-bundle.json`
- Create: `examples/verification-core/traces/application.jsonl`
- Create: `examples/verification-core/artifacts/tauri-interaction.json`
- Create: `examples/verification-core/artifacts/device-state.json`
- Modify: `README.md`

- [ ] **Step 1: Write orchestration tests before implementation**

`validate_bundle(bundle, root, now=...)` must be pure and aggregate issues from schema, identity, artifacts, tests, trace, secrets, and verdict in stable `(code, location, message)` order. Write tests proving a valid fixture returns `[]`, input is not mutated, one defect from each subsystem is returned together, and a trace file is validated only after its artifact digest passes.

- [ ] **Step 2: Write CLI exit-code tests**

```python
def test_cli_exit_codes(valid_bundle_path, invalid_bundle_path, tmp_path):
    valid = run_cli("validate", valid_bundle_path)
    invalid = run_cli("validate", invalid_bundle_path)
    missing = run_cli("validate", tmp_path / "missing.json")
    assert (valid.returncode, valid.stdout.strip()) == (0, "VALID READY_FOR_HUMAN_ACCEPTANCE")
    assert invalid.returncode == 1 and "INVALID" in invalid.stderr
    assert missing.returncode == 2 and "INPUT_ERROR" in missing.stderr
```

- [ ] **Step 3: Run focused tests and confirm RED**

Run: `python3 -m pytest tests/test_bundle_validator.py tests/test_cli.py -q`

Expected: bundle and CLI modules are missing.

- [ ] **Step 4: Implement pure orchestration and CLI**

The public CLI is:

```text
python3 -m gawain_verification validate <bundle/evidence-bundle.json>
```

Exit 0 prints `VALID <verdict>`. Validation failures print `INVALID` plus stable `<code>: <location>: <message>` lines to stderr and exit 1. File, UTF-8, or JSON input errors print `INPUT_ERROR` and exit 2. The command never writes to the bundle directory.

- [ ] **Step 5: Generate a sealed, internally consistent example**

Create the example files, compute every artifact byte count and SHA-256 from actual bytes, compute Contract/Candidate/Permit/bundle IDs with the package, and set all six required Pilot test cases to their correct positive or expected-reject status. Do not hand-type digests.

- [ ] **Step 6: Document the product boundary**

Update README with install, validate, exit-code, and example commands. State explicitly that this P0 core validates already-collected evidence; the Pilot collector/executor is a separate plan, and legacy dispatch is not the product direction.

- [ ] **Step 7: Run tests and commit**

Run:

```bash
python3 -m pytest tests/test_bundle_validator.py tests/test_cli.py -q
python3 -m gawain_verification validate examples/verification-core/evidence-bundle.json
```

Expected: tests pass and example prints `VALID READY_FOR_HUMAN_ACCEPTANCE`.

Commit:

```bash
git add gawain_verification examples README.md tests pyproject.toml
git commit -m "feat(verification): expose sealed bundle validator CLI"
```

### Task 8: Full verification and audit status correction

**Files:**
- Modify: `docs/audits/2026-08-24-verifier-test-trace-audit.md`
- Modify: `.gitignore`

- [ ] **Step 1: Add only generated-cache ignore rules**

Append:

```gitignore
__pycache__/
.pytest_cache/
*.py[cod]
.coverage
```

Do not ignore evidence bundles, schemas, examples, or `workflow/handoffs/` globally.

- [ ] **Step 2: Run the complete verification suite**

Run:

```bash
python3 -m pytest -q
python3 -m compileall -q gawain_verification
python3 -m gawain_verification validate examples/verification-core/evidence-bundle.json
git diff --check
```

Expected: all tests pass; compileall and diff check exit zero; the example is VALID.

- [ ] **Step 3: Run explicit negative CLI smoke tests**

Copy the example bundle to a temporary directory, alter one installed digest, and verify exit 1 with `installed_digest_mismatch`. Alter one trace parent and verify exit 1 with `missing_parent_span`. Keep these files under the temporary directory, not the repository.

- [ ] **Step 4: Update the audit without overstating delivery**

Change the audit status from “first P0 remediation batch in progress” to “verification-core P0 implemented” only after all commands pass. Explicitly state that remote collection, deployment, fault injection, Tauri interaction, and real-device execution remain unimplemented until the Pilot integration plan finishes.

- [ ] **Step 5: Review the final diff and commit**

Run: `git status --short && git diff --stat && git diff --check`

Confirm no `workflow/handoffs/`, unrelated audit draft, cache, credential, or real-device artifact is staged.

Commit:

```bash
git add .gitignore docs/audits/2026-08-24-verifier-test-trace-audit.md
git commit -m "docs: record verification core P0 implementation status"
```

## Plan self-review

- Spec coverage: immutable Contract/Candidate/Permit, deployed identity, `full_access`, safe artifacts, exact test layers/counts, positive/negative semantics, W3C causal traces, secret blocking, closed verdicts, waiver separation, and human acceptance separation all map to tasks.
- Scope boundary: this plan deliberately stops at validating collected evidence. It does not claim deployment, Tauri driving, real-device collection, rollback, or fault injection; those are owned by the separate Service Manager Pilot plan.
- Type consistency: `contract_id`, `candidate_id`, `permit_id`, `run_id`, `test_case_id`, `attempt_id`, `operation_id`, `trace_id`, and artifact IDs retain one spelling throughout.
- No overall `PASS`, `ACCEPTED`, or `WAIVED` verdict remains; the only success terminal is `READY_FOR_HUMAN_ACCEPTANCE`.
- Existing untracked handoffs and unrelated repository changes are preserved.
