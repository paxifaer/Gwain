from copy import deepcopy
from datetime import UTC, datetime
import importlib
from itertools import repeat

import pytest

import gawain_verification.schema as schema_module
from gawain_verification.issues import ValidationIssue, issue
from gawain_verification.schema import validate_schema


NOW = datetime(2026, 8, 25, 3, 0, tzinfo=UTC)

try:
    verdict_module = importlib.import_module("gawain_verification.verdict")
except ModuleNotFoundError:
    verdict_module = None


def api(name):
    assert verdict_module is not None, "Task 6 verdict module is not implemented"
    value = getattr(verdict_module, name, None)
    assert callable(value), f"Task 6 API {name} is not implemented"
    return value


def validate(bundle, **kwargs):
    gates = {
        "identity_issues": [],
        "artifact_issues": [],
        "test_issues": [],
        "trace_issues": [],
    }
    gates.update(kwargs)
    return api("validate_verdict")(bundle, now=NOW, **gates)


def codes(bundle, **kwargs):
    return [problem.code for problem in validate(bundle, **kwargs)]


def test_all_gate_results_are_required_keyword_arguments(valid_verdict_bundle):
    with pytest.raises(TypeError):
        api("validate_verdict")(valid_verdict_bundle, now=NOW)


class OneShotIssues:
    def __init__(self):
        self.next_calls = 0

    def __iter__(self):
        return self

    def __next__(self):
        self.next_calls += 1
        return issue("hidden", "gate", "must not be consumed")


@pytest.mark.parametrize("gate_name", ["identity_issues", "artifact_issues", "test_issues", "trace_issues"])
def test_one_shot_gate_results_are_rejected_without_consumption(
    valid_verdict_bundle, gate_name
):
    source = OneShotIssues()
    valid_verdict_bundle["verdict"]["status"] = (
        "ENV_INVALID" if gate_name == "identity_issues" else "INCONCLUSIVE"
    )

    first = validate(valid_verdict_bundle, **{gate_name: source})
    second = validate(valid_verdict_bundle, **{gate_name: source})

    assert first == second
    assert source.next_calls == 0
    assert "gate_result_invalid" in [problem.code for problem in first]


@pytest.mark.parametrize("source", [None, (item for item in ()), iter(())])
def test_non_snapshot_gate_shapes_fail_closed(valid_verdict_bundle, source):
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"
    assert "gate_result_invalid" in codes(
        valid_verdict_bundle, test_issues=source
    )


def test_invalid_test_cannot_be_hidden_by_empty_caller_issues(valid_verdict_bundle):
    record = valid_verdict_bundle["tests"][0]
    record["executed_test_count"] = 0
    record["passed_test_count"] = 0
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    found = codes(valid_verdict_bundle, test_issues=[])
    assert "test_gate_failed" in found
    assert "verdict_mismatch" not in found


@pytest.mark.parametrize(
    ("flags", "expected"),
    [
        ({"aborted": True}, "ABORTED"),
        ({"environment_valid": False}, "ENV_INVALID"),
        ({"infra_blocked": True}, "BLOCKED_INFRA"),
        ({"evidence_complete": False}, "INCONCLUSIVE"),
        ({"candidate_failed": True}, "FAIL"),
        ({"all_obligations_proven": True}, "READY_FOR_HUMAN_ACCEPTANCE"),
        ({}, "INCONCLUSIVE"),
    ],
)
def test_derive_verdict_exact_precedence(flags, expected):
    values = {
        "aborted": False,
        "environment_valid": True,
        "infra_blocked": False,
        "evidence_complete": True,
        "candidate_failed": False,
        "all_obligations_proven": False,
    }
    values.update(flags)

    assert api("derive_verdict")(**values) == expected


def test_every_higher_precedence_state_wins_over_lower_states():
    derive = api("derive_verdict")
    assert derive(
        aborted=True,
        environment_valid=False,
        infra_blocked=True,
        evidence_complete=False,
        candidate_failed=True,
        all_obligations_proven=True,
    ) == "ABORTED"
    assert derive(
        aborted=False,
        environment_valid=False,
        infra_blocked=True,
        evidence_complete=False,
        candidate_failed=True,
        all_obligations_proven=True,
    ) == "ENV_INVALID"
    assert derive(
        aborted=False,
        environment_valid=True,
        infra_blocked=True,
        evidence_complete=False,
        candidate_failed=True,
        all_obligations_proven=True,
    ) == "BLOCKED_INFRA"
    assert derive(
        aborted=False,
        environment_valid=True,
        infra_blocked=False,
        evidence_complete=False,
        candidate_failed=True,
        all_obligations_proven=True,
    ) == "INCONCLUSIVE"
    assert derive(
        aborted=False,
        environment_valid=True,
        infra_blocked=False,
        evidence_complete=True,
        candidate_failed=True,
        all_obligations_proven=True,
    ) == "FAIL"


