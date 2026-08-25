"""User feedback and longitudinal state vocabulary."""

from enum import StrEnum


class FeedbackVerdict(StrEnum):
    """How the learner rates one persisted diagnosis."""

    ACCURATE = "accurate"
    PARTIAL = "partial"
    INACCURATE = "inaccurate"


class ConceptTrend(StrEnum):
    """A deliberately coarse trend, never a promise of learning progress."""

    INSUFFICIENT_DATA = "insufficient_data"
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
