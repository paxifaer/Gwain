import hashlib
import os
import signal
import time
from pathlib import Path

import pytest

import gawain_verification.artifacts as artifact_module
from gawain_verification.artifacts import resolve_artifact, validate_artifacts
from gawain_verification.schema import validate_schema


def issue_codes(bundle, root):
    return [problem.code for problem in validate_artifacts(bundle, root)]


def test_valid_artifact_bundle_has_no_issues(valid_artifact_bundle, tmp_path):
    assert validate_artifacts(valid_artifact_bundle, tmp_path) == []


@pytest.mark.parametrize("relative", ["/etc/passwd", "", ".", "..", "a/../b"])
def test_resolve_artifact_rejects_unsafe_paths(tmp_path, relative):
    resolved, problem = resolve_artifact(tmp_path, relative)

    assert resolved is None
    assert problem is not None and problem.code == "unsafe_artifact_path"


@pytest.mark.parametrize("relative", [None, 7, [], "a\\b", "//host/share"])
def test_resolve_artifact_fails_closed_for_malformed_paths(tmp_path, relative):
    resolved, problem = resolve_artifact(tmp_path, relative)

    assert resolved is None
    assert problem is not None and problem.code == "unsafe_artifact_path"


@pytest.mark.parametrize("root", [None, "not-a-path", Path("missing-root")])
def test_resolve_artifact_fails_closed_for_malformed_roots(root):
    resolved, problem = resolve_artifact(root, "artifact.json")

    assert resolved is None
    assert problem is not None and problem.code == "artifact_path_escape"


def test_missing_artifact_is_rejected_as_path_escape(valid_artifact_bundle, tmp_path):
    (tmp_path / "artifacts" / "evidence.json").unlink()

    assert "artifact_path_escape" in issue_codes(valid_artifact_bundle, tmp_path)


def test_final_symlink_is_rejected(valid_artifact_bundle, tmp_path):
    artifact = tmp_path / "artifacts" / "evidence.json"
    target = tmp_path / "target.json"
    target.write_bytes(artifact.read_bytes())
    artifact.unlink()
    artifact.symlink_to(target)

    assert "artifact_symlink" in issue_codes(valid_artifact_bundle, tmp_path)


def test_broken_final_symlink_is_rejected_as_symlink(
    valid_artifact_bundle, tmp_path
):
    artifact = tmp_path / "artifacts" / "evidence.json"
    artifact.unlink()
    artifact.symlink_to(tmp_path / "missing-target.json")

    assert "artifact_symlink" in issue_codes(valid_artifact_bundle, tmp_path)


def test_escaping_symlink_is_rejected_as_escape(valid_artifact_bundle, tmp_path):
    artifact = tmp_path / "artifacts" / "evidence.json"
    outside = tmp_path.parent / f"{tmp_path.name}-outside.json"
    outside.write_bytes(artifact.read_bytes())
    artifact.unlink()
    artifact.symlink_to(outside)

    assert "artifact_path_escape" in issue_codes(valid_artifact_bundle, tmp_path)


