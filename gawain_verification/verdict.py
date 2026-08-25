"""Fail-closed verdict derivation for verifier-collected evidence."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
import math
import re

from .issues import ValidationIssue, issue
from .test_gate import validate_tests


VERDICTS = frozenset(
    {
        "FAIL",
        "INCONCLUSIVE",
        "BLOCKED_INFRA",
        "ENV_INVALID",
        "ABORTED",
        "READY_FOR_HUMAN_ACCEPTANCE",
    }
)
RUN_STATUSES = frozenset({"COMPLETED", "ABORTED", "BLOCKED_INFRA"})
CLAIM_STATUSES = frozenset({"PROVEN", "DISPROVEN", "INCONCLUSIVE"})
UTC_TIMESTAMP = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|\+00:00)$"
)
SHA256_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
# Public pre-release v1 ceilings for all untrusted verdict inputs and diagnostics.
MAX_STRING_LENGTH = 512
MAX_REQUIRED_TESTS = 1_024
MAX_REQUIRED_CLAIMS = 1_024
MAX_RECORDS = 2_048
MAX_WAIVERS = 256
MAX_SCOPE_IDS = 2_048
MAX_EVIDENCE_IDS = 2_048
MAX_GATE_ISSUES = 1_024
MAX_ISSUES = 256
MAX_JSON_NODES = 100_000


class _IssueCollector(list[ValidationIssue]):
    """Bound diagnostics; the final slot becomes a stable truncation marker."""

    def append(self, value: ValidationIssue) -> None:
        if MAX_ISSUES <= 0:
            return
        if len(self) < MAX_ISSUES:
            super().append(value)
            return
        marker = issue(
            "issue_limit_reached", "validation", "additional issues were suppressed"
        )
        if self[-1].code != marker.code:
            self[-1] = marker

def derive_verdict(
    *,
    aborted: bool,
    environment_valid: bool,
    infra_blocked: bool,
    evidence_complete: bool,
    candidate_failed: bool,
    all_obligations_proven: bool,
) -> str:
    if aborted:
        return "ABORTED"
    if not environment_valid:
        return "ENV_INVALID"
    if infra_blocked:
        return "BLOCKED_INFRA"
    if not evidence_complete:
        return "INCONCLUSIVE"
    if candidate_failed:
        return "FAIL"
    if all_obligations_proven:
        return "READY_FOR_HUMAN_ACCEPTANCE"
    return "INCONCLUSIVE"


def _snapshot_gate(
    source: object, name: str, problems: _IssueCollector
) -> bool:
    if type(source) not in {list, tuple} or len(source) > MAX_GATE_ISSUES:
        problems.append(
            issue(
                "gate_result_invalid",
                name,
                "gate result must be a bounded list or tuple of validation issues",
            )
        )
        return True
    snapshot = tuple(source)
    malformed = any(
        not (
            type(value) is ValidationIssue
            and _nonempty_text(value.code)
            and _nonempty_text(value.location)
            and _nonempty_text(value.message)
        )
        for value in snapshot
    )
    if malformed:
        problems.append(
            issue(
                "gate_result_invalid",
                name,
                "gate result contains malformed validation issues",
            )
        )
    return bool(snapshot) or malformed


def _nonempty_text(value: object) -> bool:
    return (
        type(value) is str
        and len(value) <= MAX_STRING_LENGTH
        and bool(value.strip())
    )


def _closed_record(value: object, fields: set[str]) -> bool:
    return (
        type(value) is dict
        and len(value) == len(fields)
        and all(type(key) is str and len(key) <= MAX_STRING_LENGTH for key in value)
        and set(value) == fields
    )


def _exact_json_tree(value: object) -> bool:
    stack = [value]
    seen = 0
    while stack:
        current = stack.pop()
        seen += 1
        if seen > MAX_JSON_NODES:
            return False
        if current is None or type(current) in {bool, int}:
            continue
        if type(current) is float:
            if not math.isfinite(current):
                return False
            continue
        if type(current) is str:
            if len(current) > MAX_STRING_LENGTH:
                return False
            continue
        if type(current) is list:
            if len(current) > MAX_RECORDS:
                return False
            stack.extend(current)
            continue
        if type(current) is dict:
            if len(current) > MAX_RECORDS or not all(
                type(key) is str and len(key) <= MAX_STRING_LENGTH
                for key in current
            ):
                return False
            stack.extend(current.values())
            continue
        return False
    return True


def _limit_problem(problems: _IssueCollector, location: str) -> None:
    problems.append(
        issue(
            "resource_limit_exceeded",
            location,
            "verification input exceeds a configured resource limit",
        )
    )


def _bundle_record_limits_valid(
    bundle: dict[object, object], problems: _IssueCollector
) -> bool:
    valid = True
    for field in ("artifacts", "traces"):
        records = bundle.get(field)
        if type(records) is list and len(records) > MAX_RECORDS:
            _limit_problem(problems, field)
            valid = False
    return valid


def _utc_time(value: object) -> datetime | None:
    if (
        type(value) is not str
        or len(value) > MAX_STRING_LENGTH
        or UTC_TIMESTAMP.fullmatch(value) is None
    ):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        return None
    return parsed.astimezone(UTC)


def _required_ids(
    bundle: dict[object, object], problems: _IssueCollector
) -> tuple[list[str], list[str], bool]:
    contract = bundle.get("contract")
    if type(contract) is not dict:
        problems.append(issue("invalid_contract", "contract", "contract must be an object"))
        return [], [], False

    claims_valid = True
    required_claims = contract.get("required_claims")
    if type(required_claims) is list and len(required_claims) > MAX_REQUIRED_CLAIMS:
        _limit_problem(problems, "contract.required_claims")
        required_claims = None
    if (
        type(required_claims) is not list
        or not required_claims
        or not all(_nonempty_text(value) for value in required_claims)
        or len(set(required_claims)) != len(required_claims)
    ):
        problems.append(
            issue(
                "invalid_required_claims",
                "contract.required_claims",
                "required_claims must be non-empty unique claim IDs",
            )
        )
        claim_ids: list[str] = []
        claims_valid = False
    else:
        claim_ids = list(required_claims)

    requirements = contract.get("required_test_cases")
    if type(requirements) is list and len(requirements) > MAX_REQUIRED_TESTS:
        _limit_problem(problems, "contract.required_test_cases")
        requirements = None
    test_ids: list[str] = []
    tests_valid = True
    if type(requirements) is not list or not requirements:
        tests_valid = False
    else:
        for requirement in requirements:
            if type(requirement) is not dict or not _nonempty_text(requirement.get("id")):
                tests_valid = False
                continue
            test_ids.append(requirement["id"])
        if len(test_ids) != len(requirements) or len(set(test_ids)) != len(test_ids):
            tests_valid = False
    if not tests_valid:
        problems.append(
            issue(
                "invalid_required_tests",
                "contract.required_test_cases",
                "required_test_cases must identify non-empty unique test IDs",
            )
        )
    return claim_ids, test_ids, claims_valid and tests_valid


def _validate_tests(
    bundle: dict[object, object], required: list[str], problems: _IssueCollector
) -> bool:
    records = bundle.get("tests")
    if type(records) is not list:
        problems.append(issue("invalid_tests", "tests", "tests must be a list"))
        return False
    if len(records) > MAX_RECORDS:
        _limit_problem(problems, "tests")
        return False
    ids = [record.get("id") for record in records if type(record) is dict]
    valid_ids = [value for value in ids if _nonempty_text(value)]
    structurally_valid = len(ids) == len(records) and len(valid_ids) == len(records)
    if not structurally_valid:
        problems.append(
            issue("invalid_test", "tests", "each test must be an object with a non-empty ID")
        )
    counts = Counter(valid_ids)
    required_set = set(required)
    for test_id in required:
        if counts[test_id] == 0:
            problems.append(issue("missing_test", "tests", "a required test is missing"))
            structurally_valid = False
        elif counts[test_id] > 1:
            problems.append(issue("duplicate_test", "tests", "a required test is duplicated"))
            structurally_valid = False
    for test_id in sorted(set(valid_ids) - required_set):
        problems.append(issue("unexpected_test", "tests", "an unexpected test is present"))
        structurally_valid = False
    return structurally_valid


def _validate_claims(
    bundle: dict[object, object], required: list[str], problems: _IssueCollector
) -> tuple[bool, dict[str, str]]:
    records = bundle.get("claims")
    if type(records) is not list:
        problems.append(issue("invalid_claims", "claims", "claims must be a list"))
        return False, {}
    if len(records) > MAX_RECORDS:
        _limit_problem(problems, "claims")
        return False, {}
    valid: list[tuple[str, str]] = []
    structurally_valid = True
    for index, record in enumerate(records):
        evidence = record.get("evidence") if type(record) is dict else None
        status = record.get("status") if type(record) is dict else None
        if not (
            _closed_record(record, {"id", "status", "evidence"})
            and _nonempty_text(record.get("id"))
            and type(status) is str
            and status in CLAIM_STATUSES
            and type(evidence) is list
            and bool(evidence)
            and len(evidence) <= MAX_EVIDENCE_IDS
            and all(_nonempty_text(value) for value in evidence)
            and len(set(evidence)) == len(evidence)
        ):
            if type(evidence) is list and len(evidence) > MAX_EVIDENCE_IDS:
                _limit_problem(problems, f"claims[{index}].evidence")
            problems.append(
                issue(
                    "invalid_claim",
                    f"claims[{index}]",
                    "claim must have the closed authoritative shape",
                )
            )
            structurally_valid = False
            continue
        valid.append((record["id"], status))
    counts = Counter(claim_id for claim_id, _ in valid)
    required_set = set(required)
    for claim_id in required:
        if counts[claim_id] == 0:
            problems.append(issue("missing_claim", "claims", "a required claim is missing"))
            structurally_valid = False
        elif counts[claim_id] > 1:
            problems.append(issue("duplicate_claim", "claims", "a required claim is duplicated"))
            structurally_valid = False
    for claim_id in sorted(set(counts) - required_set):
        problems.append(issue("unexpected_claim", "claims", "an unexpected claim is present"))
        structurally_valid = False
    statuses = {
        claim_id: status
        for claim_id, status in valid
        if counts[claim_id] == 1 and claim_id in required_set
    }
    return structurally_valid, statuses


def _validate_waivers(
    bundle: dict[object, object], scopes: set[str], now: object, problems: _IssueCollector
) -> tuple[bool, bool]:
    if "waivers" not in bundle:
        return True, False
    records = bundle.get("waivers")
    if type(records) is not list:
        problems.append(issue("invalid_waiver", "waivers", "waivers must be a list"))
        return False, True
    if len(records) > MAX_WAIVERS:
        _limit_problem(problems, "waivers")
        return False, True
    structurally_valid = True
    # Task 7 will add bundle_id after it defines and seals the canonical bundle ID.
    expected_fields = {
        "author_kind", "author", "reason", "scope", "policy_version", "expires_at",
        "run_id", "contract_id", "candidate_id",
    }
    try:
        normalized_now = (
            now.astimezone(UTC)
            if type(now) is datetime
            and now.tzinfo is not None
            and now.utcoffset() is not None
            else None
        )
    except Exception:
        normalized_now = None
    contract = bundle.get("contract")
    candidate = bundle.get("candidate")
    expected_run_id = bundle.get("run_id")
    expected_contract_id = contract.get("contract_id") if type(contract) is dict else None
    expected_candidate_id = candidate.get("candidate_id") if type(candidate) is dict else None
    expected_binding_valid = (
        _nonempty_text(expected_run_id)
        and _nonempty_text(expected_contract_id)
        and SHA256_ID.fullmatch(expected_contract_id) is not None
        and _nonempty_text(expected_candidate_id)
        and SHA256_ID.fullmatch(expected_candidate_id) is not None
    )
    for index, record in enumerate(records):
        location = f"waivers[{index}]"
        scope = record.get("scope") if type(record) is dict else None
        basic_valid = (
            _closed_record(record, expected_fields)
            and type(record.get("author_kind")) is str
            and record.get("author_kind") == "human"
            and _nonempty_text(record.get("author"))
            and _nonempty_text(record.get("reason"))
            and type(record.get("policy_version")) is str
            and record.get("policy_version") == "gawain.waiver-policy.v1"
            and type(scope) is list
            and bool(scope)
            and len(scope) <= MAX_SCOPE_IDS
            and all(_nonempty_text(value) for value in scope)
            and len(set(scope)) == len(scope)
            and _nonempty_text(record.get("run_id"))
            and _nonempty_text(record.get("contract_id"))
            and SHA256_ID.fullmatch(record["contract_id"]) is not None
            and _nonempty_text(record.get("candidate_id"))
            and SHA256_ID.fullmatch(record["candidate_id"]) is not None
        )
        if not basic_valid:
            if type(scope) is list and len(scope) > MAX_SCOPE_IDS:
                _limit_problem(problems, f"{location}.scope")
            problems.append(issue("invalid_waiver", location, "waiver must have the closed human-authored shape"))
            structurally_valid = False
            continue
        if (
            not expected_binding_valid
            or record["run_id"] != expected_run_id
            or record["contract_id"] != expected_contract_id
            or record["candidate_id"] != expected_candidate_id
        ):
            problems.append(
                issue(
                    "invalid_waiver_binding",
                    location,
                    "waiver identities must match this verification run",
                )
            )
            structurally_valid = False
        if not set(scope).issubset(scopes):
            problems.append(issue("invalid_waiver_scope", f"{location}.scope", "waiver scope must reference required claim or test IDs"))
            structurally_valid = False
        expires_at = _utc_time(record.get("expires_at"))
        if expires_at is None:
            problems.append(issue("invalid_waiver_time", f"{location}.expires_at", "expires_at must be a strict UTC timestamp"))
            structurally_valid = False
        elif normalized_now is None or expires_at <= normalized_now:
            problems.append(issue("waiver_expired", f"{location}.expires_at", "waiver must expire after now"))
            structurally_valid = False
    return structurally_valid, bool(records) or type(records) is not list


def _validate_acceptance(
    bundle: dict[object, object], now: object, problems: _IssueCollector
) -> None:
    if "human_acceptance" not in bundle:
        return
    record = bundle.get("human_acceptance")
    contract = bundle.get("contract")
    candidate = bundle.get("candidate")
    expected_run_id = bundle.get("run_id")
    expected_contract_id = contract.get("contract_id") if type(contract) is dict else None
    expected_candidate_id = candidate.get("candidate_id") if type(candidate) is dict else None
    expected_fields = {
        "author_kind", "author", "reason", "decision", "recorded_at",
        "run_id", "contract_id", "candidate_id",
    }
    valid = (
        _closed_record(record, expected_fields)
        and type(record.get("author_kind")) is str
        and record.get("author_kind") == "human"
        and _nonempty_text(record.get("author"))
        and _nonempty_text(record.get("reason"))
        and type(record.get("decision")) is str
        and record.get("decision") in {"ACCEPTED", "REJECTED"}
        and _utc_time(record.get("recorded_at")) is not None
        and _nonempty_text(record.get("run_id"))
        and _nonempty_text(expected_run_id)
        and record.get("run_id") == expected_run_id
        and type(record.get("contract_id")) is str
        and SHA256_ID.fullmatch(record["contract_id"]) is not None
        and _nonempty_text(expected_contract_id)
        and SHA256_ID.fullmatch(expected_contract_id) is not None
        and type(record.get("candidate_id")) is str
        and SHA256_ID.fullmatch(record["candidate_id"]) is not None
        and _nonempty_text(expected_candidate_id)
        and SHA256_ID.fullmatch(expected_candidate_id) is not None
        and record.get("contract_id") == expected_contract_id
        and record.get("candidate_id") == expected_candidate_id
    )
    recorded_at = _utc_time(record.get("recorded_at")) if type(record) is dict else None
    try:
        normalized_now = (
            now.astimezone(UTC)
            if type(now) is datetime
            and now.tzinfo is not None
            and now.utcoffset() is not None
            else None
        )
    except Exception:
        normalized_now = None
    valid = valid and normalized_now is not None and recorded_at <= normalized_now
    if not valid:
        problems.append(
            issue(
                "invalid_human_acceptance",
                "human_acceptance",
                "human acceptance must be closed, human-authored, and identity-bound",
            )
        )


def _internal_test_gate_failed(
    bundle: dict[object, object], problems: _IssueCollector
) -> bool:
    inputs = (bundle.get("contract"), bundle.get("artifacts"), bundle.get("tests"))
    if not all(_exact_json_tree(value) for value in inputs):
        problems.append(
            issue(
                "test_gate_failed",
                "tests",
                "independent test validation did not pass",
            )
        )
        return True
    try:
        failed = bool(validate_tests(bundle))
    except Exception:
        failed = True
    if failed:
        problems.append(
            issue(
                "test_gate_failed",
                "tests",
                "independent test validation did not pass",
            )
        )
    return failed


def validate_verdict(
    bundle: object,
    *,
    identity_issues: list[ValidationIssue] | tuple[ValidationIssue, ...],
    artifact_issues: list[ValidationIssue] | tuple[ValidationIssue, ...],
    test_issues: list[ValidationIssue] | tuple[ValidationIssue, ...],
    trace_issues: list[ValidationIssue] | tuple[ValidationIssue, ...],
    now: datetime,
) -> list[ValidationIssue]:
    if type(bundle) is not dict:
        return [issue("invalid_bundle", "bundle", "bundle must be an object")]

    problems = _IssueCollector()
    identity_bad = _snapshot_gate(identity_issues, "identity_issues", problems)
    artifact_bad = _snapshot_gate(artifact_issues, "artifact_issues", problems)
    test_bad = _snapshot_gate(test_issues, "test_issues", problems)
    trace_bad = _snapshot_gate(trace_issues, "trace_issues", problems)

    bundle_limits_valid = _bundle_record_limits_valid(bundle, problems)
    required_claims, required_tests, contract_valid = _required_ids(bundle, problems)
    tests_valid = _validate_tests(bundle, required_tests, problems)
    claims_valid, statuses = _validate_claims(bundle, required_claims, problems)

    run = bundle.get("run")
    raw_run_status = run.get("status") if type(run) is dict else None
    run_valid = (
        _closed_record(run, {"status"})
        and type(raw_run_status) is str
        and raw_run_status in RUN_STATUSES
    )
    if not run_valid:
        problems.append(issue("invalid_run", "run", "run must have one closed terminal status"))
    run_status = raw_run_status if run_valid else None

    waiver_valid, has_waiver = _validate_waivers(
        bundle,
        {f"claim:{value}" for value in required_claims}
        | {f"test:{value}" for value in required_tests},
        now,
        problems,
    )
    _validate_acceptance(bundle, now, problems)
    internal_test_bad = _internal_test_gate_failed(bundle, problems)

    prerequisites_clear = not (
        identity_bad or artifact_bad or test_bad or trace_bad or internal_test_bad
    )
    # A valid waiver is separate evidence and only blocks READY below. An invalid
    # waiver makes evidence incomplete, so exact verdict precedence yields
    # INCONCLUSIVE before claim-based FAIL; neither case turns failure into success.
    evidence_complete = (
        contract_valid
        and bundle_limits_valid
        and tests_valid
        and claims_valid
        and run_valid
        and waiver_valid
        and not (artifact_bad or test_bad or trace_bad or internal_test_bad)
    )
    candidate_failed = claims_valid and any(
        statuses.get(claim_id) == "DISPROVEN" for claim_id in required_claims
    )
    all_obligations_proven = (
        run_status == "COMPLETED"
        and prerequisites_clear
        and contract_valid
        and bundle_limits_valid
        and tests_valid
        and claims_valid
        and bool(required_claims)
        and all(statuses.get(claim_id) == "PROVEN" for claim_id in required_claims)
        and not has_waiver
    )
    derived = derive_verdict(
        aborted=run_status == "ABORTED",
        environment_valid=not identity_bad,
        infra_blocked=run_status == "BLOCKED_INFRA",
        evidence_complete=evidence_complete,
        candidate_failed=candidate_failed,
        all_obligations_proven=all_obligations_proven,
    )
    verdict = bundle.get("verdict")
    claimed = verdict.get("status") if type(verdict) is dict else None
    verdict_valid = (
        _closed_record(verdict, {"status"})
        and type(claimed) is str
        and claimed in VERDICTS
    )
    if not verdict_valid:
        problems.append(issue("invalid_verdict", "verdict", "verdict must contain one closed status"))
    if claimed != derived:
        problems.append(
            issue(
                "verdict_mismatch",
                "verdict.status",
                f"verdict status must be derived as {derived}",
            )
        )
    return sorted(problems, key=lambda value: (value.location, value.code, value.message))