def test_complete_proven_bundle_is_ready(valid_verdict_bundle):
    assert validate(valid_verdict_bundle) == []


def test_candidate_supplied_boolean_cannot_override_evidence(valid_verdict_bundle):
    valid_verdict_bundle["candidate"]["failed"] = True
    valid_verdict_bundle["candidate"]["all_obligations_proven"] = False

    assert validate(valid_verdict_bundle) == []


@pytest.mark.parametrize("status", ["PASS", "ACCEPTED", "WAIVED", "UNKNOWN"])
def test_illegal_verdicts_are_rejected_without_normalization(
    valid_verdict_bundle, status
):
    valid_verdict_bundle["verdict"]["status"] = status

    found = codes(valid_verdict_bundle)
    assert "invalid_verdict" in found
    assert "verdict_mismatch" in found
    mismatch = next(
        problem
        for problem in validate(valid_verdict_bundle)
        if problem.code == "verdict_mismatch"
    )
    assert mismatch.message == (
        "verdict status must be derived as READY_FOR_HUMAN_ACCEPTANCE"
    )
    assert valid_verdict_bundle["verdict"]["status"] == status


@pytest.mark.parametrize("value", [[], {}, True, None])
def test_malformed_claim_status_is_stable_and_fail_closed(
    valid_verdict_bundle, value
):
    valid_verdict_bundle["claims"][0]["status"] = value
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"
    original = deepcopy(valid_verdict_bundle)

    first = validate(valid_verdict_bundle)
    second = validate(valid_verdict_bundle)

    assert first == second
    assert "invalid_claim" in [problem.code for problem in first]
    assert valid_verdict_bundle == original


@pytest.mark.parametrize("value", [[], {}, True, None])
def test_malformed_run_status_is_stable_and_fail_closed(
    valid_verdict_bundle, value
):
    valid_verdict_bundle["run"]["status"] = value
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    first = validate(valid_verdict_bundle)
    second = validate(valid_verdict_bundle)

    assert first == second
    assert "invalid_run" in [problem.code for problem in first]


@pytest.mark.parametrize("value", [[], {}, True, None])
def test_malformed_acceptance_decision_is_separate_from_ready_verdict(
    valid_verdict_bundle, value
):
    acceptance = valid_acceptance(valid_verdict_bundle)
    acceptance["decision"] = value
    valid_verdict_bundle["human_acceptance"] = acceptance

    first = validate(valid_verdict_bundle)
    second = validate(valid_verdict_bundle)

    assert first == second
    assert [problem.code for problem in first] == ["invalid_human_acceptance"]


@pytest.mark.parametrize("value", [[], {}, True, None])
def test_malformed_claimed_verdict_does_not_change_independent_derivation(
    valid_verdict_bundle, value
):
    valid_verdict_bundle["verdict"]["status"] = value

    first = validate(valid_verdict_bundle)
    second = validate(valid_verdict_bundle)

    assert first == second
    assert [problem.code for problem in first] == [
        "invalid_verdict",
        "verdict_mismatch",
    ]
    assert first[1].message == (
        "verdict status must be derived as READY_FOR_HUMAN_ACCEPTANCE"
    )


@pytest.mark.parametrize("value", [[], {}, True, None])
def test_malformed_verdict_object_does_not_change_independent_derivation(
    valid_verdict_bundle, value
):
    valid_verdict_bundle["verdict"] = value

    found = validate(valid_verdict_bundle)

    assert [problem.code for problem in found] == [
        "invalid_verdict",
        "verdict_mismatch",
    ]
    assert found[1].message == (
        "verdict status must be derived as READY_FOR_HUMAN_ACCEPTANCE"
    )


@pytest.mark.parametrize("kind", ["missing", "duplicate", "unexpected"])
@pytest.mark.parametrize("section", ["tests", "claims"])
def test_required_ids_must_be_present_exactly_once(
    valid_verdict_bundle, section, kind
):
    records = valid_verdict_bundle[section]
    if kind == "missing":
        records.pop()
    elif kind == "duplicate":
        records.append(deepcopy(records[0]))
    else:
        records.append(
            {"id": "unexpected-id", "status": "PROVEN", "evidence": ["artifact-verdict-evidence"]}
            if section == "claims"
            else {"id": "unexpected-id"}
        )
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    found = codes(valid_verdict_bundle)
    assert any(kind in code and section[:-1] in code for code in found)


def test_disproven_complete_claim_fails(valid_verdict_bundle):
    valid_verdict_bundle["claims"][0]["status"] = "DISPROVEN"
    valid_verdict_bundle["verdict"]["status"] = "FAIL"

    assert validate(valid_verdict_bundle) == []


def test_inconclusive_claim_is_inconclusive(valid_verdict_bundle):
    valid_verdict_bundle["claims"][0]["status"] = "INCONCLUSIVE"
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    assert validate(valid_verdict_bundle) == []