def test_parent_directory_symlink_escape_is_rejected(valid_artifact_bundle, tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (outside / "evidence.json").write_bytes(
        (tmp_path / "artifacts" / "evidence.json").read_bytes()
    )
    (tmp_path / "artifacts" / "evidence.json").unlink()
    (tmp_path / "artifacts").rmdir()
    (tmp_path / "artifacts").symlink_to(outside, target_is_directory=True)

    assert "artifact_path_escape" in issue_codes(valid_artifact_bundle, tmp_path)


def test_internal_parent_directory_symlink_is_rejected(valid_artifact_bundle, tmp_path):
    actual = tmp_path / "actual"
    actual.mkdir()
    (actual / "evidence.json").write_bytes(
        (tmp_path / "artifacts" / "evidence.json").read_bytes()
    )
    (tmp_path / "artifacts" / "evidence.json").unlink()
    (tmp_path / "artifacts").rmdir()
    (tmp_path / "artifacts").symlink_to(actual, target_is_directory=True)

    assert "artifact_symlink" in issue_codes(valid_artifact_bundle, tmp_path)


def test_parent_swap_at_final_open_cannot_redirect_validation_to_replacement(
    valid_artifact_bundle, tmp_path, monkeypatch
):
    artifact = tmp_path / "artifacts" / "evidence.json"
    manifest_content = artifact.read_bytes()
    artifact.write_bytes(b"x" * len(manifest_content))
    moved_parent = tmp_path / "checked-artifacts"
    original_open = os.open
    swapped = False

    def swap_parent_then_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal swapped
        is_old_final_open = dir_fd is None and Path(path) == artifact
        is_fd_relative_final_open = dir_fd is not None and path == "evidence.json"
        if not swapped and (is_old_final_open or is_fd_relative_final_open):
            artifact.parent.rename(moved_parent)
            artifact.parent.mkdir()
            artifact.write_bytes(manifest_content)
            swapped = True
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(artifact_module.os, "open", swap_parent_then_open)

    issues = validate_artifacts(valid_artifact_bundle, tmp_path)

    assert swapped
    assert "artifact_digest_mismatch" in [problem.code for problem in issues]


def test_multilevel_parent_swap_stays_attached_to_checked_hierarchy(
    valid_artifact_bundle, tmp_path, monkeypatch
):
    original_artifact = tmp_path / "artifacts" / "evidence.json"
    manifest_content = original_artifact.read_bytes()
    nested_parent = tmp_path / "artifacts" / "first" / "second"
    nested_parent.mkdir(parents=True)
    artifact = nested_parent / "evidence.json"
    original_artifact.replace(artifact)
    artifact.write_bytes(b"x" * len(manifest_content))
    valid_artifact_bundle["artifacts"][0]["path"] = (
        "artifacts/first/second/evidence.json"
    )
    moved_parent = nested_parent.with_name("checked-second")
    original_open = os.open
    swapped = False

    def swap_parent_then_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal swapped
        if not swapped and dir_fd is not None and path == "evidence.json":
            nested_parent.rename(moved_parent)
            nested_parent.mkdir()
            artifact.write_bytes(manifest_content)
            swapped = True
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(artifact_module.os, "open", swap_parent_then_open)

    issues = validate_artifacts(valid_artifact_bundle, tmp_path)

    assert swapped
    assert "artifact_digest_mismatch" in [problem.code for problem in issues]


def test_final_entry_changed_to_fifo_is_rejected_without_blocking(
    valid_artifact_bundle, tmp_path, monkeypatch
):
    artifact = tmp_path / "artifacts" / "evidence.json"
    original_open = os.open
    swapped = False

    def replace_with_fifo_then_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal swapped
        if not swapped and dir_fd is not None and path == "evidence.json":
            artifact.unlink()
            os.mkfifo(artifact)
            swapped = True
        return original_open(path, flags, mode, dir_fd=dir_fd)

    def deadline_expired(signum, frame):
        raise TimeoutError("final FIFO open blocked")

    monkeypatch.setattr(artifact_module.os, "open", replace_with_fifo_then_open)
    previous_handler = signal.signal(signal.SIGALRM, deadline_expired)
    started = time.monotonic()
    signal.alarm(2)
    try:
        issues = validate_artifacts(valid_artifact_bundle, tmp_path)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)

    assert swapped
    assert time.monotonic() - started < 2
    assert "artifact_not_regular" in [problem.code for problem in issues]


def test_missing_descriptor_capabilities_fail_closed(
    valid_artifact_bundle, tmp_path, monkeypatch
):
    monkeypatch.setattr(
        artifact_module,
        "_descriptor_traversal_supported",
        lambda: False,
        raising=False,
    )

    assert "artifact_platform_unsupported" in issue_codes(
        valid_artifact_bundle, tmp_path
    )


def test_unimplemented_descriptor_relative_open_fails_closed(
    valid_artifact_bundle, tmp_path, monkeypatch
):
    original_open = os.open

    def reject_dir_fd(path, flags, mode=0o777, *, dir_fd=None):
        if dir_fd is not None:
            raise NotImplementedError("dir_fd unavailable")
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(artifact_module.os, "open", reject_dir_fd)

    assert "artifact_platform_unsupported" in issue_codes(
        valid_artifact_bundle, tmp_path
    )


