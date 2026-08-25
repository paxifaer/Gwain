"""Fail-closed verdict derivation for verifier-collected evidence."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
import re

from .issues import ValidationIssue, issue


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
    r"(?:\.[0-9]+)?(?:Z|\+00:00)$"
)
SHA256_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
MAX_EXTERNAL_ISSUES = 10_000


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


def _snapshot_issues(
    source: Iterable[ValidationIssue], name: str
) -> tuple[bool, list[ValidationIssue]]:
    problems: list[ValidationIssue] = []
    count = 0
    malformed = False
    try:
        iterator = iter(source)
        while count <= MAX_EXTERNAL_ISSUES:
            try:
                value = next(iterator)
            except StopIteration:
                break
            count += 1
            if not (
                type(value) is ValidationIssue
                and _nonempty_text(value.code)
                and _nonempty_text(value.location)
                and _nonempty_text(value.message)
            ):
                malformed = True
        else:
            malformed = True
    except Exception:
        malformed = True
    if count > MAX_EXTERNAL_ISSUES:
        malformed = True
    if malformed:
        problems.append(
            issue(
                f"invalid_{name}",
                name,
                f"{name} must be a bounded iterable of ValidationIssue values",
            )
        )
    return bool(count or malformed), problems


def _nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _utc_time(value: object) -> datetime | None:
    if not isinstance(value, str) or UTC_TIMESTAMP.fullmatch(value) is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        return None
    return parsed.astimezone(UTC)


def _required_ids(
    bundle: dict[object, object], problems: list[ValidationIssue]
) -> tuple[list[str], list[str], bool]:
    contract = bundle.get("contract")
    if type(contract) is not dict:
        problems.append(issue("invalid_contract", "contract", "contract must be an object"))
        return [], [], False

    claims_valid = True
    required_claims = contract.get("required_claims")
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
    bundle: dict[object, object], required: list[str], problems: list[ValidationIssue]
) -> bool:
    records = bundle.get("tests")
    if type(records) is not list:
        problems.append(issue("invalid_tests", "tests", "tests must be a list"))
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
            problems.append(issue("missing_test", "tests", f"required test {test_id!r} is missing"))
            structurally_valid = False
        elif counts[test_id] > 1:
            problems.append(issue("duplicate_test", "tests", f"required test {test_id!r} is duplicated"))
            structurally_valid = False
    for test_id in sorted(set(valid_ids) - required_set):
        problems.append(issue("unexpected_test", "tests", f"test {test_id!r} is not required"))
        structurally_valid = False
    return structurally_valid


def _validate_claims(
    bundle: dict[object, object], required: list[str], problems: list[ValidationIssue]
) -> tuple[bool, dict[str, str]]:
    records = bundle.get("claims")
    if type(records) is not list:
        problems.append(issue("invalid_claims", "claims", "claims must be a list"))
        return False, {}
    valid: list[tuple[str, str]] = []
    structurally_valid = True
    for index, record in enumerate(records):
        evidence = record.get("evidence") if type(record) is dict else None
        if not (
            type(record) is dict
            and set(record) == {"id", "status", "evidence"}
            and _nonempty_text(record.get("id"))
            and record.get("status") in CLAIM_STATUSES
            and type(evidence) is list
            and bool(evidence)
            and all(_nonempty_text(value) for value in evidence)
            and len(set(evidence)) == len(evidence)
        ):
            problems.append(
                issue(
                    "invalid_claim",
                    f"claims[{index}]",
                    "claim must have the closed authoritative shape",
                )
            )
            structurally_valid = False
            continue
        valid.append((record["id"], record["status"]))
    counts = Counter(claim_id for claim_id, _ in valid)
    required_set = set(required)
    for claim_id in required:
        if counts[claim_id] == 0:
            problems.append(issue("missing_claim", "claims", f"required claim {claim_id!r} is missing"))
            structurally_valid = False
        elif counts[claim_id] > 1:
            problems.append(issue("duplicate_claim", "claims", f"required claim {claim_id!r} is duplicated"))
            structurally_valid = False
    for claim_id in sorted(set(counts) - required_set):
        problems.append(issue("unexpected_claim", "claims", f"claim {claim_id!r} is not required"))
        structurally_valid = False
    statuses = {
        claim_id: status
        for claim_id, status in valid
        if counts[claim_id] == 1 and claim_id in required_set
    }
    return structurally_valid, statuses


def _validate_waivers(
    bundle: dict[object, object], scopes: set[str], now: object, problems: list[ValidationIssue]
) -> tuple[bool, bool]:
    if "waivers" not in bundle:
        return True, False
    records = bundle.get("waivers")
    if type(records) is not list:
        problems.append(issue("invalid_waiver", "waivers", "waivers must be a list"))
        return False, True
    structurally_valid = True
    expected_fields = {
        "author_kind", "author", "reason", "scope", "policy_version", "expires_at"
    }
    valid_now = isinstance(now, datetime) and now.tzinfo is not None
    normalized_now = now.astimezone(UTC) if valid_now else None
    for index, record in enumerate(records):
        location = f"waivers[{index}]"
        scope = record.get("scope") if type(record) is dict else None
        basic_valid = (
            type(record) is dict
            and set(record) == expected_fields
            and record.get("author_kind") == "human"
            and _nonempty_text(record.get("author"))
            and _nonempty_text(record.get("reason"))
            and record.get("policy_version") == "gawain.waiver-policy.v1"
            and type(scope) is list
            and bool(scope)
            and all(_nonempty_text(value) for value in scope)
            and len(set(scope)) == len(scope)
        )
        if not basic_valid:
            problems.append(issue("invalid_waiver", location, "waiver must have the closed human-authored shape"))
            structurally_valid = False
            continue
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
    bundle: dict[object, object], problems: list[ValidationIssue]
) -> None:
    if "human_acceptance" not in bundle:
        return
    record = bundle.get("human_acceptance")
    contract = bundle.get("contract")
    candidate = bundle.get("candidate")
    expected_fields = {
        "author_kind", "author", "reason", "decision", "recorded_at",
        "contract_id", "candidate_id",
    }
    valid = (
        type(record) is dict
        and set(record) == expected_fields
        and record.get("author_kind") == "human"
        and _nonempty_text(record.get("author"))
        and _nonempty_text(record.get("reason"))
        and record.get("decision") in {"ACCEPTED", "REJECTED"}
        and _utc_time(record.get("recorded_at")) is not None
        and isinstance(record.get("contract_id"), str)
        and SHA256_ID.fullmatch(record["contract_id"]) is not None
        and isinstance(record.get("candidate_id"), str)
        and SHA256_ID.fullmatch(record["candidate_id"]) is not None
        and type(contract) is dict
        and record.get("contract_id") == contract.get("contract_id")
        and type(candidate) is dict
        and record.get("candidate_id") == candidate.get("candidate_id")
    )
    if not valid:
        problems.append(
            issue(
                "invalid_human_acceptance",
                "human_acceptance",
                "human acceptance must be closed, human-authored, and identity-bound",
            )
        )


def validate_verdict(
    bundle: object,
    *,
    identity_issues: Iterable[ValidationIssue] = (),
    artifact_issues: Iterable[ValidationIssue] = (),
    test_issues: Iterable[ValidationIssue] = (),
    trace_issues: Iterable[ValidationIssue] = (),
    now: datetime,
) -> list[ValidationIssue]:
    if type(bundle) is not dict:
        return [issue("invalid_bundle", "bundle", "bundle must be an object")]

    problems: list[ValidationIssue] = []
    identity_bad, found = _snapshot_issues(identity_issues, "identity_issues")
    problems.extend(found)
    artifact_bad, found = _snapshot_issues(artifact_issues, "artifact_issues")
    problems.extend(found)
    test_bad, found = _snapshot_issues(test_issues, "test_issues")
    problems.extend(found)
    trace_bad, found = _snapshot_issues(trace_issues, "trace_issues")
    problems.extend(found)

    required_claims, required_tests, contract_valid = _required_ids(bundle, problems)
    tests_valid = _validate_tests(bundle, required_tests, problems)
    claims_valid, statuses = _validate_claims(bundle, required_claims, problems)

    run = bundle.get("run")
    run_valid = type(run) is dict and set(run) == {"status"} and run.get("status") in RUN_STATUSES
    if not run_valid:
        problems.append(issue("invalid_run", "run", "run must have one closed terminal status"))
    run_status = run.get("status") if run_valid else None

    waiver_valid, has_waiver = _validate_waivers(
        bundle, set(required_claims) | set(required_tests), now, problems
    )
    _validate_acceptance(bundle, problems)

    verdict = bundle.get("verdict")
    verdict_valid = (
        type(verdict) is dict
        and set(verdict) == {"status"}
        and verdict.get("status") in VERDICTS
    )
    if not verdict_valid:
        problems.append(issue("invalid_verdict", "verdict", "verdict must contain one closed status"))

    prerequisites_clear = not (identity_bad or artifact_bad or test_bad or trace_bad)
    # A valid waiver is separate evidence and only blocks READY below. An invalid
    # waiver makes evidence incomplete, so exact verdict precedence yields
    # INCONCLUSIVE before claim-based FAIL; neither case turns failure into success.
    evidence_complete = (
        contract_valid
        and tests_valid
        and claims_valid
        and run_valid
        and waiver_valid
        and verdict_valid
        and not (artifact_bad or test_bad or trace_bad)
    )
    candidate_failed = claims_valid and any(
        statuses.get(claim_id) == "DISPROVEN" for claim_id in required_claims
    )
    all_obligations_proven = (
        run_status == "COMPLETED"
        and prerequisites_clear
        and contract_valid
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
    claimed = verdict.get("status") if type(verdict) is dict else None
    if claimed != derived:
        problems.append(
            issue(
                "verdict_mismatch",
                "verdict.status",
                f"verdict status must be derived as {derived}",
            )
        )
    return sorted(problems, key=lambda value: (value.location, value.code, value.message))
