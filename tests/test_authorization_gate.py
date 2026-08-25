from datetime import UTC, datetime
from importlib import resources
import json

import pytest
from jsonschema import Draft202012Validator

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


@pytest.mark.parametrize("schema_version", [None, 7, "WRONG"])
def test_permit_requires_exact_schema_version(
    valid_contract,
    valid_candidate,
    valid_permit,
    valid_environment,
    schema_version,
):
    if schema_version is None:
        del valid_permit["schema_version"]
    else:
        valid_permit["schema_version"] = schema_version
    refresh("permit", valid_permit)

    matching = [
        problem
        for problem in validate(
            valid_contract, valid_candidate, valid_permit, valid_environment
        )
        if problem.code == "invalid_permit_schema_version"
    ]
    assert [
        (problem.location, problem.message) for problem in matching
    ] == [
        (
            "permit.schema_version",
            "permit schema_version must be gawain.execution-permit.v1",
        )
    ]


def test_permit_schema_and_content_identity_are_independent(
    valid_contract, valid_candidate, valid_permit, valid_environment
):
    valid_permit["schema_version"] = "WRONG"

    assert {
        "invalid_permit_schema_version",
        "permit_id_mismatch",
    }.issubset(
        codes(valid_contract, valid_candidate, valid_permit, valid_environment)
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
        (
            lambda environment: environment.update(host_identity=""),
            "invalid_environment_host_identity",
        ),
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

    assert "invalid_environment_host_identity" in codes(
        valid_contract, valid_candidate, valid_permit, valid_environment
    )


@pytest.mark.parametrize(
    "host_identity",
    ["", " ", "192.168.110.65", "host-key", "sha256:" + "A" * 64],
)
def test_contract_requires_anchored_host_identity(
    valid_contract,
    valid_candidate,
    valid_permit,
    valid_environment,
    host_identity,
):
    valid_contract["host_identity"] = host_identity
    refresh("contract", valid_contract)

    assert "invalid_contract_host_identity" in codes(
        valid_contract, valid_candidate, valid_permit, valid_environment
    )


def test_contract_requires_host_identity_field(
    valid_contract, valid_candidate, valid_permit, valid_environment
):
    del valid_contract["host_identity"]
    refresh("contract", valid_contract)

    assert "invalid_contract_host_identity" in codes(
        valid_contract, valid_candidate, valid_permit, valid_environment
    )


@pytest.mark.parametrize(
    "host_identity",
    [None, "", " ", "192.168.110.65", "host-key", "sha256:" + "A" * 64],
)
def test_environment_requires_anchored_host_identity(
    valid_contract,
    valid_candidate,
    valid_permit,
    valid_environment,
    host_identity,
):
    if host_identity is None:
        del valid_environment["host_identity"]
    else:
        valid_environment["host_identity"] = host_identity

    assert "invalid_environment_host_identity" in codes(
        valid_contract, valid_candidate, valid_permit, valid_environment
    )


def test_environment_host_identity_must_match_contract(
    valid_contract, valid_candidate, valid_permit, valid_environment
):
    valid_environment["host_identity"] = "sha256:" + "8" * 64

    assert "host_identity_mismatch" in codes(
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


def test_contract_schema_requires_host_identity(valid_contract):
    del valid_contract["host_identity"]
    refresh("contract", valid_contract)

    assert validate_schema(
        valid_contract, "verification-contract.v1.schema.json"
    )


def test_contract_schema_requires_sha256_host_identity(valid_contract):
    valid_contract["host_identity"] = "192.168.110.65"
    refresh("contract", valid_contract)

    assert "$.host_identity" in {
        problem.location
        for problem in validate_schema(
            valid_contract, "verification-contract.v1.schema.json"
        )
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("connection_hint", "999.1.1.1"),
        ("gateway_endpoint", "192.168.110.65:0"),
        ("gateway_endpoint", "192.168.110.65:65536"),
        ("gateway_endpoint", "192.168.110.65"),
        ("gateway_endpoint", "999.168.110.65:50053"),
    ],
)
def test_contract_schema_rejects_invalid_network_endpoints(
    valid_contract, field, value
):
    valid_contract[field] = value
    refresh("contract", valid_contract)

    assert f"$.{field}" in {
        problem.location
        for problem in validate_schema(
            valid_contract, "verification-contract.v1.schema.json"
        )
    }


@pytest.mark.parametrize("port", [1, 65535])
def test_contract_schema_accepts_endpoint_port_boundaries(valid_contract, port):
    valid_contract["gateway_endpoint"] = f"192.168.110.65:{port}"
    refresh("contract", valid_contract)

    assert validate_schema(
        valid_contract, "verification-contract.v1.schema.json"
    ) == []


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
        "run": {"status": "COMPLETED"},
        "contract": valid_contract,
        "candidate": {},
        "permit": {},
        "environment": {},
        "artifacts": [],
        "tests": [],
        "claims": [],
        "traces": [],
        "verdict": {"status": "INCONCLUSIVE"},
        "unexpected": True,
    }

    assert [
        problem.code
        for problem in validate_schema(bundle, "evidence-bundle.v1.schema.json")
    ] == ["schema_error"]


@pytest.mark.parametrize(
    "schema_name",
    [
        "unknown.schema.json",
        "/definitely-not-a-gawain-schema.json",
        "../definitely-not-a-gawain-schema.json",
    ],
)
def test_schema_name_is_closed_and_cannot_traverse(schema_name):
    assert [
        (problem.code, problem.location, problem.message)
        for problem in validate_schema({}, schema_name)
    ] == [
        (
            "unknown_schema",
            "schema_name",
            f"unsupported schema name: {schema_name}",
        )
    ]


def test_static_schemas_are_valid_draft_2020_12_schemas():
    schema_package = resources.files("gawain_verification.schemas")
    for schema_name in (
        "verification-contract.v1.schema.json",
        "evidence-bundle.v1.schema.json",
    ):
        schema = json.loads(
            schema_package.joinpath(schema_name).read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-08-25 00:00:00Z",
        "20260825T000000Z",
        "2026-W35-2T00:00:00Z",
        "2026-08-25T00:00:00",
        "2026-08-25T00:00:00+01:00",
        "2026-08-25T00:00:00+00:00:00",
    ],
)
def test_permit_rejects_non_utc_grammar(
    valid_contract,
    valid_candidate,
    valid_permit,
    valid_environment,
    timestamp,
):
    valid_permit["not_before"] = timestamp
    refresh("permit", valid_permit)

    assert "permit_invalid_time" in codes(
        valid_contract, valid_candidate, valid_permit, valid_environment
    )


@pytest.mark.parametrize("suffix", ["Z", "+00:00"])
def test_permit_accepts_inclusive_utc_boundary_with_allowed_suffix(
    valid_contract,
    valid_candidate,
    valid_permit,
    valid_environment,
    suffix,
):
    boundary = f"2026-08-25T03:00:00{suffix}"
    valid_permit["not_before"] = boundary
    valid_permit["not_after"] = boundary
    refresh("permit", valid_permit)

    assert not {
        "permit_invalid_time",
        "permit_invalid_window",
        "permit_not_yet_valid",
        "permit_expired",
    }.intersection(
        codes(valid_contract, valid_candidate, valid_permit, valid_environment)
    )
