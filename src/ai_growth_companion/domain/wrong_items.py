"""Stable wrong-item classifications and user-controlled statuses."""

from enum import StrEnum


class WrongItemType(StrEnum):
    """Why a successful diagnosis needs a later correction or review."""

    MISCONCEPTION = "misconception"
    GAP = "gap"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class WrongItemStatus(StrEnum):
    """A user-facing lifecycle, deliberately separate from mastery state."""

    OPEN = "open"
    SNOOZED = "snoozed"
    MASTERED = "mastered"
