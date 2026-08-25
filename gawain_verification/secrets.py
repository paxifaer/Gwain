from __future__ import annotations

from collections.abc import Mapping

from .issues import ValidationIssue, issue


SENSITIVE_KEYS = frozenset(
    {"password", "passwd", "token", "api_key", "secret", "private_key", "authorization", "cookie"}
)
REDACTED = frozenset({"[REDACTED]", "<redacted>", "***"})
PEM_HEADERS = ("-----BEGIN PRIVATE KEY-----", "-----BEGIN RSA PRIVATE KEY-----")
MAX_DEPTH = 64
MAX_NODES = 10_000
MAX_WIDTH = 10_000


def _key_name(value: object) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_") if isinstance(value, str) else ""


def _child_location(location: str, key: object) -> str:
    if isinstance(key, int):
        return f"{location}[{key}]"
    return f"{location}.{key}" if isinstance(key, str) and key.isidentifier() else f"{location}[key]"


def validate_no_secrets(value: object, location: str = "$") -> list[ValidationIssue]:
    """Inspect an arbitrary object without copying, recursion, or revealing values."""
    problems: list[ValidationIssue] = []
    stack = [(value, location, 0)]
    seen: set[int] = set()
    nodes = 0
    while stack:
        current, current_location, depth = stack.pop()
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            problems.append(issue("structure_limit", current_location, "structure exceeds validation limits"))
            break
        if isinstance(current, str):
            if any(header in current for header in PEM_HEADERS):
                problems.append(issue("private_key_material", current_location, "private key material is forbidden"))
            continue
        if isinstance(current, Mapping):
            identity = id(current)
            if identity in seen:
                problems.append(issue("structure_limit", current_location, "cyclic or repeated container is forbidden"))
                continue
            seen.add(identity)
            try:
                if len(current) > MAX_WIDTH:
                    problems.append(issue("structure_limit", current_location, "structure exceeds width limit"))
                    continue
                items = list(current.items())
            except Exception:
                problems.append(issue("structure_limit", current_location, "structure cannot be safely inspected"))
                continue
            for key, child in reversed(items):
                child_location = _child_location(current_location, key)
                if isinstance(key, str) and any(header in key for header in PEM_HEADERS):
                    problems.append(
                        issue(
                            "private_key_material",
                            f"{current_location}[key]",
                            "private key material is forbidden",
                        )
                    )
                if _key_name(key) in SENSITIVE_KEYS and not (isinstance(child, str) and child in REDACTED):
                    problems.append(issue("secret_key", child_location, "sensitive field must contain an approved redaction marker"))
                stack.append((child, child_location, depth + 1))
                if len(stack) > MAX_NODES:
                    problems.append(issue("structure_limit", current_location, "structure exceeds validation limits"))
                    stack.clear()
                    break
            continue
        if isinstance(current, (list, tuple)):
            identity = id(current)
            if identity in seen:
                problems.append(issue("structure_limit", current_location, "cyclic or repeated container is forbidden"))
                continue
            seen.add(identity)
            if len(current) > MAX_WIDTH:
                problems.append(issue("structure_limit", current_location, "structure exceeds width limit"))
                continue
            for index in range(len(current) - 1, -1, -1):
                stack.append((current[index], f"{current_location}[{index}]", depth + 1))
                if len(stack) > MAX_NODES:
                    problems.append(issue("structure_limit", current_location, "structure exceeds validation limits"))
                    stack.clear()
                    break
    return sorted(problems, key=lambda p: (p.location, p.code, p.message))
