from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Iterable

from .canonical import content_id
from .issues import ValidationIssue, issue


COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

COMPONENT_PATTERNS = {
    "base_commit": COMMIT_PATTERN,
    "head_commit": COMMIT_PATTERN,
    "tree_hash": DIGEST_PATTERN,
    "diff_hash": DIGEST_PATTERN,
    "build_recipe_id": SHA256_PATTERN,
    "build_artifact_sha256": SHA256_PATTERN,
}


def validate_candidate(candidate: object) -> list[ValidationIssue]:
    problems: list[ValidationIssue] = []
    if not isinstance(candidate, Mapping):
        return [
            issue(
                "invalid_candidate",
                "candidate",
                "candidate must be an object",
            )
        ]

    components = candidate.get("components")
    if not isinstance(components, list):
        return [
            issue(
                "invalid_components",
                "candidate.components",
                "candidate components must be a list",
            )
        ]
    if not components:
        return [
            issue(
                "missing_components",
                "candidate.components",
                "candidate must contain at least one component",
            )
        ]

    for index, component in enumerate(components):
        if not isinstance(component, Mapping):
            problems.append(
                issue(
                    "invalid_component",
                    f"candidate.components[{index}]",
                    "candidate component must be an object",
                )
            )
            continue

        name = component.get("name")
        if not isinstance(name, str) or not name:
            problems.append(
                issue(
                    "invalid_component_name",
                    f"candidate.components[{index}].name",
                    "component name must be a non-empty string",
                )
            )

    if problems:
        return problems

    seen_names: set[str] = set()
    for index, component in enumerate(components):
        name = component.get("name")
        if name in seen_names:
            problems.append(
                issue(
                    "duplicate_component",
                    f"candidate.components[{index}].name",
                    f"component name {name!r} is duplicated",
                )
            )
        seen_names.add(name)

        for field, pattern in COMPONENT_PATTERNS.items():
            value = component.get(field)
            if not isinstance(value, str) or pattern.fullmatch(value) is None:
                problems.append(
                    issue(
                        f"invalid_{field}",
                        f"candidate.components[{index}].{field}",
                        f"{field} has an invalid format",
                    )
                )

    if candidate.get("candidate_id") != content_id("candidate", candidate):
        problems.append(
            issue(
                "candidate_id_mismatch",
                "candidate.candidate_id",
                "candidate_id does not match candidate content",
            )
        )

    return problems


def _content_identity_issue(
    kind: str, value: Mapping[object, object]
) -> ValidationIssue | None:
    identity_field = f"{kind}_id"
    try:
        expected = content_id(kind, dict(value))
    except (KeyError, TypeError, ValueError):
        return issue(
            f"invalid_{kind}",
            kind,
            f"{kind} content cannot be canonicalized",
        )
    if value.get(identity_field) != expected:
        return issue(
            f"{kind}_id_mismatch",
            f"{kind}.{identity_field}",
            f"{identity_field} does not match {kind} content",
        )
    return None


def _utc_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        return None
    return parsed.astimezone(UTC)


def _string_array(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and bool(item) for item in value)
    )


def _installed_component_issues(
    candidate: Mapping[object, object], environment: Mapping[object, object]
) -> list[ValidationIssue]:
    problems: list[ValidationIssue] = []
    candidate_components = candidate.get("components")
    expected: dict[str, str] = {}
    if isinstance(candidate_components, list):
        for component in candidate_components:
            if not isinstance(component, Mapping):
                continue
            name = component.get("name")
            digest = component.get("build_artifact_sha256")
            if isinstance(name, str) and name and isinstance(digest, str):
                expected[name] = digest

    installed_components = environment.get("installed_components")
    if not isinstance(installed_components, list):
        return [
            issue(
                "invalid_installed_components",
                "environment.installed_components",
                "installed_components must be a list",
            )
        ]

    installed: dict[str, str] = {}
    for index, component in enumerate(installed_components):
        location = f"environment.installed_components[{index}]"
        if not isinstance(component, Mapping):
            problems.append(
                issue(
                    "malformed_installed_component",
                    location,
                    "installed component must be an object",
                )
            )
            continue
        name = component.get("name")
        digest = component.get("sha256")
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(digest, str)
            or SHA256_PATTERN.fullmatch(digest) is None
        ):
            problems.append(
                issue(
                    "malformed_installed_component",
                    location,
                    "installed component requires a non-empty name and sha256 digest",
                )
            )
            continue
        if name in installed:
            problems.append(
                issue(
                    "duplicate_installed_component",
                    f"{location}.name",
                    f"installed component name {name!r} is duplicated",
                )
            )
            continue
        installed[name] = digest
        if name not in expected:
            problems.append(
                issue(
                    "extra_installed_component",
                    f"{location}.name",
                    f"installed component {name!r} is not in the candidate",
                )
            )

    for name, expected_digest in expected.items():
        if name not in installed:
            problems.append(
                issue(
                    "missing_installed_component",
                    "environment.installed_components",
                    f"candidate component {name!r} is not installed",
                )
            )
        elif installed[name] != expected_digest:
            problems.append(
                issue(
                    "installed_digest_mismatch",
                    f"environment.installed_components.{name}.sha256",
                    f"installed digest for {name!r} does not match candidate",
                )
            )
    return problems


