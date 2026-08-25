from __future__ import annotations

import re
from collections.abc import Mapping

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
