"""Small local role layer for source-grounded conventional teaching.

The layer deliberately has no agent runtime or hidden loop.  It assigns clear roles,
asks one optional local planner for a validated route, and falls back immediately to a
deterministic plan when the model is unavailable.  The normal teaching provider still
owns prose generation while the application owns evidence and mastery decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ai_growth_companion.providers.base import (
    ProviderResponse,
    TeachingPlanProvider,
    TeachingPlanRequest,
)
from ai_growth_companion.schemas.teaching import TeachingDependency, TeachingPlan, TeachingPlanNode


class LocalRole(StrEnum):
    """Roles kept explicit so models can be swapped without changing the workflow."""

    PLANNER = "planner"
    TEACHER = "teacher"
    QUIZ_DESIGNER = "quiz_designer"
    SOURCE_REVIEWER = "source_reviewer"
    TRANSLATOR = "translator"
    VISUAL_PLANNER = "visual_planner"


@dataclass(frozen=True)
class LocalRoleAssignment:
    """A human-readable assignment for diagnostics and future routing."""

    role: LocalRole
    model_name: str
    purpose: str


class LocalRoleAgentLayer:
    """Coordinate optional local roles without making lesson generation fragile."""

    def __init__(
        self,
        planner: TeachingPlanProvider | None = None,
        *,
        teacher_model: str = "application-teaching-provider",
        quiz_model: str = "application-teaching-provider",
        source_reviewer_model: str = "application-grounding-checker",
        translator_model: str = "application-translation-provider",
        visual_planner_model: str = "application-visual-planner",
    ) -> None:
        self._planner = planner
        self._assignments = (
            LocalRoleAssignment(
                LocalRole.PLANNER,
                getattr(planner, "model_name", "deterministic-local-planner"),
                "整理核心事实、知识依赖和发现路径",
            ),
            LocalRoleAssignment(LocalRole.TEACHER, teacher_model, "按路线生成常规讲解和例子"),
            LocalRoleAssignment(
                LocalRole.QUIZ_DESIGNER,
                quiz_model,
                "生成同构选项并覆盖机制、边界和常见误区",
            ),
            LocalRoleAssignment(
                LocalRole.SOURCE_REVIEWER,
                source_reviewer_model,
                "核对页码、引文和资料范围；最终由后端确定状态",
            ),
            LocalRoleAssignment(
                LocalRole.TRANSLATOR,
                translator_model,
                "保留原文证据的前提下提供中文理解上下文",
            ),
            LocalRoleAssignment(
                LocalRole.VISUAL_PLANNER,
                visual_planner_model,
                "只在结构、过程或几何关系值得画图时提出视觉建议",
            ),
        )

    @property
    def assignments(self) -> tuple[LocalRoleAssignment, ...]:
        """Expose role ownership without exposing credentials or model prompts."""
        return self._assignments

    def plan_lesson(self, request: TeachingPlanRequest, *, request_id: str) -> TeachingPlan:
        """Get one plan from the local model, or return a safe deterministic route."""
        if self._planner is None:
            return self.fallback_plan(request)
        try:
            response: ProviderResponse = self._planner.generate_plan(
                request,
                request_id=request_id,
            )
            plan = TeachingPlan.model_validate(response.content)
            return self._sanitize_plan(plan, request)
        except Exception:
            # Planning is an enhancement.  A failed planner must never prevent a lesson
            # from being generated from the selected source material.
            return self.fallback_plan(request)

    @staticmethod
    def _sanitize_plan(plan: TeachingPlan, request: TeachingPlanRequest) -> TeachingPlan:
        """Keep model-generated routing inside the selected source and topic boundary."""
        allowed_source_ids = set(request.source_document_ids) or {
            unit.document_id for unit in request.source_units if unit.document_id
        }
        nodes = []
        node_ids: set[str] = set()
        for node in plan.nodes:
            if node.node_id in node_ids:
                continue
            node_ids.add(node.node_id)
            nodes.append(
                node.model_copy(
                    update={
                        "source_document_ids": [
                            item for item in node.source_document_ids if item in allowed_source_ids
                        ]
                    }
                )
            )
        if not nodes:
            return LocalRoleAgentLayer.fallback_plan(request)
        dependencies = [
            dependency
            for dependency in plan.dependencies
            if dependency.from_node in node_ids and dependency.to_node in node_ids
        ]
        return plan.model_copy(
            update={
                "topic": request.topic,
                "nodes": nodes,
                "dependencies": dependencies,
            }
        )

    @staticmethod
    def fallback_plan(request: TeachingPlanRequest) -> TeachingPlan:
        """Build a source-neutral route that does not invent domain-specific facts."""
        source_ids = list(
            dict.fromkeys(
                (*request.source_document_ids, *(unit.document_id for unit in request.source_units))
            )
        )[:20]
        nodes = [
            TeachingPlanNode(
                node_id="concept",
                title="核心概念",
                purpose="从资料中确认对象、定义和要解决的问题。",
                discovery_prompt="资料为什么需要提出这个概念？它要描述或解决什么现象？",
                source_document_ids=source_ids,
            ),
            TeachingPlanNode(
                node_id="mechanism",
                title="运作机制",
                purpose="按顺序理解定义、步骤或因果关系是怎样工作的。",
                prerequisites=["concept"],
                discovery_prompt="如果只观察输入和结果，中间发生了哪些可追踪的变化？",
                source_document_ids=source_ids,
            ),
            TeachingPlanNode(
                node_id="boundary",
                title="适用边界",
                purpose="检查依赖条件、常见误区和不能直接套用的情况。",
                prerequisites=["concept", "mechanism"],
                discovery_prompt="什么条件一旦缺失，资料中的结论就不能直接使用？",
                source_document_ids=source_ids,
            ),
            TeachingPlanNode(
                node_id="example",
                title="迁移例子",
                purpose="用结构相近的新情境检验是否能应用，而不是只记住原句。",
                prerequisites=["concept", "mechanism", "boundary"],
                discovery_prompt="换一个没有出现在资料里的情境，哪些结构仍然保持不变？",
                source_document_ids=source_ids,
            ),
        ]
        return TeachingPlan(
            topic=request.topic,
            core_truths=["先从原文确认事实，再解释原因和使用条件。"],
            nodes=nodes,
            dependencies=[
                TeachingDependency(from_node="concept", to_node="mechanism"),
                TeachingDependency(from_node="mechanism", to_node="boundary"),
                TeachingDependency(from_node="boundary", to_node="example"),
            ],
            visual_intent="dependency_graph",
            visual_prompt="用一条从概念到机制、边界再到迁移的依赖路线帮助定位学习位置。",
        )
