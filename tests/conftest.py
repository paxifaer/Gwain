from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gawain_verification.canonical import content_id


@pytest.fixture
def valid_contract() -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": "gawain.verification-contract.v1",
        "contract_kind": "service-manager-vertical-e2e",
        "device_id": "SP000065",
        "connection_hint": "192.168.110.65",
        "gateway_endpoint": "192.168.110.65:50053",
        "host_identity": "sha256:" + "7" * 64,
        "service_id": "gawain-canary",
        "unit": "gawain-canary.service",
        "systemd_scope": "user",
        "action": "Restart",
        "success_terminal": "READY_FOR_HUMAN_ACCEPTANCE",
        "required_claims": [
            "restart-path-correlated",
            "negative-cases-rejected",
            "deployed-digests-bound",
            "causal-trace-complete",
        ],
        "required_test_cases": [
            {
                "id": "P-01",
                "required_level": "real_device_e2e",
                "expected_outcome": "PASS",
                "expected_test_count": 1,
                "oracle": {
                    "assertion": "restart reaches the ready state",
                    "operator": "equals",
                    "expected": "READY",
                },
            },
            *[
                {
                    "id": case_id,
                    "required_level": "real_device_e2e",
                    "expected_outcome": "REJECT",
                    "expected_test_count": 1,
                    "oracle": {
                        "assertion": assertion,
                        "operator": "equals",
                        "expected": "REJECTED",
                    },
                }
                for case_id, assertion in (
                    ("N-01", "an unknown service is rejected"),
                    ("N-02", "an unauthorized action is rejected"),
                    ("N-03", "an invalid device target is rejected"),
                    ("N-04", "a stale request is rejected"),
                )
            ],
            {
                "id": "N-05",
                "required_level": "deployment",
                "expected_outcome": "REJECT",
                "expected_test_count": 1,
                "oracle": {
                    "assertion": "a mismatched deployment digest is rejected",
                    "operator": "equals",
                    "expected": "REJECTED",
                },
            },
        ],
    }
    body["contract_id"] = content_id("contract", body)
    return body


