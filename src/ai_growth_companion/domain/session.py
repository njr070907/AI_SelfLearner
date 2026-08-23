"""Session input rules and explicit state errors."""

from enum import StrEnum


class SessionStatus(StrEnum):
    CREATED = "created"
    QUESTIONED = "questioned"
    ANSWERED = "answered"
    DIAGNOSED = "diagnosed"
    QUESTION_FAILED = "question_failed"
    DIAGNOSIS_FAILED = "diagnosis_failed"


class InputValidationError(ValueError):
    """A safe user-correctable input error."""


class InvalidSessionState(RuntimeError):
    """The requested operation is not legal for the persisted session state."""


def normalize_concept(value: str) -> str:
    """Trim and collapse whitespace without translating or rewriting meaning."""
    normalized = " ".join(value.strip().split())
    if not 2 <= len(normalized) <= 100:
        raise InputValidationError("知识点长度必须在 2–100 个字符之间")
    return normalized


def validate_answer(value: str) -> str:
    """Keep original wording while rejecting blank and oversized answers."""
    if not value.strip():
        raise InputValidationError("回答不能为空")
    if len(value) > 5000:
        raise InputValidationError("回答不能超过 5000 个字符")
    return value
