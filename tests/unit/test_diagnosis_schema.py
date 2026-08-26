"""Strict diagnosis contract tests."""

import pytest
from pydantic import ValidationError

from ai_growth_companion.schemas.diagnosis import (
    ActionType,
    LearningAction,
    MasteryDecision,
    MasteryLevel,
    ProviderObservation,
    storage_action_type,
    storage_mastery_level,
    validate_answer_excerpts,
)


def test_provider_observation_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ProviderObservation.model_validate(
            {
                "schema_version": "provider-observation-v0.1",
                "evidence": [],
                "gaps": [],
                "possible_misconceptions": [],
                "observation_confidence": 0.5,
                "limitations": [],
                "unexpected": True,
            }
        )


def test_evidence_excerpt_must_come_from_current_answer() -> None:
    observation = ProviderObservation.model_validate(
        {
            "schema_version": "provider-observation-v0.1",
            "evidence": [
                {
                    "evidence_id": "e1",
                    "claim": "声称用户提到了机制",
                    "answer_excerpt": "用户没有说过的文字",
                    "strength": "strong",
                }
            ],
            "gaps": [],
            "possible_misconceptions": [],
            "observation_confidence": 0.8,
            "limitations": [],
        }
    )

    with pytest.raises(ValueError, match="not present"):
        validate_answer_excerpts(observation, "这是用户实际提交的回答")


def test_mastery_levels_cannot_contradict_each_other() -> None:
    with pytest.raises(ValidationError, match="conflicts"):
        MasteryDecision(
            mastery_level="solid",
            understanding_level="novice",
            score=90,
            confidence=0.9,
            evidence_ids=["e1"],
            reason="合成测试",
            protocol_version="mastery-protocol-v0.1-demo",
        )


def test_v03_no_clue_and_re_learn_are_canonical_with_legacy_read_compatibility() -> None:
    decision = MasteryDecision(
        mastery_level="not_evident",
        understanding_level="novice",
        score=10,
        confidence=0.95,
        evidence_ids=[],
        reason="没有足够证据",
        protocol_version="mastery-protocol-v0.3-golden-baseline",
    )
    action = LearningAction(
        action_type="re_explain",
        instruction="重新学习核心概念",
        reason="完全未掌握",
        evidence_ids=[],
        policy_version="learning-policy-v0.3-golden-baseline",
    )

    assert decision.mastery_level is MasteryLevel.NO_CLUE
    assert action.action_type is ActionType.RE_LEARN
    assert storage_mastery_level(decision.mastery_level) == "not_evident"
    assert storage_action_type(action.action_type) == "re_explain"
