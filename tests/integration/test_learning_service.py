"""End-to-end application service tests using only deterministic Fake scenarios."""

from pathlib import Path

import pytest

from ai_growth_companion.application.learning_service import LearningService
from ai_growth_companion.domain.events import LOCAL_USER_ID
from ai_growth_companion.domain.session import InvalidSessionState
from ai_growth_companion.domain.wrong_items import WrongItemStatus, WrongItemType
from ai_growth_companion.providers.fake import FakeScenario
from ai_growth_companion.repositories.database import Database, run_migrations
from ai_growth_companion.repositories.session_repository import SQLiteSessionRepository


def setup_service(tmp_path: Path) -> tuple[LearningService, SQLiteSessionRepository, Database]:
    database = Database(f"sqlite:///{(tmp_path / 'flow.db').as_posix()}")
    run_migrations(database)
    repository = SQLiteSessionRepository(database)
    return LearningService(repository), repository, database


@pytest.mark.parametrize(
    ("scenario", "expected_level"),
    [
        (FakeScenario.STRONG, "solid"),
        (FakeScenario.PARTIAL, "fragile"),
        (FakeScenario.MISCONCEPTION, "fragile"),
        (FakeScenario.INSUFFICIENT_EVIDENCE, "not_evident"),
    ],
)
def test_fake_success_scenarios_complete_full_pipeline(
    tmp_path: Path,
    scenario: FakeScenario,
    expected_level: str,
) -> None:
    service, repository, database = setup_service(tmp_path)
    session = service.start_session(concept="递归", request_id=f"start-{scenario.value}")

    result = service.submit_answer(
        session_id=session.session_id,
        answer_text="我用一个合成回答说明递归的机制。",
        scenario=scenario,
        request_id=f"answer-{scenario.value}",
    )

    assert result.status == "succeeded"
    assert result.decision is not None
    assert result.decision.mastery_level == expected_level
    assert result.envelope is not None

    with database.connect() as connection:
        event_types = [
            row["event_type"]
            for row in connection.execute(
                "SELECT event_type FROM learning_events WHERE session_id = ? ORDER BY rowid",
                (session.session_id,),
            ).fetchall()
        ]
        answer_count = connection.execute(
            "SELECT COUNT(*) FROM user_explanations WHERE session_id = ?",
            (session.session_id,),
        ).fetchone()[0]

    assert answer_count == 1
    expected_events = [
        "session_created",
        "question_generated",
        "answer_submitted",
        "provider_observation_recorded",
        "mastery_decision_recorded",
        "learning_action_selected",
    ]
    if scenario is not FakeScenario.STRONG:
        expected_events.append("wrong_item_created")
    assert event_types == expected_events

    rebuilt = repository.rebuild_current_state(
        user_id=LOCAL_USER_ID,
        concept_id=session.concept_id,
    )
    assert rebuilt is not None
    assert rebuilt.mastery_level == expected_level
    assert rebuilt.evidence_count == 1
    assert rebuilt.latest_event_id is not None


@pytest.mark.parametrize(
    ("scenario", "expected_status", "expected_code"),
    [
        (FakeScenario.PROVIDER_TIMEOUT, "failed", "LLM_TIMEOUT"),
        (FakeScenario.PROVIDER_FAILURE, "failed", "LLM_UNAVAILABLE"),
        (FakeScenario.INVALID_SCHEMA, "invalid", "LLM_OUTPUT_INVALID"),
    ],
)
def test_failure_preserves_answer_and_retry_uses_same_explanation(
    tmp_path: Path,
    scenario: FakeScenario,
    expected_status: str,
    expected_code: str,
) -> None:
    service, _repository, database = setup_service(tmp_path)
    session = service.start_session(concept="机会成本", request_id="start-failure")
    failed = service.submit_answer(
        session_id=session.session_id,
        answer_text="这是提交后必须保留的合成回答。",
        scenario=scenario,
        request_id="answer-failure",
    )

    assert failed.status == expected_status
    assert failed.error_code == expected_code
    assert failed.answer_saved is True
    assert failed.retryable is True
    assert failed.decision is None

    retried = service.retry(
        explanation_id=failed.explanation_id,
        scenario=FakeScenario.STRONG,
        request_id="retry-success",
    )

    assert retried.status == "succeeded"
    assert retried.explanation_id == failed.explanation_id
    with database.connect() as connection:
        answer_count = connection.execute(
            "SELECT COUNT(*) FROM user_explanations WHERE session_id = ?",
            (session.session_id,),
        ).fetchone()[0]
        attempts = connection.execute(
            "SELECT COUNT(*) FROM provider_observations WHERE explanation_id = ?",
            (failed.explanation_id,),
        ).fetchone()[0]
    assert answer_count == 1
    assert attempts == 2


