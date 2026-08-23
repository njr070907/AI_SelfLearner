"""Deterministic mastery and learning policies aligned with the first golden set."""

from ai_growth_companion.schemas.diagnosis import (
    ActionType,
    LearningAction,
    MasteryDecision,
    MasteryLevel,
    ProviderObservation,
    UnderstandingLevel,
)

DEMO_PROTOCOL_VERSION = "mastery-protocol-v0.2-golden-baseline"
DEMO_POLICY_VERSION = "learning-policy-v0.2-golden-baseline"


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
                mastery_level=MasteryLevel.NOT_EVIDENT,
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
    ) -> LearningAction:
        """Return exactly one deterministic action for the fake experiment."""
        if observation.possible_misconceptions:
            action_type = ActionType.REVIEW
            instruction = "先核对并修正报告中的可能误区，再用自己的话重新解释。"
        elif decision.mastery_level is MasteryLevel.NOT_EVIDENT:
            action_type = ActionType.RE_EXPLAIN
            instruction = "补充一个具体例子，并说明它背后的运作机制。"
        elif observation.gaps:
            action_type = ActionType.RE_EXPLAIN
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
