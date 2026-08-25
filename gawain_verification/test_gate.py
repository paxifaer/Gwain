"""Pre-release v1 semantics; oracle values allow depth 64 and 10,000 nodes each."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import math
import re

from .issues import ValidationIssue, issue


TEST_LEVELS = frozenset(
    {
        "unit",
        "component",
        "integration",
        "browser",
        "tauri",
        "deployment",
        "real_device_e2e",
    }
)
REQUIRED_EVIDENCE_KINDS = {
    "browser": frozenset({"browser-interaction"}),
    "tauri": frozenset({"tauri-interaction", "application-trace"}),
    "deployment": frozenset({"deployment-record", "installed-digest"}),
    "real_device_e2e": frozenset({"device-state", "application-trace"}),
}
COUNT_FIELDS = (
    "expected_test_count",
    "executed_test_count",
    "passed_test_count",
    "failed_test_count",
    "ignored_test_count",
)
TEST_FIELDS = frozenset(
    {
        "id",
        "required_level",
        "observed_level",
        "expected_outcome",
        "status",
        "command",
        "cwd",
        "environment_fingerprint",
        *COUNT_FIELDS,
        "exit_code",
        "oracle",
        "evidence",
    }
)
REQUIREMENT_FIELDS = frozenset(
    {"id", "required_level", "expected_outcome", "expected_test_count", "oracle"}
)
REQUIREMENT_ORACLE_FIELDS = frozenset({"assertion", "operator", "expected"})
RECORD_ORACLE_FIELDS = frozenset(
    {"assertion", "operator", "expected", "observed", "passed"}
)
ENVIRONMENT_FINGERPRINT_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
MAX_ORACLE_JSON_DEPTH = 64
MAX_ORACLE_JSON_NODES = 10_000


def _artifact_kinds(
    bundle: Mapping[object, object], problems: list[ValidationIssue]
) -> dict[str, str]:
    artifacts = bundle.get("artifacts")
    if not isinstance(artifacts, list):
        problems.append(
            issue("invalid_artifacts", "artifacts", "artifacts must be a list")
        )
        return {}

    id_counts = Counter(
        record.get("artifact_id")
        for record in artifacts
        if isinstance(record, Mapping)
        and isinstance(record.get("artifact_id"), str)
        and bool(record.get("artifact_id"))
    )
    return {
        artifact_id: kind
        for record in artifacts
        if isinstance(record, Mapping)
        and isinstance((artifact_id := record.get("artifact_id")), str)
        and bool(artifact_id)
        and id_counts[artifact_id] == 1
        and isinstance((kind := record.get("kind")), str)
        and bool(kind)
    }


def _is_bounded_json_value(value: object) -> bool:
    stack: list[tuple[str, object, int]] = [("value", value, 0)]
    active_containers: set[int] = set()
    node_count = 0

    while stack:
        action, current, depth = stack.pop()
        if action == "children":
            iterator, identity = current
            try:
                child = next(iterator)
            except StopIteration:
                active_containers.remove(identity)
                continue
            stack.append(("children", current, depth))
            stack.append(("value", child, depth))
            continue

        node_count += 1
        if node_count > MAX_ORACLE_JSON_NODES or depth > MAX_ORACLE_JSON_DEPTH:
            return False
        if current is None or type(current) in {str, bool, int}:
            continue
        if type(current) is float:
            if not math.isfinite(current):
                return False
            continue
        if type(current) not in {list, dict}:
            return False
        remaining_budget = MAX_ORACLE_JSON_NODES - node_count
        if len(current) > remaining_budget:
            return False
        if type(current) is list:
            children = iter(current)
        else:
            if not all(type(key) is str for key in current):
                return False
            children = iter(current.values())

        identity = id(current)
        if identity in active_containers:
            return False
        active_containers.add(identity)
        stack.append(("children", (children, identity), depth + 1))

    return True


def _bounded_json_equal(left: object, right: object) -> bool:
    stack: list[tuple[str, object, int]] = [("values", (left, right), 0)]
    node_count = 0
    while stack:
        action, current, depth = stack.pop()
        if action == "children":
            iterator = current
            try:
                pair = next(iterator)
            except StopIteration:
                continue
            stack.append(("children", iterator, depth))
            stack.append(("values", pair, depth))
            continue

        left_value, right_value = current
        node_count += 1
        if node_count > MAX_ORACLE_JSON_NODES or depth > MAX_ORACLE_JSON_DEPTH:
            return False
        if type(left_value) is not type(right_value):
            return False
        if type(left_value) is list:
            if len(left_value) != len(right_value):
                return False
            child_count = len(left_value)
            if child_count > MAX_ORACLE_JSON_NODES - node_count:
                return False
            children = zip(left_value, right_value)
        elif type(left_value) is dict:
            child_count = len(left_value)
            if child_count != len(right_value):
                return False
            if child_count > MAX_ORACLE_JSON_NODES - node_count:
                return False
            if left_value.keys() != right_value.keys():
                return False
            children = zip(
                left_value.values(), map(right_value.__getitem__, left_value)
            )
        else:
            if left_value != right_value:
                return False
            continue
        stack.append(("children", children, depth + 1))
    return True


def _valid_requirement(requirement: Mapping[object, object]) -> bool:
    oracle = requirement.get("oracle")
    return (
        set(requirement) == REQUIREMENT_FIELDS
        and isinstance(requirement.get("id"), str)
        and bool(requirement.get("id"))
        and isinstance(requirement.get("required_level"), str)
        and requirement.get("required_level") in TEST_LEVELS
        and isinstance(requirement.get("expected_outcome"), str)
        and requirement.get("expected_outcome") in {"PASS", "REJECT"}
        and isinstance(requirement.get("expected_test_count"), int)
        and not isinstance(requirement.get("expected_test_count"), bool)
        and requirement.get("expected_test_count") >= 1
        and isinstance(oracle, Mapping)
        and set(oracle) == REQUIREMENT_ORACLE_FIELDS
        and isinstance(oracle.get("assertion"), str)
        and bool(oracle.get("assertion").strip())
        and oracle.get("operator") == "equals"
        and oracle.get("expected") is not None
        and _is_bounded_json_value(oracle.get("expected"))
    )


def _required_test_cases(
    bundle: Mapping[object, object], problems: list[ValidationIssue]
) -> tuple[list[str] | None, dict[str, Mapping[object, object]]]:
    contract = bundle.get("contract")
    if not isinstance(contract, Mapping):
        problems.append(
            issue("invalid_contract", "contract", "contract must be an object")
        )
        return None, {}

    required = contract.get("required_test_cases")
    if (
        not isinstance(required, list)
        or not required
    ):
        problems.append(
            issue(
                "invalid_required_test_cases",
                "contract.required_test_cases",
                "required_test_cases must be a non-empty list",
            )
        )
        return None, {}

    candidate_ids = [
        requirement.get("id")
        for requirement in required
        if isinstance(requirement, Mapping)
        and isinstance(requirement.get("id"), str)
        and bool(requirement.get("id"))
    ]
    id_counts = Counter(candidate_ids)
    duplicates = sorted(case_id for case_id, count in id_counts.items() if count > 1)
    for case_id in duplicates:
        problems.append(
            issue(
                "duplicate_required_test_case",
                "contract.required_test_cases",
                f"required test case {case_id!r} is duplicated",
            )
        )
    authorities: dict[str, Mapping[object, object]] = {}
    for index, requirement in enumerate(required):
        location = f"contract.required_test_cases[{index}]"
        if not isinstance(requirement, Mapping) or not _valid_requirement(requirement):
            problems.append(
                issue(
                    "invalid_test_requirement",
                    location,
                    "test requirement must have the closed authoritative shape",
                )
            )
            continue
        case_id = requirement["id"]
        if id_counts[case_id] == 1:
            authorities[case_id] = requirement

    return list(authorities), authorities


def _validate_record(
    record: Mapping[object, object],
    location: str,
    artifact_kinds: Mapping[str, str],
    requirement: Mapping[object, object] | None,
) -> list[ValidationIssue]:
    problems: list[ValidationIssue] = []

    unexpected = sorted(
        (key for key in record if key not in TEST_FIELDS), key=lambda key: repr(key)
    )
    for key in unexpected:
        problems.append(
            issue(
                "unexpected_test_field",
                location,
                f"test record contains unexpected field {key!r}",
            )
        )

    for field in ("id", "command", "cwd"):
        value = record.get(field)
        if not isinstance(value, str) or not value:
            problems.append(
                issue(
                    f"invalid_{field}",
                    f"{location}.{field}",
                    f"{field} must be a non-empty string",
                )
            )

    environment_fingerprint = record.get("environment_fingerprint")
    if (
        not isinstance(environment_fingerprint, str)
        or ENVIRONMENT_FINGERPRINT_PATTERN.fullmatch(environment_fingerprint) is None
    ):
        problems.append(
            issue(
                "invalid_environment_fingerprint",
                f"{location}.environment_fingerprint",
                "environment_fingerprint must be a lowercase sha256 digest",
            )
        )

    required_level = record.get("required_level")
    observed_level = record.get("observed_level")
    required_level_valid = (
        isinstance(required_level, str) and required_level in TEST_LEVELS
    )
    observed_level_valid = (
        isinstance(observed_level, str) and observed_level in TEST_LEVELS
    )
    if not required_level_valid:
        problems.append(
            issue(
                "invalid_required_level",
                f"{location}.required_level",
                "required_level must be a supported test level",
            )
        )
    if not observed_level_valid:
        problems.append(
            issue(
                "invalid_observed_level",
                f"{location}.observed_level",
                "observed_level must be a supported test level",
            )
        )
    if required_level_valid and observed_level_valid and required_level != observed_level:
        problems.append(
            issue(
                "test_level_mismatch",
                f"{location}.observed_level",
                "observed test level must exactly match the required level",
            )
        )
    if requirement is not None and not _bounded_json_equal(
        required_level, requirement["required_level"]
    ):
        problems.append(
            issue(
                "required_level_contract_mismatch",
                f"{location}.required_level",
                "required_level must match the contract requirement",
            )
        )

    expected_outcome = record.get("expected_outcome")
    status = record.get("status")
    expected_outcome_valid = (
        isinstance(expected_outcome, str)
        and expected_outcome in {"PASS", "REJECT"}
    )
    status_valid = (
        isinstance(status, str) and status in {"PASS", "EXPECTED_REJECT"}
    )
    if not expected_outcome_valid:
        problems.append(
            issue(
                "invalid_expected_outcome",
                f"{location}.expected_outcome",
                "expected_outcome must be PASS or REJECT",
            )
        )
    if not status_valid:
        problems.append(
            issue(
                "invalid_status",
                f"{location}.status",
                "status must be PASS or EXPECTED_REJECT",
            )
        )
    if expected_outcome_valid and status_valid:
        if expected_outcome == "REJECT" and status != "EXPECTED_REJECT":
            problems.append(
                issue(
                    "negative_test_not_rejected",
                    f"{location}.status",
                    "negative test must report EXPECTED_REJECT",
                )
            )
        elif expected_outcome == "PASS" and status != "PASS":
            problems.append(
                issue(
                    "positive_test_not_passed",
                    f"{location}.status",
                    "positive test must report PASS",
                )
            )
    if requirement is not None and not _bounded_json_equal(
        expected_outcome, requirement["expected_outcome"]
    ):
        problems.append(
            issue(
                "expected_outcome_contract_mismatch",
                f"{location}.expected_outcome",
                "expected_outcome must match the contract requirement",
            )
        )

    valid_counts: dict[str, int] = {}
    for field in COUNT_FIELDS:
        value = record.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            problems.append(
                issue(
                    f"invalid_{field}",
                    f"{location}.{field}",
                    f"{field} must be a non-negative integer",
                )
            )
        else:
            valid_counts[field] = value

    if valid_counts.get("expected_test_count") == 0:
        problems.append(
            issue(
                "invalid_expected_test_count",
                f"{location}.expected_test_count",
                "expected_test_count must be greater than zero",
            )
        )
    if valid_counts.get("executed_test_count") == 0:
        problems.append(
            issue(
                "zero_tests_executed",
                f"{location}.executed_test_count",
                "at least one test must execute",
            )
        )
    if (
        valid_counts.get("expected_test_count", 0) > 0
        and valid_counts.get("executed_test_count", 0) > 0
        and valid_counts["executed_test_count"]
        != valid_counts["expected_test_count"]
    ):
        problems.append(
            issue(
                "test_count_mismatch",
                f"{location}.executed_test_count",
                "executed_test_count must equal expected_test_count",
            )
        )
    if (
        set(COUNT_FIELDS).issubset(valid_counts)
        and valid_counts["expected_test_count"] > 0
        and valid_counts["executed_test_count"] > 0
        and valid_counts["passed_test_count"]
        + valid_counts["failed_test_count"]
        + valid_counts["ignored_test_count"]
        != valid_counts["executed_test_count"]
    ):
        problems.append(
            issue(
                "test_count_sum_mismatch",
                location,
                "passed, failed, and ignored counts must sum to executed count",
            )
        )

    if requirement is not None and not _bounded_json_equal(
        record.get("expected_test_count"), requirement["expected_test_count"]
    ):
        problems.append(
            issue(
                "expected_test_count_contract_mismatch",
                f"{location}.expected_test_count",
                "expected_test_count must match the contract requirement",
            )
        )
    if valid_counts.get("failed_test_count", 0) > 0:
        problems.append(
            issue(
                "test_failures_present",
                f"{location}.failed_test_count",
                "required test run must contain no failures",
            )
        )
    if valid_counts.get("ignored_test_count", 0) > 0:
        problems.append(
            issue(
                "required_test_ignored",
                f"{location}.ignored_test_count",
                "required test run must contain no ignored tests",
            )
        )

    exit_code = record.get("exit_code")
    if not isinstance(exit_code, int) or isinstance(exit_code, bool):
        problems.append(
            issue(
                "invalid_exit_code",
                f"{location}.exit_code",
                "exit_code must be an integer",
            )
        )
    elif exit_code != 0:
        problems.append(
            issue(
                "test_command_failed",
                f"{location}.exit_code",
                "test command must exit successfully",
            )
        )

    oracle = record.get("oracle")
    oracle_valid = (
        isinstance(oracle, Mapping)
        and set(oracle) == RECORD_ORACLE_FIELDS
        and isinstance(oracle.get("assertion"), str)
        and bool(oracle.get("assertion").strip())
        and oracle.get("operator") == "equals"
        and oracle.get("expected") is not None
        and _is_bounded_json_value(oracle.get("expected"))
        and oracle.get("observed") is not None
        and _is_bounded_json_value(oracle.get("observed"))
        and type(oracle.get("passed")) is bool
    )
    if not oracle_valid:
        problems.append(
            issue(
                "invalid_oracle",
                f"{location}.oracle",
                "oracle must have a bounded equals assertion and a boolean result",
            )
        )
    else:
        computed_result = _bounded_json_equal(
            oracle["expected"], oracle["observed"]
        )
        if oracle["passed"] is not computed_result:
            problems.append(
                issue(
                    "oracle_passed_mismatch",
                    f"{location}.oracle.passed",
                    "oracle passed must equal the independently computed result",
                )
            )
        if not computed_result:
            problems.append(
                issue(
                    "oracle_result_failed",
                    f"{location}.oracle.observed",
                    "oracle observed value does not equal the expected value",
                )
            )
    if requirement is not None and isinstance(oracle, Mapping):
        requirement_oracle = requirement["oracle"]
        if not _bounded_json_equal(
            oracle.get("assertion"), requirement_oracle["assertion"]
        ):
            problems.append(
                issue(
                    "oracle_assertion_contract_mismatch",
                    f"{location}.oracle.assertion",
                    "oracle assertion must match the contract requirement",
                )
            )
        if not _bounded_json_equal(
            oracle.get("operator"), requirement_oracle["operator"]
        ):
            problems.append(
                issue(
                    "oracle_operator_contract_mismatch",
                    f"{location}.oracle.operator",
                    "oracle operator must match the contract requirement",
                )
            )
        if not _bounded_json_equal(
            oracle.get("expected"), requirement_oracle["expected"]
        ):
            problems.append(
                issue(
                    "oracle_expected_contract_mismatch",
                    f"{location}.oracle.expected",
                    "oracle expected value must match the contract requirement",
                )
            )

    evidence = record.get("evidence")
    evidence_valid = (
        isinstance(evidence, list)
        and bool(evidence)
        and all(isinstance(reference, str) and bool(reference) for reference in evidence)
    )
    if not evidence_valid:
        problems.append(
            issue(
                "invalid_test_evidence",
                f"{location}.evidence",
                "evidence must be a non-empty list of non-empty artifact identifiers",
            )
        )
    else:
        if len(evidence) != len(set(evidence)):
            problems.append(
                issue(
                    "duplicate_test_evidence",
                    f"{location}.evidence",
                    "test evidence identifiers must be unique",
                )
            )
    evidence_ids = (
        evidence
        if isinstance(evidence, list)
        and all(isinstance(reference, str) for reference in evidence)
        else []
    )
    if required_level_valid:
        present_kinds = {
            artifact_kinds[reference]
            for reference in evidence_ids
            if reference in artifact_kinds
        }
        missing_kinds = sorted(
            REQUIRED_EVIDENCE_KINDS.get(required_level, frozenset()) - present_kinds
        )
        for kind in missing_kinds:
            problems.append(
                issue(
                    "missing_required_evidence_kind",
                    f"{location}.evidence",
                    f"{required_level} test requires evidence kind {kind!r}",
                )
            )

    return problems


def validate_tests(bundle: object) -> list[ValidationIssue]:
    if not isinstance(bundle, Mapping):
        return [issue("invalid_bundle", "bundle", "bundle must be an object")]

    problems: list[ValidationIssue] = []
    required, requirements = _required_test_cases(bundle, problems)
    artifact_kinds = _artifact_kinds(bundle, problems)

    records = bundle.get("tests")
    if not isinstance(records, list):
        problems.append(issue("invalid_tests", "tests", "tests must be a list"))
        return sorted(problems)

    record_ids: list[str] = []
    for index, record in enumerate(records):
        location = f"tests[{index}]"
        if not isinstance(record, Mapping):
            problems.append(
                issue(
                    "malformed_test_record",
                    location,
                    "test record must be an object",
                )
            )
            continue
        test_id = record.get("id")
        if isinstance(test_id, str) and test_id:
            record_ids.append(test_id)
        requirement = requirements.get(test_id) if isinstance(test_id, str) else None
        problems.extend(
            _validate_record(record, location, artifact_kinds, requirement)
        )

    id_counts = Counter(record_ids)
    duplicate_ids = sorted(
        test_id for test_id, count in id_counts.items() if count > 1
    )
    for test_id in duplicate_ids:
        problems.append(
            issue(
                "duplicate_test_record",
                "tests",
                f"test {test_id!r} appears more than once",
            )
        )

    if required is not None:
        required_set = set(required)
        for test_id in required:
            if id_counts[test_id] == 0:
                problems.append(
                    issue(
                        "missing_required_test",
                        "tests",
                        f"required test {test_id!r} is missing",
                    )
                )
        for test_id in sorted(set(record_ids) - required_set):
            problems.append(
                issue(
                    "unexpected_test_record",
                    "tests",
                    f"test {test_id!r} is not required by the contract",
                )
            )

    return sorted(problems)
