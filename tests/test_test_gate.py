from copy import deepcopy

import pytest

from gawain_verification.schema import validate_schema
from gawain_verification.test_gate import validate_tests


def codes(bundle):
    return [problem.code for problem in validate_tests(bundle)]


def test_valid_test_bundle_has_no_issues(valid_test_bundle):
    assert validate_tests(valid_test_bundle) == []


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("executed_test_count", 0, "zero_tests_executed"),
        ("executed_test_count", 2, "test_count_mismatch"),
        ("ignored_test_count", 1, "required_test_ignored"),
        ("failed_test_count", 1, "test_failures_present"),
        ("exit_code", 1, "test_command_failed"),
    ],
)
def test_false_green_is_rejected(valid_test_bundle, field, value, expected):
    valid_test_bundle["tests"][0][field] = value

    assert expected in codes(valid_test_bundle)


@pytest.mark.parametrize(
    ("expected_outcome", "status", "expected_issue"),
    [
        ("PASS", "PASS", None),
        ("REJECT", "EXPECTED_REJECT", None),
        ("REJECT", "PASS", "negative_test_not_rejected"),
        ("PASS", "EXPECTED_REJECT", "positive_test_not_passed"),
    ],
)
def test_expected_outcome_must_match_status(
    valid_test_bundle, expected_outcome, status, expected_issue
):
    record = valid_test_bundle["tests"][0]
    record["expected_outcome"] = expected_outcome
    record["status"] = status

    found = codes(valid_test_bundle)
    if expected_issue is None:
        assert found == []
    else:
        assert expected_issue in found


def test_count_sum_must_equal_executed(valid_test_bundle):
    valid_test_bundle["tests"][0]["passed_test_count"] = 0

    assert "test_count_sum_mismatch" in codes(valid_test_bundle)


def test_expected_count_must_be_positive(valid_test_bundle):
    record = valid_test_bundle["tests"][0]
    record["expected_test_count"] = 0
    record["executed_test_count"] = 0
    record["passed_test_count"] = 0

    assert "invalid_expected_test_count" in codes(valid_test_bundle)


@pytest.mark.parametrize(
    "field",
    [
        "expected_test_count",
        "executed_test_count",
        "passed_test_count",
        "failed_test_count",
        "ignored_test_count",
    ],
)
@pytest.mark.parametrize("value", [-1, 1.5, "1", True, None])
def test_counts_must_be_nonnegative_integers(valid_test_bundle, field, value):
    valid_test_bundle["tests"][0][field] = value

    assert f"invalid_{field}" in codes(valid_test_bundle)


@pytest.mark.parametrize("value", [1.5, "0", True, None])
def test_exit_code_must_be_an_integer(valid_test_bundle, value):
    valid_test_bundle["tests"][0]["exit_code"] = value

    assert "invalid_exit_code" in codes(valid_test_bundle)


@pytest.mark.parametrize(
    "level",
    [
        "unit",
        "component",
        "integration",
        "browser",
        "tauri",
        "deployment",
        "real_device_e2e",
    ],
)
def test_exact_layer_enum_is_accepted(valid_test_bundle, level):
    record = valid_test_bundle["tests"][0]
    record["required_level"] = level
    record["observed_level"] = level
    if level == "browser":
        valid_test_bundle["artifacts"][0]["kind"] = "browser-interaction"
        record["evidence"] = [valid_test_bundle["artifacts"][0]["artifact_id"]]
    elif level == "deployment":
        valid_test_bundle["artifacts"][0]["kind"] = "deployment-record"
        valid_test_bundle["artifacts"][1]["kind"] = "installed-digest"
    elif level == "real_device_e2e":
        valid_test_bundle["artifacts"][0]["kind"] = "device-state"
    elif level not in {"tauri"}:
        record["evidence"] = [valid_test_bundle["artifacts"][0]["artifact_id"]]

    assert validate_tests(valid_test_bundle) == []


@pytest.mark.parametrize("field", ["required_level", "observed_level"])
@pytest.mark.parametrize("value", ["", "TAURI", "real-device-e2e", 7, None, [], {}])
def test_unknown_layers_are_rejected(valid_test_bundle, field, value):
    valid_test_bundle["tests"][0][field] = value

    assert f"invalid_{field}" in codes(valid_test_bundle)


def test_required_and_observed_levels_must_match(valid_test_bundle):
    valid_test_bundle["tests"][0]["observed_level"] = "browser"

    assert "test_level_mismatch" in codes(valid_test_bundle)


def test_browser_cannot_satisfy_tauri(valid_test_bundle):
    valid_test_bundle["tests"][0]["observed_level"] = "browser"
    valid_test_bundle["artifacts"][0]["kind"] = "browser-interaction"

    found = codes(valid_test_bundle)
    assert "test_level_mismatch" in found
    assert "missing_required_evidence_kind" in found


