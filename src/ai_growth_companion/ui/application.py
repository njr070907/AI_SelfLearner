"""Streamlit UI for the deterministic Sprint 0 learning loop."""

from uuid import uuid4

import streamlit as st

from ai_growth_companion.application.learning_service import LearningService
from ai_growth_companion.application.models import DiagnosisView
from ai_growth_companion.config import Settings
from ai_growth_companion.domain.session import InputValidationError, InvalidSessionState
from ai_growth_companion.providers.fake import FakeScenario

SCENARIO_LABELS: dict[FakeScenario, str] = {
    FakeScenario.STRONG: "回答充分",
    FakeScenario.PARTIAL: "部分正确",
    FakeScenario.MISCONCEPTION: "包含误区",
    FakeScenario.INSUFFICIENT_EVIDENCE: "证据不足",
    FakeScenario.PROVIDER_TIMEOUT: "模拟超时",
    FakeScenario.PROVIDER_FAILURE: "模拟服务失败",
    FakeScenario.INVALID_SCHEMA: "模拟格式错误",
}

ERROR_MESSAGES = {
    "LLM_TIMEOUT": "Fake Provider 模拟了响应超时。",
    "LLM_UNAVAILABLE": "Fake Provider 模拟了服务不可用。",
    "LLM_OUTPUT_INVALID": "Fake Provider 返回的内容未通过结构化格式检查。",
}


def render_application(
    service: LearningService,
    *,
    settings: Settings,
    database_version: int,
) -> None:
    """Render navigation and keep all business behavior inside the service."""
    st.title("AI Growth Companion")
    st.caption("用自己的话解释知识，检查自己是否真正理解。")
    st.warning(
        "当前是 Sprint 0 演示环境：所有诊断均由可预测的 Fake Provider 生成，不能代表真实学习判断。"
    )

    page = st.sidebar.radio("导航", ("开始测试", "历史记录", "系统状态"))
    st.sidebar.caption("Fake Provider · 无 API 费用")

    if page == "开始测试":
        _render_learning_flow(service)
    elif page == "历史记录":
        _render_history(service)
    else:
        _render_system_status(settings=settings, database_version=database_version)


def _render_learning_flow(service: LearningService) -> None:
    if "current_session_id" not in st.session_state:
        _render_start_form(service)
        return

    try:
        session = service.get_session(st.session_state.current_session_id)
    except LookupError:
        st.error("当前会话无法读取，请重新开始。")
        _reset_flow()
        return

    st.subheader(session.concept)
    st.markdown(f"**费曼问题：** {session.question_text}")
    st.caption("请不用查资料，用自己的话解释。表达不漂亮没有关系。")

    result = st.session_state.get("last_diagnosis")
    if isinstance(result, DiagnosisView):
        _render_diagnosis(result)
        _render_result_actions(service, result)
        return

    with st.form("answer-form"):
        answer = st.text_area(
            "你的解释",
            key="draft_answer",
            height=180,
            placeholder="写下你目前真正理解的内容；不确定也可以直接说明。",
        )
        scenario = st.selectbox(
            "Sprint 0 测试场景",
            options=list(SCENARIO_LABELS),
            format_func=SCENARIO_LABELS.__getitem__,
            help="该选项只控制 Fake Provider 返回哪一种固定结果。",
        )
        submitted = st.form_submit_button("保存回答并生成演示诊断", type="primary")

    if submitted:
        try:
            diagnosis = service.submit_answer(
                session_id=session.session_id,
                answer_text=answer,
                scenario=scenario,
                request_id=str(uuid4()),
            )
        except (InputValidationError, InvalidSessionState, LookupError) as error:
            st.error(str(error))
        else:
            st.session_state.last_diagnosis = diagnosis
            st.rerun()


def _render_start_form(service: LearningService) -> None:
    st.subheader("今天想检验哪个知识点？")
    with st.form("start-session-form"):
        concept = st.text_input("知识点", placeholder="例如：梯度下降、递归、机会成本")
        learning_goal = st.text_input("学习目标（可选）")
        learner_level = st.selectbox(
            "当前自评（可选）",
            options=("", "beginner", "intermediate", "advanced"),
            format_func=lambda value: {
                "": "暂不填写",
                "beginner": "初学",
                "intermediate": "有一些基础",
                "advanced": "希望测试深入理解",
            }[value],
        )
        submitted = st.form_submit_button("开始费曼挑战", type="primary")

    if submitted:
        try:
            session = service.start_session(
                concept=concept,
                learning_goal=learning_goal or None,
                learner_level=learner_level or None,
                request_id=str(uuid4()),
            )
        except (InputValidationError, LookupError) as error:
            st.error(str(error))
        else:
            st.session_state.current_session_id = session.session_id
            st.session_state.pop("last_diagnosis", None)
            st.session_state.pop("draft_answer", None)
            st.rerun()