def test_duplicate_requests_do_not_duplicate_session_or_answer(tmp_path: Path) -> None:
    service, _repository, database = setup_service(tmp_path)
    first_session = service.start_session(concept="梯度下降", request_id="same-start")
    second_session = service.start_session(concept="梯度下降", request_id="same-start")

    first = service.submit_answer(
        session_id=first_session.session_id,
        answer_text="合成答案用于验证幂等提交。",
        scenario=FakeScenario.PARTIAL,
        request_id="same-answer",
    )
    second = service.submit_answer(
        session_id=first_session.session_id,
        answer_text="合成答案用于验证幂等提交。",
        scenario=FakeScenario.PARTIAL,
        request_id="same-answer",
    )

    assert first_session.session_id == second_session.session_id
    assert first.explanation_id == second.explanation_id
    assert first.decision == second.decision
    with database.connect() as connection:
        session_count = connection.execute("SELECT COUNT(*) FROM learning_sessions").fetchone()[0]
        answer_count = connection.execute("SELECT COUNT(*) FROM user_explanations").fetchone()[0]
        observation_count = connection.execute(
            "SELECT COUNT(*) FROM provider_observations"
        ).fetchone()[0]
    assert (session_count, answer_count, observation_count) == (1, 1, 1)

    with pytest.raises(InvalidSessionState, match="不同的回答"):
        service.submit_answer(
            session_id=first_session.session_id,
            answer_text="相同幂等键不能对应这一条不同内容。",
            scenario=FakeScenario.PARTIAL,
            request_id="same-answer",
        )


def test_successful_diagnosis_cannot_be_retried(tmp_path: Path) -> None:
    service, _repository, _database = setup_service(tmp_path)
    session = service.start_session(concept="递归", request_id="retry-guard-start")
    result = service.submit_answer(
        session_id=session.session_id,
        answer_text="合成答案用于验证成功记录不能误重试。",
        scenario=FakeScenario.STRONG,
        request_id="retry-guard-answer",
    )

    with pytest.raises(InvalidSessionState, match="只有失败"):
        service.retry(
            explanation_id=result.explanation_id,
            scenario=FakeScenario.STRONG,
            request_id="retry-guard-invalid",
        )


def test_same_session_follow_up_is_saved_and_re_diagnosed(tmp_path: Path) -> None:
    service, repository, database = setup_service(tmp_path)
    session = service.start_session(concept="极限", request_id="follow-up-start")

    first = service.submit_answer(
        session_id=session.session_id,
        answer_text="第一次解释覆盖了定义，但还需要用例子说明边界。",
        scenario=FakeScenario.PARTIAL,
        request_id="follow-up-main",
    )
    assert first.answer_type == "main"
    assert first.sequence_no == 1
    assert service.get_session(session.session_id).can_submit_follow_up is True

    follow_up = service.submit_follow_up(
        session_id=session.session_id,
        answer_text="追问回答补充了一个新情境中的机制和边界。",
        scenario=FakeScenario.STRONG,
        request_id="follow-up-second",
    )

    assert follow_up.status == "succeeded"
    assert follow_up.answer_type == "follow_up"
    assert follow_up.sequence_no == 2
    assert follow_up.explanation_id != first.explanation_id
    assert follow_up.decision is not None
    assert follow_up.decision.mastery_level == "solid"
    assert service.get_session(session.session_id).answer_count == 2

    latest = service.get_session_diagnosis(session.session_id)
    assert latest is not None
    assert latest.explanation_id == follow_up.explanation_id
    assert latest.answer_type == "follow_up"

    rebuilt = repository.rebuild_current_state(
        user_id=LOCAL_USER_ID,
        concept_id=session.concept_id,
    )
    assert rebuilt is not None
    assert rebuilt.evidence_count == 2
    with database.connect() as connection:
        rows = connection.execute(
            "SELECT answer_type, sequence_no FROM user_explanations "
            "WHERE session_id = ? ORDER BY sequence_no",
            (session.session_id,),
        ).fetchall()
        answer_events = connection.execute(
            "SELECT payload_json FROM learning_events "
            "WHERE session_id = ? AND event_type = 'answer_submitted' ORDER BY rowid",
            (session.session_id,),
        ).fetchall()

    assert [(row["answer_type"], row["sequence_no"]) for row in rows] == [
        ("main", 1),
        ("follow_up", 2),
    ]
    assert '"answer_type": "follow_up"' in answer_events[1]["payload_json"]