@pytest.mark.parametrize(
    ("kwargs", "status"),
    [
        ({"identity_issues": [issue("identity", "x", "bad")]}, "ENV_INVALID"),
        ({"artifact_issues": [issue("artifact", "x", "bad")]}, "INCONCLUSIVE"),
        ({"test_issues": [issue("test", "x", "bad")]}, "INCONCLUSIVE"),
        ({"trace_issues": [issue("trace", "x", "bad")]}, "INCONCLUSIVE"),
    ],
)
def test_prerequisite_issues_determine_closed_status(
    valid_verdict_bundle, kwargs, status
):
    valid_verdict_bundle["claims"][0]["status"] = "DISPROVEN"
    valid_verdict_bundle["verdict"]["status"] = status

    assert validate(valid_verdict_bundle, **kwargs) == []


@pytest.mark.parametrize(
    ("run_status", "identity_issue", "expected"),
    [
        ("ABORTED", True, "ABORTED"),
        ("BLOCKED_INFRA", True, "ENV_INVALID"),
        ("BLOCKED_INFRA", False, "BLOCKED_INFRA"),
    ],
)
def test_run_terminal_precedence(
    valid_verdict_bundle, run_status, identity_issue, expected
):
    valid_verdict_bundle["run"]["status"] = run_status
    valid_verdict_bundle["verdict"]["status"] = expected
    kwargs = (
        {"identity_issues": [issue("identity", "x", "bad")]}
        if identity_issue
        else {}
    )

    assert validate(valid_verdict_bundle, **kwargs) == []


def valid_waiver(bundle):
    return {
        "author_kind": "human",
        "author": "operator@example.test",
        "reason": "Temporary documented exception",
        "scope": ["claim:restart-path-correlated", "test:P-01"],
        "policy_version": "gawain.waiver-policy.v1",
        "expires_at": "2026-08-26T03:00:00Z",
        "run_id": bundle["run_id"],
        "contract_id": bundle["contract"]["contract_id"],
        "candidate_id": bundle["candidate"]["candidate_id"],
    }


def test_any_valid_waiver_prevents_ready(valid_verdict_bundle):
    valid_verdict_bundle["waivers"] = [valid_waiver(valid_verdict_bundle)]
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    assert validate(valid_verdict_bundle) == []


def test_waiver_cannot_turn_failure_into_success(valid_verdict_bundle):
    valid_verdict_bundle["claims"][0]["status"] = "DISPROVEN"
    valid_verdict_bundle["waivers"] = [valid_waiver(valid_verdict_bundle)]
    valid_verdict_bundle["verdict"]["status"] = "FAIL"

    assert validate(valid_verdict_bundle) == []


def test_invalid_waiver_makes_disproven_evidence_inconclusive(valid_verdict_bundle):
    valid_verdict_bundle["claims"][0]["status"] = "DISPROVEN"
    invalid = valid_waiver(valid_verdict_bundle)
    invalid["extra"] = True
    valid_verdict_bundle["waivers"] = [invalid]
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    found = codes(valid_verdict_bundle)
    assert "invalid_waiver" in found
    assert "verdict_mismatch" not in found


@pytest.mark.parametrize("field", ["author_kind", "policy_version"])
@pytest.mark.parametrize("value", [[], {}, True, None])
def test_malformed_waiver_status_like_fields_are_stable_and_fail_closed(
    valid_verdict_bundle, field, value
):
    waiver = valid_waiver(valid_verdict_bundle)
    waiver[field] = value
    valid_verdict_bundle["waivers"] = [waiver]
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    first = validate(valid_verdict_bundle)
    second = validate(valid_verdict_bundle)

    assert first == second
    assert "invalid_waiver" in [problem.code for problem in first]


@pytest.mark.parametrize("field", ["run_id", "contract_id", "candidate_id"])
def test_waiver_identity_binding_prevents_replay(valid_verdict_bundle, field):
    waiver = valid_waiver(valid_verdict_bundle)
    waiver[field] = "run-other" if field == "run_id" else "sha256:" + "0" * 64
    valid_verdict_bundle["waivers"] = [waiver]
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    assert "invalid_waiver_binding" in codes(valid_verdict_bundle)


