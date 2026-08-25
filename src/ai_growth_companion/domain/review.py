"""Deterministic review scheduling rules for the MVP."""

from dataclasses import dataclass
from enum import StrEnum


class ReviewOutcome(StrEnum):
    """Coarse result used only for scheduling the next review."""

    CORRECT = "correct"
    PARTIAL = "partial"
    INCORRECT = "incorrect"


class ReviewAttemptStatus(StrEnum):
    """Whether the provider produced a usable retest diagnosis."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INVALID = "invalid"


class ReviewItemStatus(StrEnum):
    """Lifecycle of a review schedule, separate from wrong-item status."""

    ACTIVE = "active"
    MASTERED = "mastered"


@dataclass(frozen=True)
class ReviewScheduler:
    """Simple configurable intervals with conservative failure behavior."""

    intervals: tuple[int, ...] = (1, 3, 7)

    def __post_init__(self) -> None:
        if not self.intervals or any(day <= 0 for day in self.intervals):
            raise ValueError("复习间隔必须是正整数")
        if tuple(sorted(set(self.intervals))) != self.intervals:
            raise ValueError("复习间隔必须严格递增且不能重复")

    def next_interval(self, current_days: int, outcome: ReviewOutcome) -> int:
        """Return the next interval without pretending one retest proves mastery."""
        if outcome is ReviewOutcome.INCORRECT:
            return self.intervals[0]
        if outcome is ReviewOutcome.PARTIAL:
            return self.intervals[min(1, len(self.intervals) - 1)]

        next_index = next(
            (index for index, value in enumerate(self.intervals) if value > current_days),
            len(self.intervals) - 1,
        )
        return self.intervals[next_index]
