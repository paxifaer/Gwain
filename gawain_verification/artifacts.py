from __future__ import annotations

import hashlib
import os
import re
import stat
from collections import Counter
from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Iterator

from .issues import ValidationIssue, issue


SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
HASH_CHUNK_BYTES = 1024 * 1024
_OS_OPEN_SUPPORTS_DIR_FD = os.open in getattr(os, "supports_dir_fd", ())


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


class _ArtifactNotRegularError(Exception):
    pass


class _ArtifactChangedDuringReadError(Exception):
    pass


def _descriptor_traversal_supported() -> bool:
    required_flags = (
        getattr(os, "O_NOFOLLOW", 0),
        getattr(os, "O_DIRECTORY", 0),
        getattr(os, "O_CLOEXEC", 0),
        getattr(os, "O_NONBLOCK", 0),
    )
    return all(required_flags) and _OS_OPEN_SUPPORTS_DIR_FD


@contextmanager
def _bundle_root_descriptor(root: Path) -> Iterator[int | None]:
    if not isinstance(root, Path):
        yield None
        return
    try:
        resolved_root = root.resolve(strict=True)
        flags = (
            os.O_RDONLY
            | os.O_DIRECTORY
            | os.O_CLOEXEC
            | os.O_NOFOLLOW
        )
        descriptor = os.open(resolved_root, flags)
    except (OSError, RuntimeError):
        yield None
        return
    try:
        yield descriptor
    finally:
        os.close(descriptor)


def _hash_file(root_descriptor: int, relative: PurePosixPath) -> tuple[int, str]:
    digest = hashlib.sha256()
    byte_count = 0
    directory_descriptor = root_descriptor
    owns_directory_descriptor = False
    file_descriptor = -1
    try:
        directory_flags = (
            os.O_RDONLY
            | os.O_DIRECTORY
            | os.O_CLOEXEC
            | os.O_NOFOLLOW
        )
        for part in relative.parts[:-1]:
            next_descriptor = os.open(
                part, directory_flags, dir_fd=directory_descriptor
            )
            if owns_directory_descriptor:
                os.close(directory_descriptor)
            directory_descriptor = next_descriptor
            owns_directory_descriptor = True

        file_flags = (
            os.O_RDONLY
            | os.O_CLOEXEC
            | os.O_NOFOLLOW
            | os.O_NONBLOCK
        )
        file_descriptor = os.open(
            relative.parts[-1], file_flags, dir_fd=directory_descriptor
        )
        stat_before = os.fstat(file_descriptor)
        if not stat.S_ISREG(stat_before.st_mode):
            raise _ArtifactNotRegularError

        while chunk := os.read(file_descriptor, HASH_CHUNK_BYTES):
            byte_count += len(chunk)
            digest.update(chunk)
        stat_after = os.fstat(file_descriptor)
        stable_fields = (
            "st_dev",
            "st_ino",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
        if any(
            getattr(stat_before, field) != getattr(stat_after, field)
            for field in stable_fields
        ):
            raise _ArtifactChangedDuringReadError
    finally:
        if file_descriptor >= 0:
            os.close(file_descriptor)
        if owns_directory_descriptor:
            os.close(directory_descriptor)
    return byte_count, "sha256:" + digest.hexdigest()


def _evidence_issues(
    bundle: Mapping[object, object],
    declared_ids: set[str],
    verified_ids: set[str],
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
            if reference in verified_ids:
                continue
            if reference not in declared_ids:
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

    platform_supported = _descriptor_traversal_supported()
    if not platform_supported:
        return _validate_artifact_records(
            bundle, root, artifacts, None, platform_supported=False
        )

    with _bundle_root_descriptor(root) as root_descriptor:
        return _validate_artifact_records(
            bundle, root, artifacts, root_descriptor, platform_supported=True
        )


def _validate_artifact_records(
    bundle: Mapping[object, object],
    root: Path,
    artifacts: list[object],
    root_descriptor: int | None,
    *,
    platform_supported: bool,
) -> list[ValidationIssue]:
    problems: list[ValidationIssue] = []
    id_counts = Counter(
        record.get("artifact_id")
        for record in artifacts
        if isinstance(record, Mapping)
        and isinstance(record.get("artifact_id"), str)
        and bool(record.get("artifact_id"))
    )
    declared_ids = set(id_counts)
    verified_ids: set[str] = set()

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

        # The resolved Path is diagnostic only. Trusted reads use the opened
        # root and component descriptors below, never this pathname.
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

        if not platform_supported:
            problems.append(
                issue(
                    "artifact_platform_unsupported",
                    f"{location}.path",
                    "safe descriptor-relative artifact reads are unsupported",
                )
            )
            continue
        if root_descriptor is None:
            problems.append(
                issue(
                    "artifact_path_escape",
                    f"{location}.path",
                    "artifact root could not be opened safely",
                )
            )
            continue
        try:
            actual_bytes, actual_digest = _hash_file(
                root_descriptor, PurePosixPath(path_value)
            )
        except _ArtifactNotRegularError:
            problems.append(
                issue(
                    "artifact_not_regular",
                    f"{location}.path",
                    "artifact must be a regular file",
                )
            )
            continue
        except _ArtifactChangedDuringReadError:
            problems.append(
                issue(
                    "artifact_changed_during_read",
                    f"{location}.path",
                    "artifact changed while it was being read",
                )
            )
            continue
        except NotImplementedError:
            problems.append(
                issue(
                    "artifact_platform_unsupported",
                    f"{location}.path",
                    "safe descriptor-relative artifact reads are unsupported",
                )
            )
            continue
        except OSError:
            problems.append(
                issue(
                    "artifact_path_escape",
                    f"{location}.path",
                    "artifact could not be opened safely",
                )
            )
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
        if actual_bytes == expected_bytes and actual_digest == expected_digest:
            verified_ids.add(artifact_id)

    problems.extend(_evidence_issues(bundle, declared_ids, verified_ids))
    return sorted(problems)