@pytest.mark.parametrize("scope", [["P-01"], ["restart-path-correlated"]])
def test_waiver_scope_requires_authoritative_namespace(
    valid_verdict_bundle, scope
):
    waiver = valid_waiver(valid_verdict_bundle)
    waiver["scope"] = scope
    valid_verdict_bundle["waivers"] = [waiver]
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    assert "invalid_waiver_scope" in codes(valid_verdict_bundle)


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda waiver: waiver.update(author_kind="service"), "invalid_waiver"),
        (lambda waiver: waiver.update(author="   "), "invalid_waiver"),
        (lambda waiver: waiver.update(reason=""), "invalid_waiver"),
        (lambda waiver: waiver.update(scope=[]), "invalid_waiver"),
        (lambda waiver: waiver.update(scope=["P-01", "P-01"]), "invalid_waiver"),
        (lambda waiver: waiver.update(scope=["unknown"]), "invalid_waiver_scope"),
        (lambda waiver: waiver.update(policy_version="v2"), "invalid_waiver"),
        (lambda waiver: waiver.update(expires_at="2026-08-25T03:00:00Z"), "waiver_expired"),
        (lambda waiver: waiver.update(expires_at="2026-02-30T03:00:00Z"), "invalid_waiver_time"),
        (lambda waiver: waiver.update(expires_at="2026-08-26T03:00:00+01:00"), "invalid_waiver_time"),
        (lambda waiver: waiver.update(extra=True), "invalid_waiver"),
    ],
)
def test_waiver_is_closed_human_scoped_and_unexpired(
    valid_verdict_bundle, mutation, expected
):
    waiver = valid_waiver(valid_verdict_bundle)
    mutation(waiver)
    valid_verdict_bundle["waivers"] = [waiver]
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    assert expected in codes(valid_verdict_bundle)


def valid_acceptance(bundle):
    return {
        "author_kind": "human",
        "author": "reviewer@example.test",
        "reason": "Reviewed independent evidence",
        "decision": "ACCEPTED",
        "recorded_at": "2026-08-25T03:00:00+00:00",
        "run_id": bundle["run_id"],
        "contract_id": bundle["contract"]["contract_id"],
        "candidate_id": bundle["candidate"]["candidate_id"],
    }


def test_human_acceptance_is_never_synthesized_and_input_is_unchanged(
    valid_verdict_bundle
):
    original = deepcopy(valid_verdict_bundle)

    assert validate(valid_verdict_bundle) == []
    assert valid_verdict_bundle == original
    assert "human_acceptance" not in valid_verdict_bundle


def test_valid_human_acceptance_does_not_change_verdict(valid_verdict_bundle):
    valid_verdict_bundle["human_acceptance"] = valid_acceptance(valid_verdict_bundle)

    assert validate(valid_verdict_bundle) == []


@pytest.mark.parametrize("decision", ["ACCEPTED", "REJECTED"])
@pytest.mark.parametrize(
    "terminal",
    ["ABORTED", "ENV_INVALID", "BLOCKED_INFRA", "INCONCLUSIVE", "FAIL"],
)
def test_human_acceptance_requires_independently_ready_verdict(
    valid_verdict_bundle, terminal, decision
):
    kwargs = {}
    if terminal == "ABORTED":
        valid_verdict_bundle["run"]["status"] = "ABORTED"
    elif terminal == "ENV_INVALID":
        kwargs["identity_issues"] = [issue("identity", "gate", "invalid")]
    elif terminal == "BLOCKED_INFRA":
        valid_verdict_bundle["run"]["status"] = "BLOCKED_INFRA"
    elif terminal == "INCONCLUSIVE":
        valid_verdict_bundle["claims"][0]["status"] = "INCONCLUSIVE"
    else:
        valid_verdict_bundle["claims"][0]["status"] = "DISPROVEN"
    acceptance = valid_acceptance(valid_verdict_bundle)
    acceptance["decision"] = decision
    valid_verdict_bundle["human_acceptance"] = acceptance
    valid_verdict_bundle["verdict"]["status"] = terminal

    found = validate(valid_verdict_bundle, **kwargs)

    assert "human_acceptance_not_ready" in [problem.code for problem in found]
    assert "verdict_mismatch" not in [problem.code for problem in found]


def test_malformed_acceptance_on_nonready_reports_both_issues(valid_verdict_bundle):
    valid_verdict_bundle["run"]["status"] = "BLOCKED_INFRA"
    valid_verdict_bundle["verdict"]["status"] = "BLOCKED_INFRA"
    acceptance = valid_acceptance(valid_verdict_bundle)
    acceptance["decision"] = []
    valid_verdict_bundle["human_acceptance"] = acceptance

    assert {"invalid_human_acceptance", "human_acceptance_not_ready"}.issubset(
        set(codes(valid_verdict_bundle))
    )


def test_human_acceptance_is_bound_to_run(valid_verdict_bundle):
    acceptance = valid_acceptance(valid_verdict_bundle)
    acceptance["run_id"] = "run-other"
    valid_verdict_bundle["human_acceptance"] = acceptance

    found = codes(valid_verdict_bundle)
    assert "invalid_human_acceptance" in found
    assert "verdict_mismatch" not in found


def test_future_human_acceptance_is_rejected_without_affecting_verdict(
    valid_verdict_bundle
):
    acceptance = valid_acceptance(valid_verdict_bundle)
    acceptance["recorded_at"] = "2026-08-25T03:00:00.000001Z"
    valid_verdict_bundle["human_acceptance"] = acceptance

    assert codes(valid_verdict_bundle) == ["invalid_human_acceptance"]