def test_large_artifact_is_hashed_in_multiple_chunks(
    valid_artifact_bundle, tmp_path, monkeypatch
):
    artifact = tmp_path / "artifacts" / "evidence.json"
    content = b"a" * (artifact_module.HASH_CHUNK_BYTES + 37)
    artifact.write_bytes(content)
    valid_artifact_bundle["artifacts"][0]["bytes"] = len(content)
    valid_artifact_bundle["artifacts"][0]["sha256"] = (
        "sha256:" + hashlib.sha256(content).hexdigest()
    )
    original_read = os.read
    read_calls = 0

    def count_reads(descriptor, count):
        nonlocal read_calls
        chunk = original_read(descriptor, count)
        if chunk:
            read_calls += 1
        return chunk

    monkeypatch.setattr(artifact_module.os, "read", count_reads)

    assert validate_artifacts(valid_artifact_bundle, tmp_path) == []
    assert read_calls >= 2


def test_same_size_change_during_chunked_hashing_is_rejected(
    valid_artifact_bundle, tmp_path, monkeypatch
):
    artifact = tmp_path / "artifacts" / "evidence.json"
    content = b"a" * (artifact_module.HASH_CHUNK_BYTES + 37)
    artifact.write_bytes(content)
    valid_artifact_bundle["artifacts"][0]["bytes"] = len(content)
    valid_artifact_bundle["artifacts"][0]["sha256"] = (
        "sha256:" + hashlib.sha256(content).hexdigest()
    )
    original_read = os.read
    changed = False

    def change_after_first_chunk(descriptor, count):
        nonlocal changed
        chunk = original_read(descriptor, count)
        if chunk and not changed:
            previous = artifact.stat()
            artifact.write_bytes(b"b" * len(content))
            os.utime(
                artifact,
                ns=(previous.st_atime_ns, previous.st_mtime_ns + 1_000_000_000),
            )
            changed = True
        return chunk

    monkeypatch.setattr(artifact_module.os, "read", change_after_first_chunk)

    issues = validate_artifacts(valid_artifact_bundle, tmp_path)

    assert changed
    assert "artifact_changed_during_read" in [problem.code for problem in issues]


def test_intermediate_open_failure_does_not_leak_descriptors(
    valid_artifact_bundle, tmp_path, monkeypatch
):
    proc_fds = Path("/proc/self/fd")
    if not proc_fds.is_dir():
        pytest.skip("descriptor accounting requires procfs")
    original_artifact = tmp_path / "artifacts" / "evidence.json"
    nested_parent = tmp_path / "artifacts" / "first" / "second"
    nested_parent.mkdir(parents=True)
    artifact = nested_parent / "evidence.json"
    original_artifact.replace(artifact)
    valid_artifact_bundle["artifacts"][0]["path"] = (
        "artifacts/first/second/evidence.json"
    )
    original_open = os.open

    def fail_second_parent(path, flags, mode=0o777, *, dir_fd=None):
        if dir_fd is not None and path == "second":
            raise OSError("injected intermediate open failure")
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(artifact_module.os, "open", fail_second_parent)
    before = len(list(proc_fds.iterdir()))

    issues = validate_artifacts(valid_artifact_bundle, tmp_path)

    after = len(list(proc_fds.iterdir()))
    assert "artifact_path_escape" in [problem.code for problem in issues]
    assert after == before


def test_directory_artifact_is_rejected(valid_artifact_bundle, tmp_path):
    artifact = tmp_path / "artifacts" / "evidence.json"
    artifact.unlink()
    artifact.mkdir()

    assert "artifact_not_regular" in issue_codes(valid_artifact_bundle, tmp_path)


def test_fifo_artifact_is_rejected(valid_artifact_bundle, tmp_path):
    artifact = tmp_path / "artifacts" / "evidence.json"
    artifact.unlink()
    os.mkfifo(artifact)

    assert "artifact_not_regular" in issue_codes(valid_artifact_bundle, tmp_path)


def test_duplicate_artifact_id_is_rejected(valid_artifact_bundle, tmp_path, cloned):
    valid_artifact_bundle["artifacts"].append(
        cloned(valid_artifact_bundle["artifacts"][0])
    )

    assert "duplicate_artifact_id" in issue_codes(valid_artifact_bundle, tmp_path)


def test_invalid_declared_artifact_does_not_add_unknown_evidence_diagnostic(
    valid_artifact_bundle, tmp_path
):
    valid_artifact_bundle["artifacts"][0]["bytes"] = -1

    codes = issue_codes(valid_artifact_bundle, tmp_path)

    assert "invalid_artifact_bytes" in codes
    assert "unknown_evidence_ref" not in codes


