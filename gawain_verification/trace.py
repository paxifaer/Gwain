from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
import json
from pathlib import Path
import re
import stat

from .issues import ValidationIssue, issue
from .schema import validate_schema
from .secrets import validate_no_secrets


# Public resource policy for untrusted JSONL trace evidence.
MAX_TRACE_BYTES = 16 * 1024 * 1024
MAX_LINE_BYTES = 1024 * 1024
MAX_EVENTS = 10_000
MAX_SPANS = 5_000
MAX_ISSUES = 256

CONTEXT_FIELDS = (
    "run_id", "contract_id", "candidate_id", "test_case_id", "attempt_id",
    "operation_id", "trace_id",
)
TRACE_ID = re.compile(r"(?!0{32}$)[0-9a-f]{32}\Z")
RUN_ID = re.compile(r"run-[A-Za-z0-9._-]+\Z")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")


class _DuplicateJsonKey(ValueError):
    pass


class _InvalidJsonConstant(ValueError):
    pass


class _IssueCollector:
    def __init__(self) -> None:
        self.problems: list[ValidationIssue] = []
        self.truncated = False

    def add(self, problem: ValidationIssue) -> bool:
        if self.truncated:
            return False
        if len(self.problems) >= max(0, MAX_ISSUES - 1):
            if MAX_ISSUES > 0:
                self.problems.append(issue(
                    "issue_limit", "$",
                    "validation stopped after reaching the issue limit",
                ))
            self.truncated = True
            return False
        self.problems.append(problem)
        return True

    def extend(self, problems: list[ValidationIssue]) -> bool:
        for problem in problems:
            if not self.add(problem):
                return False
        return True

    def result(self) -> list[ValidationIssue]:
        return sorted(self.problems, key=lambda p: (p.location, p.code, p.message))


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> object:
    raise _InvalidJsonConstant


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


def _line_issue(code: str, line_number: int, message: str) -> ValidationIssue:
    return issue(code, f"line {line_number}", message)


def _safe_event_problems(value: dict[str, object], line_number: int) -> list[ValidationIssue]:
    schema_count = len(validate_schema(value, "trace-event.v1.schema.json"))
    problems = [
        _line_issue("schema_error", line_number, "trace event violates schema")
        for _ in range(schema_count)
    ]
    problems.extend(
        _line_issue(problem.code, line_number, problem.message)
        for problem in validate_no_secrets(value)
    )
    return problems