def validate_identity_gate(
    contract: object,
    candidate: object,
    permit: object,
    environment: object,
    *,
    now: datetime,
    software_gate_violations: Iterable[ValidationIssue] = (),
) -> list[ValidationIssue]:
    problems: list[ValidationIssue] = []

    if not isinstance(contract, Mapping):
        problems.append(issue("invalid_contract", "contract", "contract must be an object"))
    else:
        identity_problem = _content_identity_issue("contract", contract)
        if identity_problem is not None:
            problems.append(identity_problem)

    try:
        problems.extend(validate_candidate(candidate))
    except (KeyError, TypeError, ValueError):
        problems.append(
            issue("invalid_candidate", "candidate", "candidate is malformed")
        )

    permit_valid = isinstance(permit, Mapping)
    if permit is None:
        problems.append(issue("missing_permit", "permit", "permit is required"))
    elif not permit_valid:
        problems.append(issue("invalid_permit", "permit", "permit must be an object"))

    if permit_valid:
        identity_problem = _content_identity_issue("permit", permit)
        if identity_problem is not None:
            problems.append(identity_problem)

        if permit.get("schema_version") != "gawain.execution-permit.v1":
            problems.append(
                issue(
                    "invalid_permit_schema_version",
                    "permit.schema_version",
                    "permit schema_version must be gawain.execution-permit.v1",
                )
            )

        if permit.get("issuer_kind") != "human":
            problems.append(
                issue(
                    "invalid_permit_issuer_kind",
                    "permit.issuer_kind",
                    "permit issuer_kind must be human",
                )
            )
        issuer = permit.get("issuer")
        if not isinstance(issuer, str) or not issuer:
            problems.append(
                issue(
                    "invalid_permit_issuer",
                    "permit.issuer",
                    "permit issuer must be a non-empty string",
                )
            )

        not_before = _utc_time(permit.get("not_before"))
        not_after = _utc_time(permit.get("not_after"))
        now_utc = _utc_time(now.isoformat()) if isinstance(now, datetime) else None
        if not_before is None or not_after is None or now_utc is None:
            problems.append(
                issue(
                    "permit_invalid_time",
                    "permit",
                    "permit times and now must be aware UTC ISO-8601 values",
                )
            )
        elif not_before > not_after:
            problems.append(
                issue(
                    "permit_invalid_window",
                    "permit",
                    "permit not_before must not be after not_after",
                )
            )
        elif now_utc < not_before:
            problems.append(
                issue(
                    "permit_not_yet_valid",
                    "permit.not_before",
                    "permit is not yet valid",
                )
            )
        elif now_utc > not_after:
            problems.append(
                issue("permit_expired", "permit.not_after", "permit has expired")
            )

        authorizations = (
            ("device_ids", "device_id", "device_not_authorized"),
            ("service_ids", "service_id", "service_not_authorized"),
            ("actions", "action", "action_not_authorized"),
        )
        for permit_field, contract_field, denied_code in authorizations:
            authorized = permit.get(permit_field)
            if not _string_array(authorized):
                problems.append(
                    issue(
                        f"invalid_permit_{permit_field}",
                        f"permit.{permit_field}",
                        f"{permit_field} must be an array of non-empty strings",
                    )
                )
            elif isinstance(contract, Mapping) and contract.get(contract_field) not in authorized:
                problems.append(
                    issue(
                        denied_code,
                        f"permit.{permit_field}",
                        f"contract {contract_field} is not authorized",
                    )
                )

        full_access = permit.get("full_access")
        if not isinstance(full_access, bool):
            problems.append(
                issue(
                    "invalid_full_access",
                    "permit.full_access",
                    "full_access must be a boolean",
                )
            )
        elif not full_access:
            problems.extend(software_gate_violations)

    if not isinstance(environment, Mapping):
        problems.append(
            issue("invalid_environment", "environment", "environment must be an object")
        )
    else:
        if isinstance(contract, Mapping):
            if environment.get("device_id") != contract.get("device_id"):
                problems.append(
                    issue(
                        "device_identity_mismatch",
                        "environment.device_id",
                        "environment device_id does not match contract",
                    )
                )
            if environment.get("gateway_endpoint") != contract.get("gateway_endpoint"):
                problems.append(
                    issue(
                        "gateway_endpoint_mismatch",
                        "environment.gateway_endpoint",
                        "environment gateway_endpoint does not match contract",
                    )
                )
        host_identity = environment.get("host_identity")
        if not isinstance(host_identity, str) or not host_identity:
            problems.append(
                issue(
                    "missing_host_identity",
                    "environment.host_identity",
                    "an independently verifiable host identity is required",
                )
            )
        if isinstance(candidate, Mapping):
            problems.extend(_installed_component_issues(candidate, environment))

    return sorted(problems, key=lambda problem: (problem.location, problem.code, problem.message))
