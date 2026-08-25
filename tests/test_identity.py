from gawain_verification.canonical import canonical_json, content_id
from gawain_verification.identity import validate_candidate


def test_canonical_json_sorts_object_keys():
    assert canonical_json({"b": 2, "a": 1}) == b'{"a":1,"b":2}'


def test_contract_content_id_ignores_existing_identity(valid_contract, cloned):
    contract = cloned(valid_contract)
    expected = contract.pop("contract_id")

    assert content_id("contract", valid_contract) == expected


def test_candidate_component_order_does_not_change_identity(valid_candidate, cloned):
    reordered = cloned(valid_candidate)
    reordered["components"].reverse()

    assert content_id("candidate", reordered) == valid_candidate["candidate_id"]


def test_duplicate_candidate_component_name_is_rejected(valid_candidate, cloned):
    candidate = cloned(valid_candidate)
    candidate["components"][1]["name"] = candidate["components"][0]["name"]
    candidate["candidate_id"] = content_id("candidate", candidate)

    issues = validate_candidate(candidate)

    assert [problem.code for problem in issues] == ["duplicate_component"]


def test_candidate_requires_components(valid_candidate, cloned):
    candidate = cloned(valid_candidate)
    candidate["components"] = []
    candidate["candidate_id"] = content_id("candidate", candidate)

    assert [problem.code for problem in validate_candidate(candidate)] == [
        "missing_components"
    ]


def test_candidate_rejects_invalid_component_hashes(valid_candidate, cloned):
    candidate = cloned(valid_candidate)
    component = candidate["components"][0]
    for field in ("base_commit", "head_commit", "tree_hash", "diff_hash"):
        component[field] = "INVALID"
    for field in ("build_recipe_id", "build_artifact_sha256"):
        component[field] = "sha256:INVALID"
    candidate["candidate_id"] = content_id("candidate", candidate)

    assert [problem.code for problem in validate_candidate(candidate)] == [
        "invalid_base_commit",
        "invalid_head_commit",
        "invalid_tree_hash",
        "invalid_diff_hash",
        "invalid_build_recipe_id",
        "invalid_build_artifact_sha256",
    ]


def test_candidate_identity_must_match_content(valid_candidate, cloned):
    candidate = cloned(valid_candidate)
    candidate["candidate_id"] = "sha256:" + "0" * 64

    assert [problem.code for problem in validate_candidate(candidate)] == [
        "candidate_id_mismatch"
    ]


def test_candidate_validation_does_not_mutate_input(valid_candidate, cloned):
    candidate = cloned(valid_candidate)
    before = cloned(candidate)

    validate_candidate(candidate)

    assert candidate == before