def _read_events(
    path: object, collector: _IssueCollector
) -> tuple[list[tuple[int, dict[str, object]]], int]:
    events: list[tuple[int, dict[str, object]]] = []
    spans: set[str] = set()
    nonblank_lines = 0
    total_bytes = 0
    try:
        trace_path = Path(path)
        metadata = trace_path.stat()
        if not stat.S_ISREG(metadata.st_mode):
            collector.add(issue("trace_file", "$", "trace evidence must be a regular file"))
            return events, nonblank_lines
        if metadata.st_size > MAX_TRACE_BYTES:
            collector.add(issue("trace_too_large", "$", "trace file exceeds the byte limit"))
            return events, nonblank_lines
        with trace_path.open("rb") as stream:
            line_number = 0
            while True:
                raw_line = stream.readline(MAX_LINE_BYTES + 1)
                if not raw_line:
                    break
                line_number += 1
                total_bytes += len(raw_line)
                if total_bytes > MAX_TRACE_BYTES:
                    collector.add(issue("trace_too_large", "$", "trace file exceeds the byte limit"))
                    return [], nonblank_lines
                if len(raw_line) > MAX_LINE_BYTES:
                    collector.add(_line_issue(
                        "line_too_long", line_number,
                        "trace line exceeds the byte limit",
                    ))
                    return [], nonblank_lines
                try:
                    line = raw_line.decode("utf-8", errors="strict")
                except UnicodeDecodeError:
                    nonblank_lines += 1
                    if not collector.add(_line_issue(
                        "trace_utf8", line_number,
                        "trace event is not valid UTF-8",
                    )):
                        return [], nonblank_lines
                    continue
                if not line.strip():
                    continue
                nonblank_lines += 1
                try:
                    value = json.loads(
                        line,
                        object_pairs_hook=_strict_object,
                        parse_constant=_reject_json_constant,
                    )
                except _DuplicateJsonKey:
                    problem = _line_issue(
                        "duplicate_json_key", line_number,
                        "duplicate JSON object member is forbidden",
                    )
                except _InvalidJsonConstant:
                    problem = _line_issue(
                        "invalid_json", line_number,
                        "non-finite JSON number is forbidden",
                    )
                except RecursionError:
                    problem = _line_issue(
                        "structure_limit", line_number,
                        "JSON nesting exceeds the structure limit",
                    )
                except (json.JSONDecodeError, ValueError):
                    problem = _line_issue(
                        "invalid_json", line_number,
                        "trace event is invalid JSON",
                    )
                else:
                    problem = None
                if problem is not None:
                    if not collector.add(problem):
                        return [], nonblank_lines
                    continue
                if not isinstance(value, dict):
                    if not collector.add(_line_issue(
                        "trace_event_type", line_number,
                        "trace event must be an object",
                    )):
                        return [], nonblank_lines
                    continue
                try:
                    event_problems = _safe_event_problems(value, line_number)
                except RecursionError:
                    event_problems = [_line_issue(
                        "structure_limit", line_number,
                        "event nesting exceeds the structure limit",
                    )]
                except ValueError:
                    event_problems = [_line_issue(
                        "invalid_json", line_number,
                        "trace event cannot be safely validated",
                    )]
                if event_problems:
                    if not collector.extend(event_problems):
                        return [], nonblank_lines
                    continue
                if len(events) >= MAX_EVENTS:
                    collector.add(issue("event_limit", "$", "trace exceeds the event limit"))
                    return [], nonblank_lines
                span = value["span_id"]
                if span not in spans and len(spans) >= MAX_SPANS:
                    collector.add(issue("span_limit", "$", "trace exceeds the span limit"))
                    return [], nonblank_lines
                spans.add(span)
                events.append((line_number, value))
    except (OSError, TypeError, ValueError):
        collector.add(issue("trace_file", "$", "trace file cannot be read"))
        return [], nonblank_lines
    return events, nonblank_lines


def _validate_cycles(parents: dict[str, object], collector: _IssueCollector) -> None:
    colors: dict[str, int] = {}
    for start in sorted(parents):
        if colors.get(start, 0) != 0:
            continue
        path: list[str] = []
        cursor: object = start
        while isinstance(cursor, str) and cursor in parents and colors.get(cursor, 0) == 0:
            colors[cursor] = 1
            path.append(cursor)
            cursor = parents[cursor]
        if isinstance(cursor, str) and colors.get(cursor) == 1:
            if not collector.add(issue(
                "parent_cycle", "$.spans",
                "span parent graph contains a cycle",
            )):
                return
        for span in path:
            colors[span] = 2