@pytest.mark.parametrize(
    ("level", "kinds"),
    [
        ("browser", ["browser-interaction"]),
        ("tauri", ["tauri-interaction", "application-trace"]),
        ("deployment", ["deployment-record", "installed-digest"]),
        ("real_device_e2e", ["device-state", "application-trace"]),
    ],
)
def test_each_dynamic_layer_requires_every_evidence_kind(
    valid_test_bundle, level, kinds
):
    record = valid_test_bundle["tests"][0]
    record["required_level"] = level
    record["observed_level"] = level
    for index, kind in enumerate(kinds):
        valid_test_bundle["artifacts"][index]["kind"] = kind
    record["evidence"] = [
        valid_test_bundle["artifacts"][index]["artifact_id"]
        for index in range(len(kinds))
    ]

    assert validate_tests(valid_test_bundle) == []

    for missing_kind in kinds:
        mutated = deepcopy(valid_test_bundle)
        artifact = next(
            item for item in mutated["artifacts"] if item["kind"] == missing_kind
        )
        mutated["tests"][0]["evidence"].remove(artifact["artifact_id"])
        matching = [
            problem
            for problem in validate_tests(mutated)
            if problem.code == "missing_required_evidence_kind"
        ]
        assert any(missing_kind in problem.message for problem in matching)


def test_evidence_ids_are_resolved_to_manifest_kinds(valid_test_bundle):
    record = valid_test_bundle["tests"][0]
    record["evidence"] = ["tauri-interaction", "application-trace"]

    assert "missing_required_evidence_kind" in codes(valid_test_bundle)


def test_unknown_evidence_id_does_not_satisfy_kind(valid_test_bundle):
    valid_test_bundle["tests"][0]["evidence"] = [
        "artifact-tauri-interaction",
        "unknown-application-trace",
    ]

    assert "missing_required_evidence_kind" in codes(valid_test_bundle)


@pytest.mark.parametrize("field", ["id", "command", "cwd", "environment_fingerprint"])
@pytest.mark.parametrize("value", [None, "", 7, [], True])
def test_required_text_fields_are_nonempty_strings(
    valid_test_bundle, field, value
):
    valid_test_bundle["tests"][0][field] = value

    assert f"invalid_{field}" in codes(valid_test_bundle)


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("expected_outcome", "pass", "invalid_expected_outcome"),
        ("expected_outcome", None, "invalid_expected_outcome"),
        ("expected_outcome", [], "invalid_expected_outcome"),
        ("status", "REJECT", "invalid_status"),
        ("status", None, "invalid_status"),
        ("status", {}, "invalid_status"),
    ],
)
def test_outcome_and_status_enums_are_closed(
    valid_test_bundle, field, value, expected
):
    valid_test_bundle["tests"][0][field] = value

    assert expected in codes(valid_test_bundle)


@pytest.mark.parametrize("value", [None, {}, [], "asserted", {"assertion": True}])
def test_oracle_requires_explicit_structured_assertion_and_observation(
    valid_test_bundle, value
):
    valid_test_bundle["tests"][0]["oracle"] = value

    expected = [] if value == {"assertion": True} else ["invalid_oracle"]
    assert ("invalid_oracle" in codes(valid_test_bundle)) == bool(expected)


@pytest.mark.parametrize("value", [None, [], "artifact", [""], [7], [True]])
def test_evidence_requires_nonempty_string_id_list(valid_test_bundle, value):
    valid_test_bundle["tests"][0]["evidence"] = value

    assert "invalid_test_evidence" in codes(valid_test_bundle)


def test_unexpected_test_fields_are_rejected(valid_test_bundle):
    valid_test_bundle["tests"][0]["narrative_result"] = "looks good"

    assert "unexpected_test_field" in codes(valid_test_bundle)


@pytest.mark.parametrize("required", [None, [], "P-01", [""], [7], [True]])
def test_required_test_cases_must_be_nonempty_string_list(
    valid_test_bundle, required
):
    valid_test_bundle["contract"]["required_test_cases"] = required

    assert "invalid_required_test_cases" in codes(valid_test_bundle)


def test_required_test_case_ids_must_be_unique(valid_test_bundle):
    valid_test_bundle["contract"]["required_test_cases"] = ["P-01", "P-01"]

    assert "duplicate_required_test_case" in codes(valid_test_bundle)


def test_missing_required_test_is_rejected(valid_test_bundle):
    valid_test_bundle["contract"]["required_test_cases"].append("N-01")

    assert "missing_required_test" in codes(valid_test_bundle)


