from datetime import UTC, datetime

import pytest

from gawain_verification.canonical import content_id
from gawain_verification.identity import validate_identity_gate
from gawain_verification.issues import issue
from gawain_verification.schema import validate_schema


NOW = datetime(2026, 8, 25, 3, 0, tzinfo=UTC)


def validate(contract, candidate, permit, environment, **kwargs):
    return validate_identity_gate(
        contract, candidate, permit, environment, now=NOW, **kwargs
    )


def codes(contract, candidate, permit, environment, **kwargs):
    return [
        problem.code
        for problem in validate(contract, candidate, permit, environment, **kwargs)
    ]


def refresh(kind, value):
    value[f"{kind}_id"] = content_id(kind, value)


def test_valid_identity_gate_has_no_issues(
    valid_contract, valid_candidate, valid_permit, valid_environment
):
    assert validate(valid_contract, valid_candidate, valid_permit, valid_environment) == []


def test_full_access_does_not_replace_permit(
    valid_contract, valid_candidate, valid_environment
):
    assert "missing_permit" in codes(
        valid_contract, valid_candidate, None, valid_environment
    )


def test_full_access_does_not_allow_wrong_device(
    valid_contract, valid_candidate, valid_permit, valid_environment
):
    valid_permit["full_access"] = True
    valid_environment["device_id"] = "SP000056"

    assert "device_identity_mismatch" in codes(
        valid_contract, valid_candidate, valid_permit, valid_environment
    )


def test_expired_permit_is_rejected(
    valid_contract, valid_candidate, valid_permit, valid_environment
):
    valid_permit["not_after"] = "2026-08-25T02:59:59Z"
    refresh("permit", valid_permit)

    assert "permit_expired" in codes(
        valid_contract, valid_candidate, valid_permit, valid_environment
    )


def test_installed_digest_must_match_candidate(
    valid_contract, valid_candidate, valid_permit, valid_environment
):
    valid_environment["installed_components"][0]["sha256"] = "sha256:" + "0" * 64

    assert "installed_digest_mismatch" in codes(
        valid_contract, valid_candidate, valid_permit, valid_environment
    )


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda contract: contract.update(contract_id="sha256:" + "0" * 64), "contract_id_mismatch"),
        (lambda candidate: candidate.update(candidate_id="sha256:" + "0" * 64), "candidate_id_mismatch"),
        (lambda permit: permit.update(permit_id="sha256:" + "0" * 64), "permit_id_mismatch"),
    ],
)
def test_content_id_gates_are_independent(
    valid_contract,
    valid_candidate,
    valid_permit,
    valid_environment,
    mutation,
    expected,
):
    target = {
        "contract_id_mismatch": valid_contract,
        "candidate_id_mismatch": valid_candidate,
        "permit_id_mismatch": valid_permit,
    }[expected]
    mutation(target)

    assert expected in codes(
        valid_contract, valid_candidate, valid_permit, valid_environment
    )


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("issuer_kind", "service", "invalid_permit_issuer_kind"),
        ("issuer", "", "invalid_permit_issuer"),
    ],
)
def test_permit_requires_human_issuer(
    valid_contract,
    valid_candidate,
    valid_permit,
    valid_environment,
    field,
    value,
    expected,
):
    valid_permit[field] = value
    refresh("permit", valid_permit)

    assert expected in codes(
        valid_contract, valid_candidate, valid_permit, valid_environment
    )


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("not_before", "not-a-time", "permit_invalid_time"),
        ("not_after", "2026-08-26T00:00:00", "permit_invalid_time"),
        ("not_before", "2026-08-25T03:00:01Z", "permit_not_yet_valid"),
    ],
)
def test_permit_time_gate(
    valid_contract,
    valid_candidate,
    valid_permit,
    valid_environment,
    field,
    value,
    expected,
):
    valid_permit[field] = value
    refresh("permit", valid_permit)

    assert expected in codes(
        valid_contract, valid_candidate, valid_permit, valid_environment
    )


def test_permit_rejects_reversed_window(
    valid_contract, valid_candidate, valid_permit, valid_environment
):
    valid_permit["not_before"] = "2026-08-26T00:00:01Z"
    refresh("permit", valid_permit)

    assert "permit_invalid_window" in codes(
        valid_contract, valid_candidate, valid_permit, valid_environment
    )


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("device_ids", "device_not_authorized"),
        ("service_ids", "service_not_authorized"),
        ("actions", "action_not_authorized"),
    ],
)
def test_permit_must_authorize_exact_contract_target(
    valid_contract,
    valid_candidate,
    valid_permit,
    valid_environment,
    field,
    expected,
):
    valid_permit[field] = ["other"]
    refresh("permit", valid_permit)

    assert expected in codes(
        valid_contract, valid_candidate, valid_permit, valid_environment
    )


