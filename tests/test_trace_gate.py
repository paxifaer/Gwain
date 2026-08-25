from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gawain_verification.schema import validate_schema
from gawain_verification.secrets import validate_no_secrets
from gawain_verification.trace import validate_trace_file


def load_events(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_events(path: Path, events):
    path.write_text("".join(json.dumps(x) + "\n" for x in events), encoding="utf-8")


def codes(path, context):
    return [x.code for x in validate_trace_file(path, context)]


def test_valid_trace(valid_trace_file, expected_trace_context):
    assert validate_trace_file(valid_trace_file, expected_trace_context) == []


def test_schema_is_valid_and_registered(valid_trace_file):
    schema = json.loads(
        (Path(__file__).parents[1] / "gawain_verification/schemas/trace-event.v1.schema.json").read_text()
    )
    Draft202012Validator.check_schema(schema)
    assert validate_schema(load_events(valid_trace_file)[0], "trace-event.v1.schema.json") == []


@pytest.mark.parametrize("content", [b"{bad}\n", b"[]\n", b'"text"\n'])
def test_bad_json_or_nonobject_is_line_numbered(tmp_path, expected_trace_context, content):
    path = tmp_path / "bad.jsonl"
    path.write_bytes(content)
    issues = validate_trace_file(path, expected_trace_context)
    assert issues and all(x.location.startswith("line 1") for x in issues)


def test_invalid_utf8_missing_file_and_blank_policy(tmp_path, expected_trace_context, valid_trace_file):
    bad = tmp_path / "utf8.jsonl"
    bad.write_bytes(b"\xff\n")
    utf8_issues = validate_trace_file(bad, expected_trace_context)
    assert any(x.code == "trace_utf8" and x.location == "line 1" for x in utf8_issues)
    assert "trace_file" in codes(tmp_path / "missing", expected_trace_context)
    valid_trace_file.write_text("\n" + valid_trace_file.read_text() + "  \n")
    assert validate_trace_file(valid_trace_file, expected_trace_context) == []
    empty = tmp_path / "empty.jsonl"
    empty.write_text("\n  \n")
    assert "trace_empty" in codes(empty, expected_trace_context)


def test_schema_issue_has_line_location(valid_trace_file, expected_trace_context):
    events = load_events(valid_trace_file)
    del events[1]["service"]
    write_events(valid_trace_file, events)
    issues = validate_trace_file(valid_trace_file, expected_trace_context)
    assert any(x.code == "schema_error" and x.location.startswith("line 2") for x in issues)


@pytest.mark.parametrize("field,value", [
    ("trace_id", "0" * 32), ("trace_id", "a" * 31),
    ("span_id", "0" * 16), ("span_id", "A" * 16),
    ("parent_span_id", "0" * 16), ("parent_span_id", "a" * 15),
])
def test_invalid_w3c_ids(valid_trace_file, expected_trace_context, field, value):
    events = load_events(valid_trace_file)
    index = 1 if field == "parent_span_id" else 0
    events[index][field] = value
    write_events(valid_trace_file, events)
    assert "schema_error" in codes(valid_trace_file, expected_trace_context)


def mutate(valid_trace_file, mutator):
    events = load_events(valid_trace_file)
    mutator(events)
    write_events(valid_trace_file, events)


@pytest.mark.parametrize("field", ["run_id", "contract_id", "candidate_id", "test_case_id", "attempt_id", "operation_id", "trace_id"])
def test_cross_context(valid_trace_file, expected_trace_context, field):
    replacements = {
        "run_id": "run-different",
        "contract_id": "sha256:" + "c" * 64,
        "candidate_id": "sha256:" + "d" * 64,
        "operation_id": "1" * 32,
        "trace_id": "1" * 32,
    }
    mutate(valid_trace_file, lambda e: e[1].__setitem__(field, replacements.get(field, "different")))
    assert "trace_context_mismatch" in codes(valid_trace_file, expected_trace_context)


def test_operation_must_equal_trace(valid_trace_file, expected_trace_context):
    mutate(valid_trace_file, lambda e: e[0].__setitem__("operation_id", "1" * 32))
    assert "operation_trace_mismatch" in codes(valid_trace_file, expected_trace_context)


@pytest.mark.parametrize("field,code", [("event_id", "duplicate_event_id"), ("sequence", "duplicate_sequence")])
def test_duplicate_identity(valid_trace_file, expected_trace_context, field, code):
    mutate(valid_trace_file, lambda e: e[1].__setitem__(field, e[0][field]))
    assert code in codes(valid_trace_file, expected_trace_context)


def test_nonmonotonic_sequence(valid_trace_file, expected_trace_context):
    mutate(valid_trace_file, lambda e: e[1].__setitem__("sequence", 9))
    assert "nonmonotonic_sequence" in codes(valid_trace_file, expected_trace_context)


@pytest.mark.parametrize("change,code", [
    (lambda e: e[1].__setitem__("parent_span_id", None), "root_span_count"),
    (lambda e: [x.__setitem__("parent_span_id", "1111111111111111") for x in e if x["span_id"].startswith("f")], "missing_parent_span"),
    (lambda e: [x.__setitem__("parent_span_id", "fedcba9876543210") for x in e if x["span_id"].startswith("0")], "parent_cycle"),
    (lambda e: e[2].__setitem__("parent_span_id", None), "inconsistent_span_parent"),
    (lambda e: e.pop(0), "missing_span_start"),
    (lambda e: e.pop(), "missing_span_end"),
    (lambda e: e.append({**e[0], "event_id": "extra", "sequence": 5}), "duplicate_span_start"),
    (lambda e: e.append({**e[-1], "event_id": "extra", "sequence": 5}), "duplicate_span_end"),
    (lambda e: (e[0].__setitem__("sequence", 4), e[-1].__setitem__("sequence", 1)), "span_end_before_start"),
])
def test_graph_defects(valid_trace_file, expected_trace_context, change, code):
    mutate(valid_trace_file, change)
    assert code in codes(valid_trace_file, expected_trace_context)


@pytest.mark.parametrize("kind,attributes", [
    ("STATE", {}), ("STATE", {"from_state": "", "to_state": "x"}),
    ("FAIL", {"caller": "x", "callee": "x", "phase": "x", "error_class": "x", "message": "x"}),
    ("ERROR", {"error_class": "x", "message": "x", "cause": ""}),
    ("SPAN_END", {"status": "BAD"}),
])
def test_event_specific_attributes(valid_trace_file, expected_trace_context, kind, attributes):
    events = load_events(valid_trace_file)
    events[2]["event_kind"] = kind
    events[2]["attributes"] = attributes
    write_events(valid_trace_file, events)
    assert "schema_error" in codes(valid_trace_file, expected_trace_context)


@pytest.mark.parametrize("key", ["password", "passwd", "token", "api_key", " API-KEY ", "secret", "private_key", "Authorization", "cookie"])
@pytest.mark.parametrize("wrapper", [lambda k: {k: "leak"}, lambda k: {"a": [{"b": {k: "leak"}}]}])
def test_sensitive_keys_nested(key, wrapper):
    value = wrapper(key)
    snapshot = deepcopy(value)
    issues = validate_no_secrets(value)
    assert [x.code for x in issues] == ["secret_key"]
    assert value == snapshot
    assert "leak" not in repr(issues)


@pytest.mark.parametrize("allowed", ["[REDACTED]", "<redacted>", "***"])
def test_exact_redactions_allowed(allowed):
    assert validate_no_secrets({"token": allowed}) == []


@pytest.mark.parametrize("forbidden", [None, "", 1, {}, [], "[redacted]"])
def test_other_sensitive_values_forbidden(forbidden):
    assert validate_no_secrets({"token": forbidden})[0].code == "secret_key"


@pytest.mark.parametrize("header", ["-----BEGIN PRIVATE KEY-----", "-----BEGIN RSA PRIVATE KEY-----"])
def test_pem_any_string_is_blocked_without_leak(header):
    issues = validate_no_secrets({"safe": ["prefix " + header + " material"]})
    assert issues[0].code == "private_key_material"
    assert header not in repr(issues)


def test_trace_secret_is_line_numbered_excluded_and_never_leaked(valid_trace_file, expected_trace_context):
    events = load_events(valid_trace_file)
    events[1]["attributes"]["API-KEY"] = "uniquely-sensitive-value"
    write_events(valid_trace_file, events)
    issues = validate_trace_file(valid_trace_file, expected_trace_context)
    assert any(x.code == "secret_key" and x.location.startswith("line 2") for x in issues)
    assert "uniquely-sensitive-value" not in repr(issues)


def test_cycles_depth_width_and_nodes_fail_closed():
    cycle = []
    cycle.append(cycle)
    deep = value = {}
    for _ in range(66):
        child = {}
        value["x"] = child
        value = child
    for obj in (cycle, deep, list(range(10001))):
        assert any(x.code == "structure_limit" for x in validate_no_secrets(obj))


@pytest.mark.parametrize("context", [None, {}, {"run_id": "x"}, {"run_id": 1}, {
    "run_id": "run-x", "contract_id": "sha256:" + "a" * 64,
    "candidate_id": "sha256:" + "b" * 64, "test_case_id": "P-01",
    "attempt_id": "attempt-1", "operation_id": "1" * 32, "trace_id": "2" * 32,
}])
def test_malformed_expected_context(valid_trace_file, context):
    assert "expected_context" in codes(valid_trace_file, context)


def test_deterministic_and_nonmutating(valid_trace_file, expected_trace_context):
    context = deepcopy(expected_trace_context)
    first = validate_trace_file(valid_trace_file, context)
    assert first == validate_trace_file(valid_trace_file, context)
    assert context == expected_trace_context
