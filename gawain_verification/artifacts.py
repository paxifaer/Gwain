from __future__ import annotations

import hashlib
import os
import re
import stat
from collections import Counter
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

from .issues import ValidationIssue, issue


SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
HASH_CHUNK_BYTES = 1024 * 1024


def resolve_artifact(
    root: Path, relative: str
) -> tuple[Path | None, ValidationIssue | None]:
    if not isinstance(relative, str) or not relative or "\\" in relative or "\0" in relative:
        return None, issue(
            "unsafe_artifact_path", "path", "artifact path must be a safe relative POSIX path"
        )

    path = PurePosixPath(relative)
    if (
        path.is_absolute()
        or path == PurePosixPath(".")
        or ".." in path.parts
        or str(path) != relative
    ):
        return None, issue(
            "unsafe_artifact_path", "path", "artifact path must be a safe relative POSIX path"
        )

    if not isinstance(root, Path):
        return None, issue(
            "artifact_path_escape", "path", "artifact root is unavailable"
        )
    try:
        resolved_root = root.resolve(strict=True)
        if not resolved_root.is_dir():
            raise NotADirectoryError(root)
        candidate = resolved_root.joinpath(*path.parts)
    except (OSError, RuntimeError):
        return None, issue(
            "artifact_path_escape", "path", "artifact path cannot be resolved under root"
        )

    try:
        resolved_candidate = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        try:
            tentative = candidate.resolve(strict=False)
        except (OSError, RuntimeError):
            tentative = None
        if tentative is not None and not tentative.is_relative_to(resolved_root):
            return None, issue(
                "artifact_path_escape", "path", "artifact path resolves outside root"
            )
        current = resolved_root
        for part in path.parts:
            current = current / part
            try:
                if stat.S_ISLNK(current.lstat().st_mode):
                    return None, issue(
                        "artifact_symlink",
                        "path",
                        "artifact path must not contain symlinks",
                    )
            except OSError:
                break
        return None, issue(
            "artifact_path_escape", "path", "artifact path cannot be resolved under root"
        )

    if not resolved_candidate.is_relative_to(resolved_root):
        return None, issue(
            "artifact_path_escape", "path", "artifact path resolves outside root"
        )

    current = resolved_root
    try:
        for part in path.parts:
            current = current / part
            if stat.S_ISLNK(current.lstat().st_mode):
                return None, issue(
                    "artifact_symlink", "path", "artifact path must not contain symlinks"
                )
        if not stat.S_ISREG(candidate.stat().st_mode):
            return None, issue(
                "artifact_not_regular", "path", "artifact must be a regular file"
            )
    except OSError:
        return None, issue(
            "artifact_path_escape", "path", "artifact path cannot be inspected under root"
        )

    return candidate, None


def _relocate(problem: ValidationIssue, location: str) -> ValidationIssue:
    return issue(problem.code, location, problem.message)


def _hash_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    byte_count = 0
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            while chunk := stream.read(HASH_CHUNK_BYTES):
                byte_count += len(chunk)
                digest.update(chunk)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    return byte_count, "sha256:" + digest.hexdigest()


def _evidence_issues(
    bundle: Mapping[object, object], known_ids: set[str]
) -> list[ValidationIssue]:
    problems: list[ValidationIssue] = []

    def validate_record(record: Mapping[object, object], location: str) -> None:
        evidence = record.get("evidence")
        evidence_location = f"{location}.evidence"
        if not isinstance(evidence, list) or not all(
            isinstance(reference, str) and bool(reference) for reference in evidence
        ):
            problems.append(
                issue(
                    "invalid_evidence",
                    evidence_location,
                    "evidence must be a list of non-empty artifact identifiers",
                )
            )
            return
        for index, reference in enumerate(evidence):
            if reference not in known_ids:
                problems.append(
                    issue(
                        "unknown_evidence_ref",
                        f"{evidence_location}[{index}]",
                        f"evidence references unknown artifact {reference!r}",
                    )
                )

    for section in ("tests", "claims", "traces"):
        records = bundle.get(section)
        if not isinstance(records, list):
            problems.append(
                issue(
                    "invalid_evidence_container",
                    section,
                    f"{section} must be a list",
                )
            )
            continue
        for index, record in enumerate(records):
            location = f"{section}[{index}]"
            if not isinstance(record, Mapping):
                problems.append(
                    issue(
                        "malformed_evidence_record",
                        location,
                        "evidence record must be an object",
                    )
                )
                continue
            validate_record(record, location)

    for section in ("environment", "deployment"):
        if section == "deployment" and section not in bundle:
            continue
        record = bundle.get(section)
        if not isinstance(record, Mapping):
            problems.append(
                issue(
                    "invalid_evidence_container",
                    section,
                    f"{section} must be an object",
                )
            )
            continue
        validate_record(record, section)

    return problems


