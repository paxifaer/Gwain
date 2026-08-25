from __future__ import annotations

import json
from ipaddress import IPv4Address
from importlib import resources
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .issues import ValidationIssue, issue


_SCHEMA_RESOURCES = {
    "verification-contract.v1.schema.json": "verification-contract.v1.schema.json",
    "evidence-bundle.v1.schema.json": "evidence-bundle.v1.schema.json",
    "trace-event.v1.schema.json": "trace-event.v1.schema.json",
}
_FORMAT_CHECKER = FormatChecker()


@_FORMAT_CHECKER.checks("ipv4-endpoint", raises=ValueError)
def _is_ipv4_endpoint(value: object) -> bool:
    if not isinstance(value, str) or value.count(":") != 1:
        return False
    address, port_text = value.split(":")
    if not port_text.isascii() or not port_text.isdecimal():
        return False
    IPv4Address(address)
    return 1 <= int(port_text) <= 65535


def _json_location(path: list[object]) -> str:
    location = "$"
    for part in path:
        if isinstance(part, int):
            location += f"[{part}]"
        elif isinstance(part, str) and part.isidentifier():
            location += f".{part}"
        else:
            location += f"[{json.dumps(part, ensure_ascii=False)}]"
    return location


def validate_schema(instance: Any, schema_name: str) -> list[ValidationIssue]:
    if not isinstance(schema_name, str) or schema_name not in _SCHEMA_RESOURCES:
        return [
            issue(
                "unknown_schema",
                "schema_name",
                f"unsupported schema name: {schema_name}",
            )
        ]
    schema_resource = resources.files("gawain_verification.schemas").joinpath(
        _SCHEMA_RESOURCES[schema_name]
    )
    schema = json.loads(schema_resource.read_text(encoding="utf-8"))
    errors = Draft202012Validator(
        schema, format_checker=_FORMAT_CHECKER
    ).iter_errors(instance)
    problems = [
        issue("schema_error", _json_location(list(error.absolute_path)), error.message)
        for error in errors
    ]
    return sorted(problems, key=lambda problem: (problem.location, problem.message))