def test_follow_up_requires_a_successful_main_diagnosis(tmp_path: Path) -> None:
    service, _repository, _database = setup_service(tmp_path)
    session = service.start_session(concept="导数", request_id="follow-up-guard-start")

    with pytest.raises(InvalidSessionState, match="成功诊断"):
        service.submit_follow_up(
            session_id=session.session_id,
            answer_text="还没有主回答，不能直接提交追问。",
            scenario=FakeScenario.STRONG,
            request_id="follow-up-before-main",
        )


@pytest.mark.parametrize(
    ("scenario", "expected_type"),
    [
        (FakeScenario.PARTIAL, WrongItemType.GAP),
        (FakeScenario.MISCONCEPTION, WrongItemType.MISCONCEPTION),
        (FakeScenario.INSUFFICIENT_EVIDENCE, WrongItemType.INSUFFICIENT_EVIDENCE),
    ],
)
def test_diagnosis_creates_traceable_wrong_item_and_status_is_idempotent(
    tmp_path: Path,
    scenario: FakeScenario,
    expected_type: WrongItemType,
) -> None:
    service, _repository, database = setup_service(tmp_path)
    session = service.start_session(concept="连续性", request_id=f"wrong-start-{scenario.value}")
    diagnosis = service.submit_answer(
        session_id=session.session_id,
        answer_text="这是一条用于错题追踪的合成回答。",
        scenario=scenario,
        request_id=f"wrong-answer-{scenario.value}",
    )

    items = service.list_wrong_items()
    assert len(items) == 1
    item = items[0]
    assert item.wrong_item_id
    assert item.error_type is expected_type
    assert item.status is WrongItemStatus.OPEN
    assert item.session_id == session.session_id
    assert item.explanation_id == diagnosis.explanation_id
    assert item.question_text == session.question_text
    assert item.answer_text == diagnosis.answer_text
    assert item.evidence.schema_version == "provider-observation-v0.1"
    assert item.correction_text

    mastered = service.update_wrong_item_status(
        wrong_item_id=item.wrong_item_id,
        status=WrongItemStatus.MASTERED,
        request_id=f"wrong-status-{scenario.value}",
    )
    duplicate = service.update_wrong_item_status(
        wrong_item_id=item.wrong_item_id,
        status=WrongItemStatus.MASTERED,
        request_id=f"wrong-status-{scenario.value}",
    )
    assert mastered.status is WrongItemStatus.MASTERED
    assert mastered.resolved_at is not None
    assert duplicate == mastered
    assert service.list_wrong_items(status=WrongItemStatus.OPEN) == ()
    assert service.list_wrong_items(status=WrongItemStatus.MASTERED)[0] == mastered

    with database.connect() as connection:
        status_events = connection.execute(
            "SELECT COUNT(*) FROM learning_events "
            "WHERE session_id = ? AND event_type = 'wrong_item_status_updated'",
            (session.session_id,),
        ).fetchone()[0]
    assert status_events == 1


def test_solid_diagnosis_does_not_create_wrong_item(tmp_path: Path) -> None:
    service, _repository, _database = setup_service(tmp_path)
    session = service.start_session(concept="矩阵", request_id="solid-wrong-start")
    service.submit_answer(
        session_id=session.session_id,
        answer_text="这是一条覆盖核心机制的合成回答。",
        scenario=FakeScenario.STRONG,
        request_id="solid-wrong-answer",
    )

    assert service.list_wrong_items() == ()


def test_history_can_be_reopened_by_a_new_service_instance(tmp_path: Path) -> None:
    service, repository, _database = setup_service(tmp_path)
    session = service.start_session(concept="Embedding", request_id="history-start")
    original = service.submit_answer(
        session_id=session.session_id,
        answer_text="合成答案用于验证应用重启后的历史恢复。",
        scenario=FakeScenario.PARTIAL,
        request_id="history-answer",
    )

    restarted_service = LearningService(repository)
    restored = restarted_service.get_session_diagnosis(session.session_id)

    assert restored is not None
    assert restored.explanation_id == original.explanation_id
    assert restored.decision == original.decision
    assert restarted_service.list_history()[0].session_id == session.session_id