def validate_artifacts(bundle: object, root: Path) -> list[ValidationIssue]:
    if not isinstance(bundle, Mapping):
        return [issue("invalid_bundle", "bundle", "bundle must be an object")]

    artifacts = bundle.get("artifacts")
    if not isinstance(artifacts, list):
        return [
            issue("invalid_artifacts", "artifacts", "artifacts must be a list")
        ]

    problems: list[ValidationIssue] = []
    id_counts = Counter(
        record.get("artifact_id")
        for record in artifacts
        if isinstance(record, Mapping)
        and isinstance(record.get("artifact_id"), str)
        and bool(record.get("artifact_id"))
    )
    known_ids: set[str] = set()

    for index, record in enumerate(artifacts):
        location = f"artifacts[{index}]"
        if not isinstance(record, Mapping):
            problems.append(
                issue(
                    "malformed_artifact",
                    location,
                    "artifact record must be an object",
                )
            )
            continue

        artifact_id = record.get("artifact_id")
        path_value = record.get("path")
        expected_bytes = record.get("bytes")
        expected_digest = record.get("sha256")

        valid_id = isinstance(artifact_id, str) and bool(artifact_id)
        if not valid_id:
            problems.append(
                issue(
                    "invalid_artifact_id",
                    f"{location}.artifact_id",
                    "artifact_id must be a non-empty string",
                )
            )
        elif id_counts[artifact_id] > 1:
            problems.append(
                issue(
                    "duplicate_artifact_id",
                    f"{location}.artifact_id",
                    f"artifact_id {artifact_id!r} is duplicated",
                )
            )

        valid_bytes = (
            isinstance(expected_bytes, int)
            and not isinstance(expected_bytes, bool)
            and expected_bytes >= 0
        )
        if not valid_bytes:
            problems.append(
                issue(
                    "invalid_artifact_bytes",
                    f"{location}.bytes",
                    "artifact bytes must be a non-negative integer",
                )
            )

        valid_digest = (
            isinstance(expected_digest, str)
            and SHA256_PATTERN.fullmatch(expected_digest) is not None
        )
        if not valid_digest:
            problems.append(
                issue(
                    "invalid_artifact_sha256",
                    f"{location}.sha256",
                    "artifact sha256 must be a lowercase sha256 digest",
                )
            )

        resolved, path_problem = resolve_artifact(root, path_value)
        if path_problem is not None:
            problems.append(_relocate(path_problem, f"{location}.path"))
        path_valid = resolved is not None and path_problem is None

        structurally_valid = (
            valid_id
            and id_counts[artifact_id] == 1
            and valid_bytes
            and valid_digest
            and path_valid
        )
        if not structurally_valid:
            continue

        known_ids.add(artifact_id)
        try:
            actual_bytes, actual_digest = _hash_file(resolved)
        except OSError:
            problems.append(
                issue(
                    "artifact_path_escape",
                    f"{location}.path",
                    "artifact could not be opened safely",
                )
            )
            known_ids.discard(artifact_id)
            continue
        if actual_bytes != expected_bytes:
            problems.append(
                issue(
                    "artifact_bytes_mismatch",
                    f"{location}.bytes",
                    "artifact byte count does not match manifest",
                )
            )
        if actual_digest != expected_digest:
            problems.append(
                issue(
                    "artifact_digest_mismatch",
                    f"{location}.sha256",
                    "artifact digest does not match manifest",
                )
            )

    problems.extend(_evidence_issues(bundle, known_ids))
    return sorted(problems)
