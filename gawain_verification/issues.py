from dataclasses import dataclass


@dataclass(frozen=True, slots=True, order=True)
class ValidationIssue:
    code: str
    location: str
    message: str


def issue(code: str, location: str, message: str) -> ValidationIssue:
    return ValidationIssue(code=code, location=location, message=message)
