"""Deterministic Learning Policy tests."""

from ai_growth_companion.domain.mastery import DemoLearningPolicy, DemoMasteryEngine
from ai_growth_companion.schemas.diagnosis import (
    ActionType,
    MisconceptionItem,
    ProviderObservation,
)


def test_explicit_misconception_requires_re_learning() -> None:
    observation = ProviderObservation(
        evidence=[],
        gaps=[],
        possible_misconceptions=[
            MisconceptionItem(
                description="把等价无穷小当成恒等相等",
                confidence=0.95,
                answer_excerpt="二者完全相同",
            )
        ],
        observation_confidence=0.95,
        limitations=[],
    )
    decision = DemoMasteryEngine().decide(observation, observation_id="obs-1")

    action = DemoLearningPolicy().choose(observation, decision)

    assert action.action_type is ActionType.RE_LEARN
    assert "重新学习" in action.instruction