def _render_diagnosis(result: DiagnosisView) -> None:
    st.divider()
    st.subheader("演示诊断结果")
    if result.status != "succeeded":
        st.error(ERROR_MESSAGES.get(result.error_code or "", "诊断暂时失败。"))
        st.info("你的回答已经保存，可以直接重试，不需要重新输入。")
        st.code(result.error_code or "UNKNOWN_ERROR", language=None)
        return

    assert result.observation is not None
    assert result.decision is not None
    assert result.next_action is not None

    st.success(result.decision.reason)
    left, right = st.columns(2)
    left.metric("掌握状态", result.decision.mastery_level.value)
    right.metric("证据置信度", f"{result.decision.confidence:.0%}")

    st.markdown("#### 当前回答中的证据")
    if result.observation.evidence:
        for item in result.observation.evidence:
            st.markdown(f"- {item.claim} — “{item.answer_excerpt}”")
    else:
        st.caption("当前没有足够的正向理解证据。")

    if result.observation.gaps:
        st.markdown("#### 需要补充的内容")
        for gap in result.observation.gaps:
            st.markdown(f"- {gap.description}（{gap.severity.value}）")

    if result.observation.possible_misconceptions:
        st.markdown("#### 可能的误区")
        for misconception in result.observation.possible_misconceptions:
            st.markdown(f"- {misconception.description} — “{misconception.answer_excerpt}”")

    st.markdown("#### 下一步")
    st.info(result.next_action.instruction)
    if result.observation.limitations:
        with st.expander("为什么这个判断仍有限制？"):
            for limitation in result.observation.limitations:
                st.markdown(f"- {limitation}")

    with st.expander("查看演示协议详情"):
        st.json(result.envelope.model_dump(mode="json") if result.envelope else {})


def _render_result_actions(service: LearningService, result: DiagnosisView) -> None:
    if result.retryable:
        retry_scenario = st.selectbox(
            "重试时使用的 Fake 场景",
            options=list(SCENARIO_LABELS),
            index=0,
            format_func=SCENARIO_LABELS.__getitem__,
        )
        if st.button("使用已保存回答重试", type="primary"):
            st.session_state.last_diagnosis = service.retry(
                explanation_id=result.explanation_id,
                scenario=retry_scenario,
                request_id=str(uuid4()),
            )
            st.rerun()

    if st.button("开始新的测试"):
        _reset_flow()
        st.rerun()


def _render_history(service: LearningService) -> None:
    st.subheader("历史记录")
    history = service.list_history()
    if not history:
        st.info("还没有学习记录。完成一次演示测试后会显示在这里。")
        return

    labels = {
        item.session_id: (
            f"{item.started_at.astimezone().strftime('%Y-%m-%d %H:%M')} · "
            f"{item.concept} · {item.mastery_level or item.status}"
        )
        for item in history
    }
    selected = st.selectbox(
        "选择一条记录",
        options=[item.session_id for item in history],
        format_func=labels.__getitem__,
    )
    result = service.get_session_diagnosis(selected)
    if result is None:
        st.caption("该会话尚未产生诊断结果。")
    else:
        st.markdown(f"**保存的回答：** {result.answer_text}")
        _render_diagnosis(result)


def _render_system_status(*, settings: Settings, database_version: int) -> None:
    st.subheader("系统状态")
    st.success("应用、配置和数据库迁移均已就绪。")
    st.json(
        {
            "environment": settings.app_env,
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "database_version": database_version,
            "content_logging": settings.log_content_enabled,
            "telemetry": settings.telemetry_enabled,
            "api_key_displayed": False,
        }
    )
    st.caption("外部模型尚未实现；Fake Provider 不访问网络，也不产生 API 费用。")


def _reset_flow() -> None:
    for key in ("current_session_id", "last_diagnosis", "draft_answer"):
        st.session_state.pop(key, None)