@pytest.mark.parametrize(
    ("fraction", "valid"),
    [(".1", True), (".123456", True), (".1234567", False)],
)
def test_utc_fraction_is_limited_to_six_digits(
    valid_verdict_bundle, fraction, valid
):
    waiver = valid_waiver(valid_verdict_bundle)
    waiver["expires_at"] = f"2026-08-26T03:00:00{fraction}Z"
    acceptance = valid_acceptance(valid_verdict_bundle)
    acceptance["recorded_at"] = f"2026-08-25T02:59:59{fraction}Z"
    valid_verdict_bundle["waivers"] = [waiver]
    valid_verdict_bundle["human_acceptance"] = acceptance
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    found = validate(valid_verdict_bundle)
    if valid:
        assert [problem.code for problem in found] == [
            "human_acceptance_not_ready"
        ]
    else:
        assert {"invalid_waiver_time", "invalid_human_acceptance"}.issubset(
            {problem.code for problem in found}
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda acceptance: acceptance.update(author_kind="candidate"),
        lambda acceptance: acceptance.update(author=" "),
        lambda acceptance: acceptance.update(reason=" "),
        lambda acceptance: acceptance.update(decision="READY"),
        lambda acceptance: acceptance.update(recorded_at="2026-08-25T03:00:00+01:00"),
        lambda acceptance: acceptance.update(recorded_at="2026-02-30T03:00:00Z"),
        lambda acceptance: acceptance.update(contract_id="sha256:" + "0" * 64),
        lambda acceptance: acceptance.update(candidate_id="sha256:" + "0" * 64),
        lambda acceptance: acceptance.update(extra=True),
    ],
)
def test_malformed_or_forged_acceptance_is_reported_but_does_not_change_verdict(
    valid_verdict_bundle, mutation
):
    acceptance = valid_acceptance(valid_verdict_bundle)
    mutation(acceptance)
    valid_verdict_bundle["human_acceptance"] = acceptance

    found = codes(valid_verdict_bundle)
    assert "invalid_human_acceptance" in found
    assert "verdict_mismatch" not in found


@pytest.mark.parametrize("bad_bundle", [None, True, [], "bundle"])
def test_malformed_bundle_shapes_fail_closed_without_crash(bad_bundle):
    assert codes(bad_bundle) == ["invalid_bundle"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("run", True),
        ("contract", True),
        ("tests", True),
        ("claims", True),
        ("verdict", True),
        ("waivers", True),
        ("human_acceptance", True),
    ],
)
def test_boolean_external_shapes_fail_closed(valid_verdict_bundle, field, value):
    valid_verdict_bundle[field] = value

    assert validate(valid_verdict_bundle)


class HostileString(str):
    def strip(self, *args, **kwargs):
        raise AssertionError("hostile string method invoked")

    def __hash__(self):
        raise AssertionError("hostile string hash invoked")

    def __eq__(self, other):
        raise AssertionError("hostile string equality invoked")


class HostileList(list):
    def __iter__(self):
        raise AssertionError("hostile list iterator invoked")


class HostileDict(dict):
    def get(self, *args, **kwargs):
        raise AssertionError("hostile dict get invoked")


def test_hostile_builtin_subclasses_fail_closed_without_methods(
    valid_verdict_bundle
):
    bundles = []
    hostile_id = deepcopy(valid_verdict_bundle)
    hostile_id["claims"][0]["id"] = HostileString("claim")
    hostile_id["verdict"]["status"] = "INCONCLUSIVE"
    bundles.append(hostile_id)
    hostile_claims = deepcopy(valid_verdict_bundle)
    hostile_claims["claims"] = HostileList(hostile_claims["claims"])
    hostile_claims["verdict"]["status"] = "INCONCLUSIVE"
    bundles.append(hostile_claims)
    hostile_verdict = deepcopy(valid_verdict_bundle)
    hostile_verdict["verdict"] = HostileDict(hostile_verdict["verdict"])
    bundles.append(hostile_verdict)

    for bundle in bundles:
        assert validate(bundle)


class HostileIterable:
    def __iter__(self):
        yield issue("first", "x", "bad")
        raise RuntimeError("hostile")


def test_hostile_and_malformed_issue_iterables_fail_closed_deterministically(
    valid_verdict_bundle
):
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"
    first = validate(valid_verdict_bundle, test_issues=HostileIterable())
    second = validate(valid_verdict_bundle, test_issues=HostileIterable())

    assert first == second
    assert "gate_result_invalid" in [problem.code for problem in first]
    assert validate(valid_verdict_bundle, test_issues=[True])


def test_malformed_validation_issue_record_is_rejected(valid_verdict_bundle):
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"
    malformed = ValidationIssue(code=True, location=[], message={})

    assert "gate_result_invalid" in codes(
        valid_verdict_bundle, test_issues=[malformed]
    )


def test_unbounded_issue_iterable_is_bounded_and_rejected(valid_verdict_bundle):
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    assert "gate_result_invalid" in codes(
        valid_verdict_bundle,
        test_issues=repeat(issue("test", "test", "failed")),
    )


