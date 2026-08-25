"""Deterministic local workspace data for frontend development and manual QA."""

from dataclasses import dataclass

from ai_growth_companion.application.bootstrap import build_learning_service
from ai_growth_companion.application.learning_service import LearningService
from ai_growth_companion.application.models import DiagnosisView
from ai_growth_companion.config import Settings
from ai_growth_companion.providers.fake import FakeScenario
from ai_growth_companion.repositories.database import Database, run_migrations


@dataclass(frozen=True)
class DemoWorkspaceSummary:
    """Counts printed by the seed command and asserted by its contract test."""

    history_count: int
    concept_state_count: int
    wrong_item_count: int
    review_queue_count: int


def seed_fake_workspace(
    database_url: str,
    *,
    seed_name: str = "frontend-demo",
) -> DemoWorkspaceSummary:
    """Create a repeatable Fake workspace without deleting existing local data.

    Every write uses a stable request id derived from ``seed_name``. Running the
    command again with the same name is therefore idempotent, while a different
    name can create a separate demo batch in the same local database.
    """
    normalized_seed = seed_name.strip()
    if not normalized_seed:
        raise ValueError("seed_name cannot be empty")
    if len(normalized_seed) > 80:
        raise ValueError("seed_name cannot exceed 80 characters")

    database = Database(database_url)
    run_migrations(database)
    settings = Settings(
        database_url=database_url,
        llm_provider="fake",
        llm_model="fake-mastery-v0.1",
        llm_api_key=None,
        llm_paid_calls_allowed=False,
    )
    service = build_learning_service(database, settings)

    first = _submit_turn(
        service,
        seed=normalized_seed,
        key="limits-partial",
        concept="函数极限",
        scenario=FakeScenario.PARTIAL,
        answer="我知道函数靠近某点时会接近一个值，但还没有说清左右极限和存在条件。",
    )
    _submit_turn(
        service,
        seed=normalized_seed,
        key="limits-strong",
        concept="函数极限",
        scenario=FakeScenario.STRONG,
        answer="函数极限描述自变量趋近某点时函数值的稳定趋势，也要检查左右极限是否相等。",
    )
    if first.diagnosis_id is not None:
        service.record_user_correction(
            diagnosis_id=first.diagnosis_id,
            correction="我补充了左右极限相等才足以说明双侧极限存在。",
            request_id=_request_id(normalized_seed, "limits-correction"),
        )

    _submit_turn(
        service,
        seed=normalized_seed,
        key="lhopital-misconception",
        concept="洛必达法则",
        scenario=FakeScenario.MISCONCEPTION,
        answer="我记得只要看到分式就可以直接使用洛必达法则。",
    )
    _submit_turn(
        service,
        seed=normalized_seed,
        key="taylor-insufficient",
        concept="泰勒公式",
        scenario=FakeScenario.INSUFFICIENT_EVIDENCE,
        answer="我暂时只记得一个公式，不能解释它为什么成立或什么时候适用。",
    )

    snapshot = service.get_workspace_snapshot()
    return DemoWorkspaceSummary(
        history_count=len(snapshot.history),
        concept_state_count=len(snapshot.concept_states),
        wrong_item_count=len(snapshot.wrong_items),
        review_queue_count=len(snapshot.review_queue),
    )


def _submit_turn(
    service: LearningService,
    *,
    seed: str,
    key: str,
    concept: str,
    scenario: FakeScenario,
    answer: str,
) -> DiagnosisView:
    session = service.start_session(
        concept=concept,
        request_id=_request_id(seed, f"{key}-session"),
    )
    return service.submit_answer(
        session_id=session.session_id,
        answer_text=answer,
        scenario=scenario,
        request_id=_request_id(seed, f"{key}-answer"),
    )


def _request_id(seed: str, key: str) -> str:
    return f"demo:{seed}:{key}"