def test_duplicate_test_record_is_rejected(valid_test_bundle):
    valid_test_bundle["tests"].append(deepcopy(valid_test_bundle["tests"][0]))

    assert "duplicate_test_record" in codes(valid_test_bundle)


def test_unexpected_test_record_is_rejected(valid_test_bundle):
    record = deepcopy(valid_test_bundle["tests"][0])
    record["id"] = "UNRELATED-01"
    valid_test_bundle["tests"].append(record)

    assert "unexpected_test_record" in codes(valid_test_bundle)


def test_duplicate_unexpected_test_id_is_also_rejected_as_duplicate(
    valid_test_bundle,
):
    record = deepcopy(valid_test_bundle["tests"][0])
    record["id"] = "UNRELATED-01"
    valid_test_bundle["tests"].extend([record, deepcopy(record)])

    found = codes(valid_test_bundle)
    assert "duplicate_test_record" in found
    assert "unexpected_test_record" in found


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda bundle: None, "invalid_bundle"),
        (lambda bundle: bundle.update(contract=None), "invalid_contract"),
        (lambda bundle: bundle.update(tests=None), "invalid_tests"),
        (lambda bundle: bundle["tests"].__setitem__(0, None), "malformed_test_record"),
        (lambda bundle: bundle.update(artifacts=None), "invalid_artifacts"),
    ],
)
def test_malformed_containers_fail_closed_without_raising(
    valid_test_bundle, mutation, expected
):
    if expected == "invalid_bundle":
        value = None
    else:
        mutation(valid_test_bundle)
        value = valid_test_bundle

    assert expected in codes(value)


def test_validation_is_deterministic_and_does_not_mutate(valid_test_bundle):
    valid_test_bundle["tests"][0]["executed_test_count"] = 0
    valid_test_bundle["tests"][0]["status"] = "EXPECTED_REJECT"
    before = deepcopy(valid_test_bundle)

    first = validate_tests(valid_test_bundle)
    second = validate_tests(valid_test_bundle)

    assert first == second == sorted(first)
    assert valid_test_bundle == before


def test_evidence_bundle_schema_closes_test_and_artifact_records(
    valid_test_bundle, valid_candidate, valid_permit
):
    bundle = {
        "schema_version": "gawain.evidence-bundle.v1",
        "run_id": "run-test-schema",
        "candidate": valid_candidate,
        "permit": valid_permit,
        "environment": {},
        "claims": [],
        "traces": [],
        "verdict": {},
        **valid_test_bundle,
    }
    assert validate_schema(bundle, "evidence-bundle.v1.schema.json") == []

    bundle["tests"][0]["unexpected"] = True
    bundle["artifacts"][0]["unexpected"] = True
    locations = {
        problem.location
        for problem in validate_schema(bundle, "evidence-bundle.v1.schema.json")
    }
    assert {"$.tests[0]", "$.artifacts[0]"}.issubset(locations)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("required_level", "TAURI"),
        ("observed_level", "TAURI"),
        ("expected_outcome", "pass"),
        ("status", "REJECT"),
        ("command", ""),
        ("cwd", ""),
        ("environment_fingerprint", ""),
        ("expected_test_count", 0),
        ("executed_test_count", -1),
        ("passed_test_count", -1),
        ("failed_test_count", -1),
        ("ignored_test_count", -1),
        ("exit_code", True),
        ("oracle", {}),
        ("evidence", []),
        ("evidence", ["artifact", "artifact"]),
    ],
)
def test_evidence_bundle_schema_rejects_invalid_test_fields(
    valid_test_bundle, valid_candidate, valid_permit, field, value
):
    bundle = {
        "schema_version": "gawain.evidence-bundle.v1",
        "run_id": "run-test-schema",
        "candidate": valid_candidate,
        "permit": valid_permit,
        "environment": {},
        "claims": [],
        "traces": [],
        "verdict": {},
        **valid_test_bundle,
    }
    bundle["tests"][0][field] = value

    assert f"$.tests[0].{field}" in {
        problem.location
        for problem in validate_schema(bundle, "evidence-bundle.v1.schema.json")
    }


def test_evidence_bundle_schema_requires_artifact_kind(
    valid_test_bundle, valid_candidate, valid_permit
):
    bundle = {
        "schema_version": "gawain.evidence-bundle.v1",
        "run_id": "run-test-schema",
        "candidate": valid_candidate,
        "permit": valid_permit,
        "environment": {},
        "claims": [],
        "traces": [],
        "verdict": {},
        **valid_test_bundle,
    }
    del bundle["artifacts"][0]["kind"]

    assert "$.artifacts[0]" in {
        problem.location
        for problem in validate_schema(bundle, "evidence-bundle.v1.schema.json")
    }
