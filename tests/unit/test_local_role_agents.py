"""Tests for the lightweight local teaching-role coordinator."""

from dataclasses import dataclass

from ai_growth_companion.application.local_role_agents import LocalRole, LocalRoleAgentLayer
from ai_growth_companion.providers.base import (
    ProviderMetadata,
    ProviderResponse,
    TeachingPlanRequest,
    TeachingSourceUnit,
)


def plan_request() -> TeachingPlanRequest:
    return TeachingPlanRequest(
        topic="函数极限",
        source_text="极限描述函数在某点附近的变化趋势。",
        source_units=(
            TeachingSourceUnit(
                document_id="doc-1",
                filename="limits.md",
                page_number=None,
                text="极限描述函数在某点附近的变化趋势。",
            ),
        ),
    )


def test_fallback_plan_contains_dependencies_and_visual_hint() -> None:
    layer = LocalRoleAgentLayer()

    plan = layer.plan_lesson(plan_request(), request_id="plan-fallback-1")

    assert plan.schema_version == "teaching-plan-v0.1"
    assert [node.node_id for node in plan.nodes] == [
        "concept",
        "mechanism",
        "boundary",
        "example",
    ]
    assert [(edge.from_node, edge.to_node) for edge in plan.dependencies] == [
        ("concept", "mechanism"),
        ("mechanism", "boundary"),
        ("boundary", "example"),
    ]
    assert plan.visual_intent == "dependency_graph"


@dataclass
class BrokenPlanner:
    model_name: str = "qwen-test"

    def generate_plan(self, request: TeachingPlanRequest, *, request_id: str) -> ProviderResponse:
        raise RuntimeError("planner unavailable")


def test_planner_failure_is_non_blocking() -> None:
    layer = LocalRoleAgentLayer(BrokenPlanner())

    plan = layer.plan_lesson(plan_request(), request_id="plan-broken-1")

    assert plan.nodes
    assert plan.topic == "函数极限"


@dataclass
class ValidPlanner:
    model_name: str = "qwen-test"

    def generate_plan(self, request: TeachingPlanRequest, *, request_id: str) -> ProviderResponse:
        return ProviderResponse(
            content={
                "schema_version": "teaching-plan-v0.1",
                "topic": "错误主题",
                "nodes": [
                    {
                        "node_id": "one",
                        "title": "第一步",
                        "purpose": "先确认资料中的定义。",
                        "source_document_ids": ["doc-1", "not-selected"],
                    },
                    {
                        "node_id": "two",
                        "title": "第二步",
                        "purpose": "再解释资料中的过程。",
                        "prerequisites": ["one"],
                        "source_document_ids": ["doc-1"],
                    },
                ],
                "dependencies": [
                    {"from_node": "one", "to_node": "two"},
                    {"from_node": "fake", "to_node": "two"},
                ],
            },
            metadata=ProviderMetadata(
                provider="ollama",
                model="qwen-test",
                model_revision=None,
                prompt_version="test",
                schema_version="teaching-plan-v0.1",
                latency_ms=1,
                usage={},
                finish_reason="stop",
                request_id=request_id,
            ),
        )


def test_planner_output_is_sanitized_to_request_boundary() -> None:
    layer = LocalRoleAgentLayer(ValidPlanner())

    plan = layer.plan_lesson(plan_request(), request_id="plan-valid-1")

    assert plan.topic == "函数极限"
    assert plan.nodes[0].source_document_ids == ["doc-1"]
    assert [(edge.from_node, edge.to_node) for edge in plan.dependencies] == [("one", "two")]


def test_role_manifest_keeps_roles_explicit() -> None:
    layer = LocalRoleAgentLayer()

    assert {assignment.role for assignment in layer.assignments} == set(LocalRole)
