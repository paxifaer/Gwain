from __future__ import annotations

import json
import math
from ipaddress import IPv4Address
from importlib import resources
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import (
    FormatError,
    RefResolutionError,
    SchemaError,
    ValidationError,
)

from .issues import ValidationIssue, issue


_SCHEMA_RESOURCES = {
    "verification-contract.v1.schema.json": "verification-contract.v1.schema.json",
    "evidence-bundle.v1.schema.json": "evidence-bundle.v1.schema.json",
    "trace-event.v1.schema.json": "trace-event.v1.schema.json",
}
_FORMAT_CHECKER = FormatChecker()
MAX_SCHEMA_DEPTH = 64
MAX_SCHEMA_NODES = 100_000
MAX_SCHEMA_WIDTH = 2_048
MAX_SCHEMA_STRING_LENGTH = 1024 * 1024
MAX_SCHEMA_ISSUES = 256
MAX_SCHEMA_LOCATION_LENGTH = 128
MAX_SCHEMA_LOCATION_COMPONENT_LENGTH = 64
MAX_SCHEMA_SELECTOR_LENGTH = 128
_VALIDATOR_KEYWORDS = frozenset(
    {
        "additionalProperties",
        "allOf",
        "anyOf",
        "const",
        "contains",
        "dependentRequired",
        "dependentSchemas",
        "enum",
        "exclusiveMaximum",
        "exclusiveMinimum",
        "format",
        "if",
        "items",
        "maxContains",
        "maximum",
        "maxItems",
        "maxLength",
        "maxProperties",
        "minContains",
        "minimum",
        "minItems",
        "minLength",
        "minProperties",
        "multipleOf",
        "not",
        "oneOf",
        "pattern",
        "patternProperties",
        "prefixItems",
        "propertyNames",
        "required",
        "then",
        "type",
        "unevaluatedItems",
        "unevaluatedProperties",
        "uniqueItems",
    }
)


@_FORMAT_CHECKER.checks("ipv4-endpoint", raises=ValueError)
def _is_ipv4_endpoint(value: object) -> bool:
    if not isinstance(value, str) or value.count(":") != 1:
        return False
    address, port_text = value.split(":")
    if not port_text.isascii() or not port_text.isdecimal():
        return False
    IPv4Address(address)
    return 1 <= int(port_text) <= 65535


def _is_safe_json_tree(value: object) -> bool:
    stack: list[tuple[str, object, int]] = [("value", value, 0)]
    active_containers: set[int] = set()
    node_count = 0

    while stack:
        action, current, depth = stack.pop()
        if action == "children":
            iterator, identity = current
            try:
                child = next(iterator)
            except StopIteration:
                active_containers.remove(identity)
                continue
            stack.append(("children", current, depth))
            stack.append(("value", child, depth))
            continue

        node_count += 1
        if node_count > MAX_SCHEMA_NODES or depth > MAX_SCHEMA_DEPTH:
            return False
        if current is None or type(current) in {bool, int}:
            continue
        if type(current) is float:
            if not math.isfinite(current):
                return False
            continue
        if type(current) is str:
            if len(current) > MAX_SCHEMA_STRING_LENGTH:
                return False
            continue
        if type(current) not in {list, dict}:
            return False

        child_count = len(current)
        if (
            child_count > MAX_SCHEMA_WIDTH
            or child_count > MAX_SCHEMA_NODES - node_count
        ):
            return False
        if type(current) is dict:
            if any(
                type(key) is not str
                or len(key) > MAX_SCHEMA_STRING_LENGTH
                for key in current
            ):
                return False
            children = iter(current.values())
        else:
            children = iter(current)

        identity = id(current)
        if identity in active_containers:
            return False
        active_containers.add(identity)
        stack.append(("children", (children, identity), depth + 1))

    return True


def _schema_property_names(schema: object) -> frozenset[str]:
    names: set[str] = set()
    stack = [schema]
    while stack:
        current = stack.pop()
        if type(current) is dict:
            properties = current.get("properties")
            if type(properties) is dict:
                names.update(
                    key
                    for key in properties
                    if type(key) is str
                    and len(key) <= MAX_SCHEMA_LOCATION_COMPONENT_LENGTH
                    and key.isidentifier()
                )
            stack.extend(current.values())
        elif type(current) is list:
            stack.extend(current)
    return frozenset(names)


def _json_location(path: list[object], safe_names: frozenset[str]) -> str:
    location = "$"
    for part in path:
        if type(part) is int and 0 <= part <= MAX_SCHEMA_WIDTH:
            suffix = f"[{part}]"
        elif type(part) is str and part in safe_names:
            suffix = f".{part}"
        else:
            suffix = "[<key>]"
        if len(location) + len(suffix) > MAX_SCHEMA_LOCATION_LENGTH:
            return "$[<nested>]"
        location += suffix
    return location


def _resource_limit_issue() -> ValidationIssue:
    return issue(
        "schema_resource_limit",
        "$",
        "schema input exceeds safe resource limits",
    )


def _schema_failure_issue() -> ValidationIssue:
    return issue("schema_error", "$", "schema validation failed (internal)")


def validate_schema(instance: Any, schema_name: str) -> list[ValidationIssue]:
    if (
        type(schema_name) is not str
        or len(schema_name) > MAX_SCHEMA_SELECTOR_LENGTH
        or schema_name not in _SCHEMA_RESOURCES
    ):
        return [
            issue(
                "unknown_schema",
                "schema_name",
                "unsupported schema name",
            )
        ]
    if not _is_safe_json_tree(instance):
        return [_resource_limit_issue()]
    try:
        schema_resource = resources.files("gawain_verification.schemas").joinpath(
            _SCHEMA_RESOURCES[schema_name]
        )
        schema = json.loads(schema_resource.read_text(encoding="utf-8"))
        safe_names = _schema_property_names(schema)
        problems: list[ValidationIssue] = []
        errors = Draft202012Validator(
            schema, format_checker=_FORMAT_CHECKER
        ).iter_errors(instance)
        for error in errors:
            if len(problems) >= MAX_SCHEMA_ISSUES - 1:
                problems.append(
                    issue(
                        "schema_issue_limit",
                        "$",
                        "additional schema issues were suppressed",
                    )
                )
                break
            keyword = (
                error.validator
                if type(error.validator) is str
                and error.validator in _VALIDATOR_KEYWORDS
                else "unknown"
            )
            problems.append(
                issue(
                    "schema_error",
                    _json_location(list(error.absolute_path), safe_names),
                    f"schema validation failed ({keyword})",
                )
            )
    except (RecursionError, ValueError):
        return [_resource_limit_issue()]
    except (FormatError, RefResolutionError, SchemaError, ValidationError):
        return [_schema_failure_issue()]
    return sorted(problems, key=lambda problem: (problem.location, problem.message))
