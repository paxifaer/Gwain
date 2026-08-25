from __future__ import annotations

import json
from importlib import resources
from typing import Any

from jsonschema import Draft202012Validator

from .issues import ValidationIssue, issue


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
    schema_resource = resources.files("schemas").joinpath(schema_name)
    schema = json.loads(schema_resource.read_text(encoding="utf-8"))
    errors = Draft202012Validator(schema).iter_errors(instance)
    problems = [
        issue("schema_error", _json_location(list(error.absolute_path)), error.message)
        for error in errors
    ]
    return sorted(problems, key=lambda problem: (problem.location, problem.message))