def test_gate_snapshot_limit_fails_closed(valid_verdict_bundle, monkeypatch):
    monkeypatch.setattr(verdict_module, "MAX_GATE_ISSUES", 1)
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"
    gate = [issue("one", "gate", "bad"), issue("two", "gate", "bad")]

    assert "gate_result_invalid" in codes(valid_verdict_bundle, test_issues=gate)


@pytest.mark.parametrize(
    ("constant", "mutation"),
    [
        ("MAX_REQUIRED_CLAIMS", lambda bundle: None),
        ("MAX_REQUIRED_TESTS", lambda bundle: None),
        ("MAX_RECORDS", lambda bundle: None),
        (
            "MAX_WAIVERS",
            lambda bundle: bundle.update(
                waivers=[valid_waiver(bundle), valid_waiver(bundle)]
            ),
        ),
        (
            "MAX_SCOPE_IDS",
            lambda bundle: bundle.update(waivers=[valid_waiver(bundle)]),
        ),
    ],
)
def test_resource_limits_fail_closed(
    valid_verdict_bundle, monkeypatch, constant, mutation
):
    monkeypatch.setattr(verdict_module, constant, 1)
    mutation(valid_verdict_bundle)
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    assert "resource_limit_exceeded" in codes(valid_verdict_bundle)


def test_claim_evidence_limit_fails_closed(valid_verdict_bundle, monkeypatch):
    monkeypatch.setattr(verdict_module, "MAX_EVIDENCE_IDS", 0)
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    assert "resource_limit_exceeded" in codes(valid_verdict_bundle)


def test_issue_output_is_capped_with_marker(valid_verdict_bundle, monkeypatch):
    monkeypatch.setattr(verdict_module, "MAX_ISSUES", 3)
    valid_verdict_bundle["claims"] = []
    valid_verdict_bundle["tests"] = []
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    found = validate(valid_verdict_bundle)

    assert len(found) == 3
    assert "issue_limit_reached" in [problem.code for problem in found]


def test_long_untrusted_id_is_not_echoed_in_diagnostics(
    valid_verdict_bundle, monkeypatch
):
    monkeypatch.setattr(verdict_module, "MAX_STRING_LENGTH", 8)
    raw_id = "candidate-controlled-" + "x" * 100
    valid_verdict_bundle["claims"][0]["id"] = raw_id
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    found = validate(valid_verdict_bundle)

    assert found
    assert raw_id not in repr(found)


def test_validation_is_nonmutating_and_deterministic(valid_verdict_bundle):
    original = deepcopy(valid_verdict_bundle)

    first = validate(valid_verdict_bundle)
    second = validate(valid_verdict_bundle)

    assert first == second == []
    assert valid_verdict_bundle == original


def test_contract_schema_requires_unique_nonempty_claim_ids(valid_contract):
    assert validate_schema(valid_contract, "verification-contract.v1.schema.json") == []
    for value in ([], [""], ["same", "same"]):
        contract = deepcopy(valid_contract)
        contract["required_claims"] = value
        assert validate_schema(contract, "verification-contract.v1.schema.json")


def test_partially_malformed_required_test_authority_fails_closed(
    valid_verdict_bundle
):
    valid_verdict_bundle["contract"]["required_test_cases"].append(True)
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    assert "invalid_required_tests" in codes(valid_verdict_bundle)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda bundle: bundle["run"].update(extra=True),
        lambda bundle: bundle["run"].update(status="RUNNING"),
        lambda bundle: bundle["claims"][0].update(extra=True),
        lambda bundle: bundle["claims"][0].update(status="WAIVED"),
        lambda bundle: bundle["claims"][0].update(evidence=[]),
        lambda bundle: bundle["verdict"].update(extra=True),
        lambda bundle: bundle["verdict"].update(status="PASS"),
    ],
)
def test_evidence_schema_closes_run_claim_and_verdict_records(
    valid_verdict_bundle, mutation
):
    assert validate_schema(valid_verdict_bundle, "evidence-bundle.v1.schema.json") == []
    mutation(valid_verdict_bundle)
    assert validate_schema(valid_verdict_bundle, "evidence-bundle.v1.schema.json")


def test_evidence_schema_closes_waiver_and_human_acceptance(valid_verdict_bundle):
    valid_verdict_bundle["waivers"] = [valid_waiver(valid_verdict_bundle)]
    valid_verdict_bundle["human_acceptance"] = valid_acceptance(valid_verdict_bundle)
    assert validate_schema(valid_verdict_bundle, "evidence-bundle.v1.schema.json") == []

    valid_verdict_bundle["waivers"][0]["extra"] = True
    valid_verdict_bundle["human_acceptance"]["extra"] = True
    locations = {
        problem.location
        for problem in validate_schema(valid_verdict_bundle, "evidence-bundle.v1.schema.json")
    }
    assert {"$.waivers[0]", "$.human_acceptance"}.issubset(locations)


