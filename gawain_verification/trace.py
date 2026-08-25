from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
import json
from pathlib import Path
import re

from .issues import ValidationIssue, issue
from .schema import validate_schema
from .secrets import validate_no_secrets


CONTEXT_FIELDS = ("run_id", "contract_id", "candidate_id", "test_case_id", "attempt_id", "operation_id", "trace_id")
TRACE_ID = re.compile(r"(?!0{32}$)[0-9a-f]{32}\Z")
RUN_ID = re.compile(r"run-[A-Za-z0-9._-]+\Z")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")


def _valid_context(value: object) -> bool:
    try:
        if not isinstance(value, Mapping) or set(value) != set(CONTEXT_FIELDS):
            return False
        if any(not isinstance(value[name], str) or not value[name] for name in CONTEXT_FIELDS):
            return False
        return bool(
            RUN_ID.fullmatch(value["run_id"])
            and DIGEST.fullmatch(value["contract_id"])
            and DIGEST.fullmatch(value["candidate_id"])
            and TRACE_ID.fullmatch(value["operation_id"])
            and TRACE_ID.fullmatch(value["trace_id"])
            and value["operation_id"] == value["trace_id"]
        )
    except Exception:
        return False


def _at_line(problem: ValidationIssue, line_number: int) -> ValidationIssue:
    suffix = problem.location[1:] if problem.location.startswith("$") else f".{problem.location}"
    return issue(problem.code, f"line {line_number}{suffix}", problem.message)


def validate_trace_file(path: Path, expected_context: object) -> list[ValidationIssue]:
    problems: list[ValidationIssue] = []
    if not _valid_context(expected_context):
        return [issue("expected_context", "$", "expected trace context is malformed")]
    events: list[tuple[int, dict[str, object]]] = []
    nonblank_lines = 0
    try:
        with Path(path).open("rb") as stream:
            for line_number, raw_line in enumerate(stream, 1):
                try:
                    line = raw_line.decode("utf-8", errors="strict")
                except UnicodeDecodeError:
                    nonblank_lines += 1
                    problems.append(issue("trace_utf8", f"line {line_number}", "trace event is not valid UTF-8"))
                    continue
                if not line.strip():
                    continue
                nonblank_lines += 1
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    problems.append(issue("trace_json", f"line {line_number}", "invalid JSON event"))
                    continue
                if not isinstance(value, dict):
                    problems.append(issue("trace_event_type", f"line {line_number}", "trace event must be an object"))
                    continue
                schema_problems = validate_schema(value, "trace-event.v1.schema.json")
                secret_problems = validate_no_secrets(value)
                if secret_problems:
                    schema_problems = [
                        issue(p.code, p.location, "trace event does not match schema")
                        for p in schema_problems
                    ]
                event_problems = schema_problems + secret_problems
                problems.extend(_at_line(p, line_number) for p in event_problems)
                if not event_problems:
                    events.append((line_number, value))
    except (OSError, TypeError, ValueError):
        problems.append(issue("trace_file", str(path), "trace file cannot be read"))

    if not events:
        if nonblank_lines == 0 and not problems:
            problems.append(issue("trace_empty", "$", "trace file contains no events"))
        return sorted(problems, key=lambda p: (p.location, p.code, p.message))

    event_ids: dict[str, int] = {}
    sequences: dict[int, int] = {}
    previous_sequence: int | None = None
    parents: dict[str, object] = {}
    kinds: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for line_number, event in events:
        for field in CONTEXT_FIELDS:
            if event[field] != expected_context[field]:
                problems.append(issue("trace_context_mismatch", f"line {line_number}.{field}", f"{field} does not match expected context"))
        if event["operation_id"] != event["trace_id"]:
            problems.append(issue("operation_trace_mismatch", f"line {line_number}.operation_id", "operation_id must equal trace_id"))
        event_id = event["event_id"]
        if event_id in event_ids:
            problems.append(issue("duplicate_event_id", f"line {line_number}.event_id", "event_id is duplicated"))
        else:
            event_ids[event_id] = line_number
        sequence = event["sequence"]
        if sequence in sequences:
            problems.append(issue("duplicate_sequence", f"line {line_number}.sequence", "sequence is duplicated"))
        else:
            sequences[sequence] = line_number
        if previous_sequence is not None and sequence <= previous_sequence:
            problems.append(issue("nonmonotonic_sequence", f"line {line_number}.sequence", "sequence must strictly increase in file order"))
        previous_sequence = sequence
        span = event["span_id"]
        parent = event["parent_span_id"]
        if span in parents and parents[span] != parent:
            problems.append(issue("inconsistent_span_parent", f"line {line_number}.parent_span_id", "span has inconsistent parent identity"))
        else:
            parents[span] = parent
        kinds[span].append((event["event_kind"], sequence))

    roots = [span for span, parent in parents.items() if parent is None]
    if len(roots) != 1:
        problems.append(issue("root_span_count", "$", "trace must contain exactly one root span"))
    for span, parent in sorted(parents.items()):
        if parent is not None and parent not in parents:
            problems.append(issue("missing_parent_span", f"$.spans.{span}", "parent span does not exist"))
    for span in sorted(parents):
        visited: set[str] = set()
        cursor: object = span
        while cursor is not None and cursor in parents:
            if cursor in visited:
                problems.append(issue("parent_cycle", f"$.spans.{span}", "span parent graph contains a cycle"))
                break
            visited.add(cursor)
            cursor = parents[cursor]
    for span in sorted(kinds):
        span_events = kinds[span]
        starts = [seq for kind, seq in span_events if kind == "SPAN_START"]
        ends = [seq for kind, seq in span_events if kind == "SPAN_END"]
        if not starts:
            problems.append(issue("missing_span_start", f"$.spans.{span}", "span has no SPAN_START"))
        elif len(starts) > 1:
            problems.append(issue("duplicate_span_start", f"$.spans.{span}", "span has multiple SPAN_START events"))
        if not ends:
            problems.append(issue("missing_span_end", f"$.spans.{span}", "span has no SPAN_END"))
        elif len(ends) > 1:
            problems.append(issue("duplicate_span_end", f"$.spans.{span}", "span has multiple SPAN_END events"))
        if starts and ends and min(ends) <= min(starts):
            problems.append(issue("span_end_before_start", f"$.spans.{span}", "SPAN_END must follow SPAN_START"))
    return sorted(problems, key=lambda p: (p.location, p.code, p.message))