def test_duplicate_declared_artifact_does_not_add_unknown_evidence_diagnostic(
    valid_artifact_bundle, tmp_path, cloned
):
    valid_artifact_bundle["artifacts"].append(
        cloned(valid_artifact_bundle["artifacts"][0])
    )

    codes = issue_codes(valid_artifact_bundle, tmp_path)

    assert "duplicate_artifact_id" in codes
    assert "unknown_evidence_ref" not in codes


@pytest.mark.parametrize("artifact_id", [None, "", 7, [], True])
def test_malformed_artifact_id_is_rejected(
    valid_artifact_bundle, tmp_path, artifact_id
):
    valid_artifact_bundle["artifacts"][0]["artifact_id"] = artifact_id

    assert "invalid_artifact_id" in issue_codes(valid_artifact_bundle, tmp_path)


@pytest.mark.parametrize("artifacts", [None, {}, "artifact"])
def test_artifacts_must_be_a_list(valid_artifact_bundle, tmp_path, artifacts):
    valid_artifact_bundle["artifacts"] = artifacts

    assert issue_codes(valid_artifact_bundle, tmp_path) == ["invalid_artifacts"]


@pytest.mark.parametrize("record", [None, "artifact", [], 7])
def test_malformed_artifact_record_is_rejected(
    valid_artifact_bundle, tmp_path, record
):
    valid_artifact_bundle["artifacts"][0] = record

    assert "malformed_artifact" in issue_codes(valid_artifact_bundle, tmp_path)


@pytest.mark.parametrize("byte_count", [-1, 1.5, "23", True, None])
def test_invalid_artifact_bytes_are_rejected(
    valid_artifact_bundle, tmp_path, byte_count
):
    valid_artifact_bundle["artifacts"][0]["bytes"] = byte_count

    assert "invalid_artifact_bytes" in issue_codes(valid_artifact_bundle, tmp_path)


def test_artifact_byte_count_must_match(valid_artifact_bundle, tmp_path):
    valid_artifact_bundle["artifacts"][0]["bytes"] += 1

    assert "artifact_bytes_mismatch" in issue_codes(valid_artifact_bundle, tmp_path)


@pytest.mark.parametrize(
    "digest",
    [None, "", "0" * 64, "sha256:" + "A" * 64, "sha256:" + "0" * 63],
)
def test_malformed_sha256_is_rejected(valid_artifact_bundle, tmp_path, digest):
    valid_artifact_bundle["artifacts"][0]["sha256"] = digest

    assert "invalid_artifact_sha256" in issue_codes(valid_artifact_bundle, tmp_path)


def test_artifact_digest_must_match(valid_artifact_bundle, tmp_path):
    valid_artifact_bundle["artifacts"][0]["sha256"] = "sha256:" + "0" * 64

    assert "artifact_digest_mismatch" in issue_codes(valid_artifact_bundle, tmp_path)


def test_byte_and_digest_mismatches_are_reported_independently(
    valid_artifact_bundle, tmp_path
):
    valid_artifact_bundle["artifacts"][0]["bytes"] += 1
    valid_artifact_bundle["artifacts"][0]["sha256"] = "sha256:" + "0" * 64

    assert {"artifact_bytes_mismatch", "artifact_digest_mismatch"}.issubset(
        issue_codes(valid_artifact_bundle, tmp_path)
    )


@pytest.mark.parametrize("section", ["tests", "claims", "traces"])
def test_unknown_evidence_reference_in_list_section_is_rejected(
    valid_artifact_bundle, tmp_path, section
):
    valid_artifact_bundle[section][0]["evidence"] = ["missing-artifact"]

    issues = validate_artifacts(valid_artifact_bundle, tmp_path)

    assert any(
        problem.code == "unknown_evidence_ref"
        and problem.location == f"{section}[0].evidence[0]"
        for problem in issues
    )


@pytest.mark.parametrize("section", ["environment", "deployment"])
def test_unknown_evidence_reference_in_object_section_is_rejected(
    valid_artifact_bundle, tmp_path, section
):
    valid_artifact_bundle[section]["evidence"] = ["missing-artifact"]

    issues = validate_artifacts(valid_artifact_bundle, tmp_path)

    assert any(
        problem.code == "unknown_evidence_ref"
        and problem.location == f"{section}.evidence[0]"
        for problem in issues
    )


def test_missing_claim_reference_yields_unknown_evidence_ref(
    valid_artifact_bundle, tmp_path
):
    valid_artifact_bundle["claims"][0]["evidence"] = ["missing"]

    assert "unknown_evidence_ref" in issue_codes(valid_artifact_bundle, tmp_path)


