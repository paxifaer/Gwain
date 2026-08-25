from __future__ import annotations

import hashlib
import json
from typing import Any


IDENTITY_FIELDS = {
    "contract": "contract_id",
    "candidate": "candidate_id",
    "permit": "permit_id",
    "bundle": "bundle_id",
}


def _normalized(kind: str, value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result.pop(IDENTITY_FIELDS[kind], None)
    if kind == "candidate":
        result["components"] = sorted(
            result.get("components", []), key=lambda item: item["name"]
        )
    return result


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def content_id(kind: str, value: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json(_normalized(kind, value)))