@pytest.mark.parametrize("field", ["device_ids", "service_ids", "actions"])
@pytest.mark.parametrize("value", [[], "SP000065", [""], [7]])
def test_permit_authorization_fields_are_arrays_of_non_empty_strings(
    valid_contract,
    valid_candidate,
    valid_permit,
    valid_environment,
    field,
    value,
):
    valid_permit[field] = value
    refresh("permit", valid_permit)

    assert f"invalid_permit_{field}" in codes(
        valid_contract, valid_candidate, valid_permit, valid_environment
    )


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda environment: environment.update(host_identity=""), "missing_host_identity"),
        (
            lambda environment: environment.update(gateway_endpoint="192.168.110.65:1"),
            "gateway_endpoint_mismatch",
        ),
    ],
)
def test_environment_identity_and_endpoint_are_required(
    valid_contract,
    valid_candidate,
    valid_permit,
    valid_environment,
    mutation,
    expected,
):
    mutation(valid_environment)

    assert expected in codes(
        valid_contract, valid_candidate, valid_permit, valid_environment
    )


def test_peer_address_alone_is_not_host_identity(
    valid_contract, valid_candidate, valid_permit, valid_environment
):
    del valid_environment["host_identity"]
    valid_environment["peer_addr"] = "192.168.110.65"

    assert "missing_host_identity" in codes(
        valid_contract, valid_candidate, valid_permit, valid_environment
    )


@pytest.mark.parametrize(
    ("installed", "expected"),
    [
        (None, "invalid_installed_components"),
        ([None], "malformed_installed_component"),
        ([{"name": "frontend", "sha256": "sha256:" + "f" * 64}] * 2, "duplicate_installed_component"),
        ([{"name": "extra", "sha256": "sha256:" + "0" * 64}], "extra_installed_component"),
    ],
)
def test_malformed_installed_component_sets_fail_closed(
    valid_contract,
    valid_candidate,
    valid_permit,
    valid_environment,
    installed,
    expected,
):
    valid_environment["installed_components"] = installed

    assert expected in codes(
        valid_contract, valid_candidate, valid_permit, valid_environment
    )


def test_missing_installed_candidate_component_is_rejected(
    valid_contract, valid_candidate, valid_permit, valid_environment
):
    valid_environment["installed_components"].pop()

    assert "missing_installed_component" in codes(
        valid_contract, valid_candidate, valid_permit, valid_environment
    )


def test_full_access_only_skips_optional_software_policy_issues(
    valid_contract, valid_candidate, valid_permit, valid_environment
):
    policy_problem = issue("software_policy_denied", "software", "denied")
    valid_permit["full_access"] = False
    refresh("permit", valid_permit)
    assert policy_problem in validate(
        valid_contract,
        valid_candidate,
        valid_permit,
        valid_environment,
        software_gate_violations=(policy_problem,),
    )

    valid_permit["full_access"] = True
    refresh("permit", valid_permit)
    assert policy_problem not in validate(
        valid_contract,
        valid_candidate,
        valid_permit,
        valid_environment,
        software_gate_violations=(policy_problem,),
    )


def test_full_access_must_be_boolean(
    valid_contract, valid_candidate, valid_permit, valid_environment
):
    valid_permit["full_access"] = 1
    refresh("permit", valid_permit)

    assert "invalid_full_access" in codes(
        valid_contract, valid_candidate, valid_permit, valid_environment
    )


@pytest.mark.parametrize("bad_value", [None, [], "bad"])
def test_malformed_trust_boundary_objects_do_not_raise(
    valid_contract, valid_candidate, valid_permit, valid_environment, bad_value
):
    assert validate(bad_value, valid_candidate, valid_permit, valid_environment)
    assert validate(valid_contract, bad_value, valid_permit, valid_environment)
    assert validate(valid_contract, valid_candidate, bad_value, valid_environment)
    assert validate(valid_contract, valid_candidate, valid_permit, bad_value)


def test_identity_gate_does_not_mutate_inputs(
    valid_contract, valid_candidate, valid_permit, valid_environment, cloned
):
    values = (valid_contract, valid_candidate, valid_permit, valid_environment)
    before = cloned(values)

    validate(*values)

    assert values == before


def test_contract_schema_is_closed_and_action_is_pilot_neutral(valid_contract, cloned):
    contract = cloned(valid_contract)
    contract["action"] = "AnyFutureHarnessAction"
    refresh("contract", contract)
    assert validate_schema(contract, "verification-contract.v1.schema.json") == []

    contract["unexpected"] = True
    assert [p.code for p in validate_schema(contract, "verification-contract.v1.schema.json")] == [
        "schema_error"
    ]


def test_contract_schema_requires_all_frozen_fields(valid_contract, cloned):
    contract = cloned(valid_contract)
    del contract["connection_hint"]

    issues = validate_schema(contract, "verification-contract.v1.schema.json")

    assert issues and issues[0].location == "$"


def test_schema_issues_are_sorted_by_json_path(valid_contract, cloned):
    contract = cloned(valid_contract)
    contract["unit"] = ""
    contract["action"] = ""

    issues = validate_schema(contract, "verification-contract.v1.schema.json")

    assert [problem.location for problem in issues] == ["$.action", "$.unit"]


def test_evidence_bundle_schema_is_closed_at_top_level(valid_contract):
    bundle = {
        "schema_version": "gawain.evidence-bundle.v1",
        "run_id": "run-example_1",
        "contract": valid_contract,
        "candidate": {},
        "permit": {},
        "environment": {},
        "artifacts": [],
        "tests": [],
        "claims": [],
        "traces": [],
        "verdict": {},
        "unexpected": True,
    }

    assert [
        problem.code
        for problem in validate_schema(bundle, "evidence-bundle.v1.schema.json")
    ] == ["schema_error"]
