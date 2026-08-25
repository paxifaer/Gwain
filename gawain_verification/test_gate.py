from __future__ import annotations

from collections import Counter
from collections.abc import Mapping

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


def _required_test_cases(
    bundle: Mapping[object, object], problems: list[ValidationIssue]
) -> list[str] | None:
    contract = bundle.get("contract")
    if not isinstance(contract, Mapping):
        problems.append(
            issue("invalid_contract", "contract", "contract must be an object")
        )
        return None

    required = contract.get("required_test_cases")
    if (
        not isinstance(required, list)
        or not required
        or not all(isinstance(case_id, str) and bool(case_id) for case_id in required)
    ):
        problems.append(
            issue(
                "invalid_required_test_cases",
                "contract.required_test_cases",
                "required_test_cases must be a non-empty list of non-empty strings",
            )
        )
        return None

    duplicates = sorted(
        case_id for case_id, count in Counter(required).items() if count > 1
    )
    for case_id in duplicates:
        problems.append(
            issue(
                "duplicate_required_test_case",
                "contract.required_test_cases",
                f"required test case {case_id!r} is duplicated",
            )
        )
    if duplicates:
        return None
    return required


def _validate_record(
    record: Mapping[object, object],
    location: str,
    artifact_kinds: Mapping[str, str],
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

    for field in ("id", "command", "cwd", "environment_fingerprint"):
        value = record.get(field)
        if not isinstance(value, str) or not value:
            problems.append(
                issue(
                    f"invalid_{field}",
                    f"{location}.{field}",
                    f"{field} must be a non-empty string",
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
    if {"expected_test_count", "executed_test_count"}.issubset(valid_counts) and (
        valid_counts["executed_test_count"] != valid_counts["expected_test_count"]
    ):
        problems.append(
            issue(
                "test_count_mismatch",
                f"{location}.executed_test_count",
                "executed_test_count must equal expected_test_count",
            )
        )
    if set(COUNT_FIELDS).issubset(valid_counts) and (
        valid_counts["passed_test_count"]
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
    if not isinstance(oracle, Mapping) or not oracle:
        problems.append(
            issue(
                "invalid_oracle",
                f"{location}.oracle",
                "oracle must be a non-empty object",
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
    required = _required_test_cases(bundle, problems)
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
        problems.extend(_validate_record(record, location, artifact_kinds))

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
