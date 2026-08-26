"""Deterministic mastery and learning policies aligned with the first golden set."""

from ai_growth_companion.schemas.diagnosis import (
    ActionType,
    LearningAction,
    MasteryDecision,
    MasteryLevel,
    ProviderObservation,
    UnderstandingLevel,
)

DEMO_PROTOCOL_VERSION = "mastery-protocol-v0.5-golden-baseline"
DEMO_POLICY_VERSION = "learning-policy-v0.5-golden-baseline"

FORGETFULNESS_CUES = ("忘记", "忘了", "忘掉", "想不起来", "记不全")


def learner_reported_forgetting(answer_text: str | None) -> bool:
    """Recognize an explicit memory-loss cue without treating uncertainty as forgetting."""
    if not answer_text:
        return False
    return any(cue in answer_text for cue in FORGETFULNESS_CUES)


class DemoMasteryEngine:
    """Apply the conservative rules approved with the first golden set."""

    def decide(self, observation: ProviderObservation, *, observation_id: str) -> MasteryDecision:
        """Create a deterministic decision without asking the LLM for final authority."""
        evidence_ids = [item.evidence_id for item in observation.evidence]
        evidence_ids.append(observation_id)

        if observation.possible_misconceptions:
            return MasteryDecision(
                mastery_level=MasteryLevel.FRAGILE,
                understanding_level=UnderstandingLevel.NOVICE,
                score=30,
                confidence=observation.observation_confidence,
                evidence_ids=evidence_ids,
                reason="当前结构化观察包含一个有原文依据的可能误区。",
                protocol_version=DEMO_PROTOCOL_VERSION,
            )
        if not observation.evidence:
            return MasteryDecision(
                mastery_level=MasteryLevel.NO_CLUE,
                understanding_level=UnderstandingLevel.NOVICE,
                score=10,
                confidence=observation.observation_confidence,
                evidence_ids=evidence_ids,
                reason="目前没有足够的回答证据支持掌握判断。",
                protocol_version=DEMO_PROTOCOL_VERSION,
            )
        if observation.gaps:
            return MasteryDecision(
                mastery_level=MasteryLevel.FRAGILE,
                understanding_level=UnderstandingLevel.NOVICE,
                score=40,
                confidence=observation.observation_confidence,
                evidence_ids=evidence_ids,
                reason=(
                    "回答包含部分正确内容，但仍有机制或边界缺口；单次复述不能作为迁移理解证据。"
                ),
                protocol_version=DEMO_PROTOCOL_VERSION,
            )
        return MasteryDecision(
            mastery_level=MasteryLevel.SOLID,
            understanding_level=UnderstandingLevel.PROFICIENT,
            score=85,
            confidence=observation.observation_confidence,
            evidence_ids=evidence_ids,
            reason="回答覆盖了当前问题要求的核心机制，且没有记录到重大缺口。",
            protocol_version=DEMO_PROTOCOL_VERSION,
        )


class DemoLearningPolicy:
    """Select one transparent next action from a validated decision and observation."""

    def choose(
        self,
        observation: ProviderObservation,
        decision: MasteryDecision,
        *,
        answer_text: str | None = None,
    ) -> LearningAction:
        """Return exactly one deterministic action for the fake experiment."""
        if learner_reported_forgetting(answer_text):
            action_type = ActionType.REVIEW
            instruction = (
                "先复习核心概念，再用一道复习题确认当前掌握程度；如果掌握仍然很低，再重新学习。"
            )
        elif observation.possible_misconceptions:
            action_type = ActionType.RE_LEARN
            instruction = "先重新学习并纠正错误概念，再用自己的话解释一个新例子。"
        elif decision.mastery_level is MasteryLevel.NO_CLUE:
            action_type = ActionType.RE_LEARN
            instruction = "先重新学习核心概念，再用一个具体例子检查是否形成理解。"
        elif observation.gaps:
            action_type = ActionType.RE_LEARN
            instruction = "先补充机制与边界，再用一个未提示的新情境检验迁移。"
        else:
            action_type = ActionType.PRACTICE
            instruction = "做一个新情境下的迁移练习，验证理解能否应用。"

        return LearningAction(
            action_type=action_type,
            instruction=instruction,
            reason=decision.reason,
            evidence_ids=decision.evidence_ids,
            policy_version=DEMO_POLICY_VERSION,
        )