@pytest.fixture
def valid_candidate() -> dict[str, object]:
    candidate: dict[str, object] = {
        "schema_version": "gawain.candidate-set.v1",
        "components": [
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
    }
    candidate["candidate_id"] = content_id("candidate", candidate)
    return candidate


@pytest.fixture
def valid_permit() -> dict[str, object]:
    permit: dict[str, object] = {
        "schema_version": "gawain.execution-permit.v1",
        "issuer_kind": "human",
        "issuer": "operator@example.test",
        "device_ids": ["SP000065"],
        "service_ids": ["gawain-canary"],
        "actions": ["Restart", "DeployFixture", "InjectFault", "Rollback"],
        "not_before": "2026-08-25T00:00:00Z",
        "not_after": "2026-08-26T00:00:00Z",
        "full_access": True,
    }
    permit["permit_id"] = content_id("permit", permit)
    return permit


@pytest.fixture
def valid_environment(valid_candidate) -> dict[str, object]:
    return {
        "device_id": "SP000065",
        "host_identity": "sha256:" + "7" * 64,
        "gateway_endpoint": "192.168.110.65:50053",
        "installed_components": [
            {
                "name": component["name"],
                "sha256": component["build_artifact_sha256"],
            }
            for component in valid_candidate["components"]
        ],
    }


@pytest.fixture
def bundle_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def cloned():
    return deepcopy


@pytest.fixture
def expected_trace_context() -> dict[str, str]:
    trace_id = "0123456789abcdef0123456789abcdef"
    return {
        "run_id": "run-pilot-001",
        "contract_id": "sha256:" + "a" * 64,
        "candidate_id": "sha256:" + "b" * 64,
        "test_case_id": "P-01",
        "attempt_id": "attempt-1",
        "operation_id": trace_id,
        "trace_id": trace_id,
    }


@pytest.fixture
def valid_trace_file(tmp_path: Path, expected_trace_context) -> Path:
    root = "0123456789abcdef"
    child = "fedcba9876543210"
    events = []
    for sequence, kind, span, parent in (
        (1, "SPAN_START", root, None),
        (2, "SPAN_START", child, root),
        (3, "SPAN_END", child, root),
        (4, "SPAN_END", root, None),
    ):
        events.append(
            {
                "schema_version": "gawain.trace-event.v1",
                "event_id": f"evt-{sequence:04d}",
                "ts": f"2026-08-25T03:00:0{sequence}.000Z",
                "level": "INFO",
                "event_kind": kind,
                **expected_trace_context,
                "span_id": span,
                "parent_span_id": parent,
                "service": "frontend.renderer",
                "instance_id": "skyline-test-1",
                "sequence": sequence,
                "attributes": {"status": "OK"} if kind == "SPAN_END" else {},
            }
        )
    path = tmp_path / "application.jsonl"
    path.write_text(
        "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
    )
    return path


@pytest.fixture
def valid_artifact_bundle(tmp_path: Path) -> dict[str, object]:
    artifact_id = "artifact-evidence-json"
    artifact_path = tmp_path / "artifacts" / "evidence.json"
    artifact_path.parent.mkdir()
    content = b'{"result":"verified"}\n'
    artifact_path.write_bytes(content)

    evidence = {"evidence": [artifact_id]}
    test_evidence = {
        "id": "P-01",
        "required_level": "unit",
        "observed_level": "unit",
        "expected_outcome": "PASS",
        "status": "PASS",
        "command": "pytest tests/test_unit.py -q",
        "cwd": "/workspace",
        "environment_fingerprint": "sha256:" + "0" * 64,
        "expected_test_count": 1,
        "executed_test_count": 1,
        "passed_test_count": 1,
        "failed_test_count": 0,
        "ignored_test_count": 0,
        "exit_code": 0,
        "oracle": {
            "assertion": "unit behavior is correct",
            "operator": "equals",
            "expected": True,
            "observed": True,
            "passed": True,
        },
        **evidence,
    }
    return {
        "artifacts": [
            {
                "artifact_id": artifact_id,
                "kind": "test-evidence",
                "path": "artifacts/evidence.json",
                "bytes": len(content),
                "sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
            }
        ],
        "tests": [deepcopy(test_evidence)],
        "claims": [
            {
                "id": "restart-path-correlated",
                "status": "PROVEN",
                **deepcopy(evidence),
            }
        ],
        "traces": [deepcopy(evidence)],
        "environment": deepcopy(evidence),
        "deployment": deepcopy(evidence),
    }


@pytest.fixture
def valid_test_bundle() -> dict[str, object]:
    tauri_artifact_id = "artifact-tauri-interaction"
    trace_artifact_id = "artifact-application-trace"
    return {
        "contract": {
            "required_test_cases": [
                {
                    "id": "P-01",
                    "required_level": "tauri",
                    "expected_outcome": "PASS",
                    "expected_test_count": 1,
                    "oracle": {
                        "assertion": "window is visible",
                        "operator": "equals",
                        "expected": True,
                    },
                }
            ]
        },
        "artifacts": [
            {
                "artifact_id": tauri_artifact_id,
                "kind": "tauri-interaction",
                "path": "artifacts/tauri-interaction.json",
                "bytes": 2,
                "sha256": "sha256:" + "1" * 64,
            },
            {
                "artifact_id": trace_artifact_id,
                "kind": "application-trace",
                "path": "artifacts/application-trace.jsonl",
                "bytes": 3,
                "sha256": "sha256:" + "2" * 64,
            },
        ],
        "tests": [
            {
                "id": "P-01",
                "required_level": "tauri",
                "observed_level": "tauri",
                "expected_outcome": "PASS",
                "status": "PASS",
                "command": "pytest tests/test_ui.py -q",
                "cwd": "/workspace",
                "environment_fingerprint": "sha256:" + "3" * 64,
                "expected_test_count": 1,
                "executed_test_count": 1,
                "passed_test_count": 1,
                "failed_test_count": 0,
                "ignored_test_count": 0,
                "exit_code": 0,
                "oracle": {
                    "assertion": "window is visible",
                    "operator": "equals",
                    "expected": True,
                    "observed": True,
                    "passed": True,
                },
                "evidence": [tauri_artifact_id, trace_artifact_id],
            }
        ],
    }


@pytest.fixture
def valid_verdict_bundle(valid_contract, valid_candidate, valid_permit):
    artifact_id = "artifact-verdict-evidence"
    tests = []
    for requirement in valid_contract["required_test_cases"]:
        expected_outcome = requirement["expected_outcome"]
        tests.append(
            {
                "id": requirement["id"],
                "required_level": requirement["required_level"],
                "observed_level": requirement["required_level"],
                "expected_outcome": expected_outcome,
                "status": "PASS" if expected_outcome == "PASS" else "EXPECTED_REJECT",
                "command": f"pytest -q -k {requirement['id']}",
                "cwd": "/workspace",
                "environment_fingerprint": "sha256:" + "0" * 64,
                "expected_test_count": 1,
                "executed_test_count": 1,
                "passed_test_count": 1,
                "failed_test_count": 0,
                "ignored_test_count": 0,
                "exit_code": 0,
                "oracle": {
                    **deepcopy(requirement["oracle"]),
                    "observed": requirement["oracle"]["expected"],
                    "passed": True,
                },
                "evidence": [artifact_id],
            }
        )
    return {
        "schema_version": "gawain.evidence-bundle.v1",
        "run_id": "run-verdict-001",
        "run": {"status": "COMPLETED"},
        "contract": deepcopy(valid_contract),
        "candidate": deepcopy(valid_candidate),
        "permit": deepcopy(valid_permit),
        "environment": {},
        "artifacts": [
            {
                "artifact_id": artifact_id,
                "kind": "test-evidence",
                "path": "artifacts/verdict.json",
                "bytes": 1,
                "sha256": "sha256:" + "9" * 64,
            }
        ],
        "tests": tests,
        "claims": [
            {"id": claim_id, "status": "PROVEN", "evidence": [artifact_id]}
            for claim_id in valid_contract["required_claims"]
        ],
        "traces": [],
        "verdict": {"status": "READY_FOR_HUMAN_ACCEPTANCE"},
    }