@pytest.mark.parametrize("evidence", [None, "artifact-evidence-json", {}, [""], [7]])
def test_malformed_evidence_list_or_reference_is_rejected(
    valid_artifact_bundle, tmp_path, evidence
):
    valid_artifact_bundle["tests"][0]["evidence"] = evidence

    assert "invalid_evidence" in issue_codes(valid_artifact_bundle, tmp_path)


@pytest.mark.parametrize("section", ["tests", "claims", "traces"])
def test_malformed_evidence_record_is_rejected(
    valid_artifact_bundle, tmp_path, section
):
    valid_artifact_bundle[section][0] = None

    assert "malformed_evidence_record" in issue_codes(valid_artifact_bundle, tmp_path)


@pytest.mark.parametrize("section", ["tests", "claims", "traces"])
def test_evidence_record_sections_must_be_lists(
    valid_artifact_bundle, tmp_path, section
):
    valid_artifact_bundle[section] = None

    assert "invalid_evidence_container" in issue_codes(valid_artifact_bundle, tmp_path)


@pytest.mark.parametrize("section", ["environment", "deployment"])
def test_environment_and_deployment_must_be_objects(
    valid_artifact_bundle, tmp_path, section
):
    valid_artifact_bundle[section] = []

    assert "invalid_evidence_container" in issue_codes(valid_artifact_bundle, tmp_path)


def test_optional_deployment_may_be_absent(valid_artifact_bundle, tmp_path):
    del valid_artifact_bundle["deployment"]

    assert validate_artifacts(valid_artifact_bundle, tmp_path) == []


def test_unrelated_nested_evidence_strings_are_not_recursively_interpreted(
    valid_artifact_bundle, tmp_path
):
    valid_artifact_bundle["tests"][0]["details"] = {
        "evidence": ["missing-artifact"]
    }

    assert validate_artifacts(valid_artifact_bundle, tmp_path) == []


def test_artifact_validation_does_not_mutate_input(
    valid_artifact_bundle, tmp_path, cloned
):
    before = cloned(valid_artifact_bundle)

    validate_artifacts(valid_artifact_bundle, tmp_path)

    assert valid_artifact_bundle == before


def test_artifact_validation_fails_closed_for_non_mapping_bundle(tmp_path):
    issues = validate_artifacts(None, tmp_path)

    assert [(problem.code, problem.location) for problem in issues] == [
        ("invalid_bundle", "bundle")
    ]


def test_artifact_issues_are_sorted(valid_artifact_bundle, tmp_path):
    valid_artifact_bundle["claims"][0]["evidence"] = ["z-missing"]
    valid_artifact_bundle["tests"][0]["evidence"] = ["a-missing"]

    issues = validate_artifacts(valid_artifact_bundle, tmp_path)

    assert issues == sorted(issues)


def test_evidence_bundle_schema_closes_artifact_records(
    valid_artifact_bundle, valid_contract, valid_candidate, valid_permit
):
    bundle = {
        "schema_version": "gawain.evidence-bundle.v1",
        "run_id": "run-artifact-schema",
        "contract": valid_contract,
        "candidate": valid_candidate,
        "permit": valid_permit,
        "verdict": {},
        **valid_artifact_bundle,
    }
    assert validate_schema(bundle, "evidence-bundle.v1.schema.json") == []

    bundle["artifacts"][0]["unexpected"] = True
    issues = validate_schema(bundle, "evidence-bundle.v1.schema.json")

    assert "$.artifacts[0]" in {problem.location for problem in issues}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("artifact_id", ""),
        ("kind", ""),
        ("path", ""),
        ("bytes", -1),
        ("sha256", "sha256:" + "A" * 64),
    ],
)
def test_evidence_bundle_schema_rejects_invalid_artifact_fields(
    valid_artifact_bundle, valid_contract, valid_candidate, valid_permit, field, value
):
    bundle = {
        "schema_version": "gawain.evidence-bundle.v1",
        "run_id": "run-artifact-schema",
        "contract": valid_contract,
        "candidate": valid_candidate,
        "permit": valid_permit,
        "verdict": {},
        **valid_artifact_bundle,
    }
    bundle["artifacts"][0][field] = value

    assert f"$.artifacts[0].{field}" in {
        problem.location
        for problem in validate_schema(bundle, "evidence-bundle.v1.schema.json")
    }
