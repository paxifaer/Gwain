from copy import deepcopy
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
def bundle_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def cloned():
    return deepcopy