def test_schema_rejects_human_acceptance_with_claimed_nonready_verdict(
    valid_verdict_bundle
):
    valid_verdict_bundle["human_acceptance"] = valid_acceptance(valid_verdict_bundle)
    valid_verdict_bundle["verdict"]["status"] = "FAIL"

    assert validate_schema(valid_verdict_bundle, "evidence-bundle.v1.schema.json")


def set_first_oracle(bundle, value):
    requirement_oracle = bundle["contract"]["required_test_cases"][0]["oracle"]
    record_oracle = bundle["tests"][0]["oracle"]
    requirement_oracle["expected"] = deepcopy(value)
    record_oracle["expected"] = deepcopy(value)
    record_oracle["observed"] = deepcopy(value)
    record_oracle["passed"] = True


@pytest.mark.parametrize(
    ("value_factory", "accepted"),
    [
        (lambda: {"nested": ["x" * 512]}, True),
        (lambda: {"nested": ["x" * 513]}, False),
        (lambda: [True] * 2048, True),
        (lambda: [True] * 2049, False),
        (lambda: {f"key-{index}": True for index in range(2048)}, True),
        (lambda: {f"key-{index}": True for index in range(2049)}, False),
    ],
)
def test_oracle_schema_and_runtime_collection_boundaries(
    valid_verdict_bundle, value_factory, accepted
):
    set_first_oracle(valid_verdict_bundle, value_factory())

    contract_issues = validate_schema(
        valid_verdict_bundle["contract"], "verification-contract.v1.schema.json"
    )
    bundle_issues = validate_schema(
        valid_verdict_bundle, "evidence-bundle.v1.schema.json"
    )
    if accepted:
        assert contract_issues == []
        assert bundle_issues == []
        assert validate(valid_verdict_bundle) == []
    else:
        assert contract_issues
        assert bundle_issues
        valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"
        assert "test_gate_failed" in codes(valid_verdict_bundle)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(float("nan"), id="nan"),
        pytest.param(float("inf"), id="infinity"),
    ],
)
def test_runtime_rejects_nonfinite_oracle_numbers(valid_verdict_bundle, value):
    set_first_oracle(valid_verdict_bundle, value)
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    assert "test_gate_failed" in codes(valid_verdict_bundle)


def test_runtime_rejects_oracle_depth_beyond_gate_limit(valid_verdict_bundle):
    value = True
    for _ in range(66):
        value = [value]
    set_first_oracle(valid_verdict_bundle, value)
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    assert "test_gate_failed" in codes(valid_verdict_bundle)


def test_runtime_rejects_oracle_global_node_budget(valid_verdict_bundle):
    value = [[True] * 100 for _ in range(101)]
    set_first_oracle(valid_verdict_bundle, value)
    valid_verdict_bundle["verdict"]["status"] = "INCONCLUSIVE"

    assert "test_gate_failed" in codes(valid_verdict_bundle)


def schema_depth_value(absolute_leaf_depth):
    value = True
    for _ in range(absolute_leaf_depth - 2):
        value = [value]
    return {"value": value}


def json_value_node_count(value):
    count = 0
    stack = [value]
    while stack:
        current = stack.pop()
        count += 1
        if type(current) is list:
            stack.extend(current)
        elif type(current) is dict:
            stack.extend(current.values())
    return count


class SchemaStringSubclass(str):
    pass


def test_schema_resource_preflight_accepts_depth_64_and_rejects_65(
    valid_verdict_bundle,
):
    valid_verdict_bundle["environment"] = schema_depth_value(64)
    assert validate_schema(
        valid_verdict_bundle, "evidence-bundle.v1.schema.json"
    ) == []

    valid_verdict_bundle["environment"] = schema_depth_value(65)
    assert [
        (problem.code, problem.location, problem.message)
        for problem in validate_schema(
            valid_verdict_bundle, "evidence-bundle.v1.schema.json"
        )
    ] == [
        (
            "schema_resource_limit",
            "$",
            "schema input exceeds safe resource limits",
        )
    ]


def test_schema_resource_preflight_rejects_depth_500_without_recursion_error(
    valid_verdict_bundle,
):
    valid_verdict_bundle["environment"] = schema_depth_value(500)

    assert [problem.code for problem in validate_schema(
        valid_verdict_bundle, "evidence-bundle.v1.schema.json"
    )] == ["schema_resource_limit"]


def test_schema_resource_preflight_rejects_cycles(valid_verdict_bundle):
    cycle = []
    cycle.append(cycle)
    valid_verdict_bundle["environment"] = {"value": cycle}

    assert [problem.code for problem in validate_schema(
        valid_verdict_bundle, "evidence-bundle.v1.schema.json"
    )] == ["schema_resource_limit"]