def validate_trace_file(path: Path, expected_context: object) -> list[ValidationIssue]:
    collector = _IssueCollector()
    if not _valid_context(expected_context):
        collector.add(issue("expected_context", "$", "expected trace context is malformed"))
        return collector.result()
    events, nonblank_lines = _read_events(path, collector)
    if collector.truncated:
        return collector.result()
    if not events:
        if nonblank_lines == 0 and not collector.problems:
            collector.add(issue("trace_empty", "$", "trace file contains no events"))
        return collector.result()

    event_ids: set[str] = set()
    sequences: set[int] = set()
    previous_sequence: int | None = None
    identities: dict[str, tuple[object, object, object]] = {}
    parents: dict[str, object] = {}
    kinds: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for line_number, event in events:
        for field in CONTEXT_FIELDS:
            if event[field] != expected_context[field]:
                if not collector.add(issue(
                    "trace_context_mismatch", f"line {line_number}.{field}",
                    f"{field} does not match expected context",
                )):
                    return collector.result()
        if event["operation_id"] != event["trace_id"]:
            if not collector.add(issue(
                "operation_trace_mismatch", f"line {line_number}.operation_id",
                "operation_id must equal trace_id",
            )):
                return collector.result()
        event_id = event["event_id"]
        if event_id in event_ids:
            if not collector.add(issue(
                "duplicate_event_id", f"line {line_number}.event_id",
                "event_id is duplicated",
            )):
                return collector.result()
        event_ids.add(event_id)
        sequence = event["sequence"]
        if sequence in sequences:
            if not collector.add(issue(
                "duplicate_sequence", f"line {line_number}.sequence",
                "sequence is duplicated",
            )):
                return collector.result()
        sequences.add(sequence)
        if previous_sequence is not None and sequence <= previous_sequence:
            if not collector.add(issue(
                "nonmonotonic_sequence", f"line {line_number}.sequence",
                "sequence must strictly increase in file order",
            )):
                return collector.result()
        previous_sequence = sequence
        span = event["span_id"]
        identity = (event["parent_span_id"], event["service"], event["instance_id"])
        if span in identities and identities[span] != identity:
            code = (
                "inconsistent_span_parent"
                if identities[span][0] != identity[0]
                else "inconsistent_span_identity"
            )
            if not collector.add(issue(
                code, f"line {line_number}",
                "span identity is inconsistent across events",
            )):
                return collector.result()
        else:
            identities[span] = identity
            parents[span] = identity[0]
        kinds[span].append((event["event_kind"], sequence))

    roots = [span for span, parent in parents.items() if parent is None]
    if len(roots) != 1 and not collector.add(issue(
        "root_span_count", "$", "trace must contain exactly one root span",
    )):
        return collector.result()
    for span, parent in sorted(parents.items()):
        if parent is not None and parent not in parents:
            if not collector.add(issue(
                "missing_parent_span", f"$.spans.{span}",
                "parent span does not exist",
            )):
                return collector.result()
    _validate_cycles(parents, collector)
    if collector.truncated:
        return collector.result()
    for span in sorted(kinds):
        span_events = kinds[span]
        all_sequences = [sequence for _, sequence in span_events]
        starts = [sequence for kind, sequence in span_events if kind == "SPAN_START"]
        ends = [sequence for kind, sequence in span_events if kind == "SPAN_END"]
        if not starts:
            collector.add(issue(
                "missing_span_start", f"$.spans.{span}", "span has no SPAN_START",
            ))
        elif len(starts) > 1:
            collector.add(issue(
                "duplicate_span_start", f"$.spans.{span}",
                "span has multiple SPAN_START events",
            ))
        elif starts[0] != min(all_sequences):
            collector.add(issue(
                "span_start_not_first", f"$.spans.{span}",
                "SPAN_START must be the first span event",
            ))
        if collector.truncated:
            return collector.result()
        if not ends:
            collector.add(issue(
                "missing_span_end", f"$.spans.{span}", "span has no SPAN_END",
            ))
        elif len(ends) > 1:
            collector.add(issue(
                "duplicate_span_end", f"$.spans.{span}",
                "span has multiple SPAN_END events",
            ))
        elif ends[0] != max(all_sequences):
            collector.add(issue(
                "span_end_not_last", f"$.spans.{span}",
                "SPAN_END must be the last span event",
            ))
        if collector.truncated:
            return collector.result()
        if starts and ends and min(ends) <= min(starts):
            collector.add(issue(
                "span_end_before_start", f"$.spans.{span}",
                "SPAN_END must follow SPAN_START",
            ))
        if collector.truncated:
            return collector.result()
    return collector.result()