def test_schema_resource_preflight_enforces_aggregate_node_boundary(
    valid_verdict_bundle, monkeypatch
):
    node_count = json_value_node_count(valid_verdict_bundle)
    monkeypatch.setattr(schema_module, "MAX_SCHEMA_NODES", node_count, raising=False)
    assert validate_schema(
        valid_verdict_bundle, "evidence-bundle.v1.schema.json"
    ) == []

    monkeypatch.setattr(schema_module, "MAX_SCHEMA_NODES", node_count - 1)
    assert [problem.code for problem in validate_schema(
        valid_verdict_bundle, "evidence-bundle.v1.schema.json"
    )] == ["schema_resource_limit"]


def test_schema_resource_preflight_enforces_container_width_boundary(
    valid_verdict_bundle, monkeypatch
):
    monkeypatch.setattr(schema_module, "MAX_SCHEMA_WIDTH", 32, raising=False)
    valid_verdict_bundle["environment"] = {
        f"key_{index}": True for index in range(32)
    }
    assert validate_schema(
        valid_verdict_bundle, "evidence-bundle.v1.schema.json"
    ) == []

    valid_verdict_bundle["environment"]["key_32"] = True
    assert [problem.code for problem in validate_schema(
        valid_verdict_bundle, "evidence-bundle.v1.schema.json"
    )] == ["schema_resource_limit"]


@pytest.mark.parametrize("target", ["value", "key"])
def test_schema_resource_preflight_enforces_one_mib_text_boundary(
    valid_verdict_bundle, target
):
    boundary = "x" * (1024 * 1024)
    if target == "value":
        valid_verdict_bundle["environment"] = {"value": boundary}
    else:
        valid_verdict_bundle["environment"] = {boundary: True}
    assert validate_schema(
        valid_verdict_bundle, "evidence-bundle.v1.schema.json"
    ) == []

    oversized = boundary + "x"
    if target == "value":
        valid_verdict_bundle["environment"] = {"value": oversized}
    else:
        valid_verdict_bundle["environment"] = {oversized: True}
    assert [problem.code for problem in validate_schema(
        valid_verdict_bundle, "evidence-bundle.v1.schema.json"
    )] == ["schema_resource_limit"]


@pytest.mark.parametrize(
    "unsafe_value",
    [
        pytest.param(float("nan"), id="nonfinite"),
        pytest.param(float("inf"), id="infinity"),
        pytest.param((True,), id="tuple"),
        pytest.param({1: True}, id="non-string-key"),
        pytest.param(SchemaStringSubclass("text"), id="string-subclass"),
    ],
)
def test_schema_resource_preflight_requires_exact_json_values(
    valid_verdict_bundle, unsafe_value
):
    valid_verdict_bundle["environment"] = {"value": unsafe_value}

    assert [problem.code for problem in validate_schema(
        valid_verdict_bundle, "evidence-bundle.v1.schema.json"
    )] == ["schema_resource_limit"]


def test_schema_diagnostics_are_bounded_with_one_limit_marker(
    valid_verdict_bundle,
):
    valid_verdict_bundle["claims"] = [{} for _ in range(300)]

    found = validate_schema(
        valid_verdict_bundle, "evidence-bundle.v1.schema.json"
    )

    assert len(found) == 256
    assert [problem.code for problem in found].count("schema_issue_limit") == 1


def test_schema_diagnostics_do_not_expose_invalid_values_or_keys(
    valid_verdict_bundle,
):
    secret_key = "credential_like_key"
    secret_value = "credential-value-" + "x" * 512
    set_first_oracle(valid_verdict_bundle, {secret_key: secret_value})

    found = validate_schema(
        valid_verdict_bundle, "evidence-bundle.v1.schema.json"
    )
    rendered = repr(found)

    assert found
    assert secret_key not in rendered
    assert secret_value not in rendered
    assert schema_module._json_location([secret_key], frozenset()) == "$[<key>]"
    assert all(
        problem.message.startswith("schema validation failed (")
        for problem in found
        if problem.code == "schema_error"
    )


def test_schema_loading_value_error_is_fixed_and_fail_closed(
    valid_verdict_bundle, monkeypatch
):
    def fail_loads(_text):
        raise ValueError("credential-like parser detail")

    monkeypatch.setattr(schema_module.json, "loads", fail_loads)

    assert validate_schema(
        valid_verdict_bundle, "evidence-bundle.v1.schema.json"
    ) == [
        ValidationIssue(
            code="schema_resource_limit",
            location="$",
            message="schema input exceeds safe resource limits",
        )
    ]


def test_jsonschema_exception_is_fixed_and_fail_closed(
    valid_verdict_bundle, monkeypatch
):
    def fail_validation(_validator, _instance):
        raise schema_module.SchemaError("credential-like schema detail")

    monkeypatch.setattr(
        schema_module.Draft202012Validator, "iter_errors", fail_validation
    )

    found = validate_schema(
        valid_verdict_bundle, "evidence-bundle.v1.schema.json"
    )

    assert found == [
        ValidationIssue(
            code="schema_error",
            location="$",
            message="schema validation failed (internal)",
        )
    ]
    assert "credential" not in repr(found)
