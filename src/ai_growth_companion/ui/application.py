"""Chinese-first Streamlit interface for the evidence-based learning loop."""

from collections import defaultdict
from html import escape
from uuid import uuid4

import streamlit as st

from ai_growth_companion.application.health import HealthReport, HealthState
from ai_growth_companion.application.learning_service import LearningService
from ai_growth_companion.application.models import DiagnosisView, HistoryItem
from ai_growth_companion.config import Settings
from ai_growth_companion.domain.session import InputValidationError, InvalidSessionState
from ai_growth_companion.ui.presentation import (
    SCENARIO_LABELS,
    action_heading,
    action_label,
    error_message,
    local_datetime,
    mastery_label,
    severity_label,
    status_label,
)
from ai_growth_companion.ui.theme import apply_design_system

PAGES = ("今日", "学习", "进度", "系统")


def render_application(
    service: LearningService,
    *,
    settings: Settings,
    health_report: HealthReport,
) -> None:
    """Render product navigation while keeping business behavior in the service."""
    apply_design_system()
    if "active_page" not in st.session_state:
        st.session_state.active_page = "今日"

    with st.sidebar:
        st.markdown(
            '<div class="brand"><span class="brand-mark">S</span><span>AI SelfLearner</span></div>',
            unsafe_allow_html=True,
        )
        page = st.radio(
            "主导航",
            PAGES,
            label_visibility="collapsed",
            key="active_page",
        )
        st.markdown(
            '<div class="sidebar-status"><span class="status-dot"></span>'
            "Fake Provider 已就绪<br>本地模式 · 零 API 费用</div>",
            unsafe_allow_html=True,
        )

    if page == "今日":
        _render_today(service)
    elif page == "学习":
        _render_learning_flow(service)
    elif page == "进度":
        _render_progress(service)
    else:
        _render_system_status(settings=settings, health_report=health_report)


def _render_today(service: LearningService) -> None:
    history = service.list_history()
    st.markdown('<div class="eyebrow">今天 · 你的学习工作台</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">AI SelfLearner</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-copy">不是告诉你答案，而是验证你是否真正掌握。'
        "从一次自己的解释开始，找到证据、缺口和下一步。</p>",
        unsafe_allow_html=True,
    )

    if not history:
        st.markdown(
            """
            <div class="empty-state">
              <div class="section-label">今日学习</div>
              <h2>还没有学习记录</h2>
              <p>选择一个你正在学习的概念，先用自己的话解释。系统会依据回答中的证据，告诉你理解到了哪里。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            "开始第一次学习",
            type="primary",
            on_click=_navigate,
            args=("学习",),
        )
        return

    latest = history[0]
    latest_result = service.get_session_diagnosis(latest.session_id)
    latest_diagnosed = next((item for item in history if item.mastery_level), None)
    latest_mastery = mastery_label(latest_diagnosed.mastery_level if latest_diagnosed else None)
    if latest.status == "questioned":
        next_step = "继续回答上次的费曼问题"
    elif latest_result and latest_result.next_action:
        next_step = action_heading(latest_result.next_action.action_type)
    else:
        next_step = "继续完成上一次学习"
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">继续学习</div>', unsafe_allow_html=True)
    st.subheader(latest.concept)
    st.caption(f"最近记录于 {local_datetime(latest.started_at)}")
    left, right = st.columns(2)
    left.markdown(f"**当前判断**<br>{latest_mastery}", unsafe_allow_html=True)
    right.markdown(f"**建议行动**<br>{next_step}", unsafe_allow_html=True)
    if latest.status == "questioned":
        st.button(
            "继续上次学习",
            type="primary",
            on_click=_resume_session,
            args=(latest.session_id,),
        )
    else:
        st.button("查看并继续", type="primary", on_click=_navigate, args=("进度",))

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">最近主题</div>', unsafe_allow_html=True)
    for item in history[:4]:
        _history_row(item)


def _render_learning_flow(service: LearningService) -> None:
    if "current_session_id" not in st.session_state:
        _render_start_form(service)
        return

    try:
        session = service.get_session(st.session_state.current_session_id)
    except LookupError:
        st.error("当前学习记录无法读取，请重新开始。")
        _reset_flow()
        return

    st.markdown(
        f'<div class="eyebrow">学习主题 · {escape(session.concept)}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<h1 class="hero-title">先说出你真正理解的部分</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-copy">不必追求标准答案，也不用查资料。'
        "清楚写下你理解的机制、边界和例子。</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="question-panel"><div class="question-kicker">费曼问题</div>'
        f"<p>{escape(session.question_text)}</p></div>",
        unsafe_allow_html=True,
    )

    result = st.session_state.get("last_diagnosis")
    if isinstance(result, DiagnosisView):
        _render_diagnosis(result)
        _render_result_actions(service, result)
        return

    with st.form("answer-form"):
        answer = st.text_area(
            "你的解释",
            key="draft_answer",
            height=220,
            placeholder="例如：它是什么、为什么有效、在什么情况下不成立……",
        )
        with st.expander("测试不同诊断结果（仅 Fake Provider）"):
            scenario = st.selectbox(
                "诊断场景",
                options=list(SCENARIO_LABELS),
                format_func=SCENARIO_LABELS.__getitem__,
                help="只控制本地 Fake Provider 的固定返回，不会访问任何真实模型。",
            )
        submitted = st.form_submit_button("提交解释并查看诊断", type="primary")

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

    st.button("更换学习主题", on_click=_reset_flow)


def _render_start_form(service: LearningService) -> None:
    st.markdown('<div class="eyebrow">学习 · 新的检验</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">今天想真正弄懂什么？</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-copy">从一个具体概念开始。我们会提出一个问题，'
        "再依据你自己的解释判断掌握证据。</p>",
        unsafe_allow_html=True,
    )
    with st.form("start-session-form"):
        concept = st.text_input("学习主题", placeholder="例如：梯度下降、递归、机会成本")
        learning_goal = st.text_input(
            "这次希望弄清什么？（可选）",
            placeholder="例如：能向同事解释它为什么有效",
        )
        learner_level = st.selectbox(
            "你对它的熟悉程度（可选）",
            options=("", "beginner", "intermediate", "advanced"),
            format_func=lambda value: {
                "": "暂不填写",
                "beginner": "刚开始接触",
                "intermediate": "已有一些基础",
                "advanced": "希望检验深入理解",
            }[value],
        )
        submitted = st.form_submit_button("生成费曼问题", type="primary")

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
            _set_current_session(session.session_id)
            st.rerun()


def _render_diagnosis(result: DiagnosisView) -> None:
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">诊断结果 · 基于本次解释</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">你的理解到了哪里？</h1>', unsafe_allow_html=True)
    st.caption("系统只根据本次解释中的证据给出判断，不把一次回答当作永久结论。")

    if result.status != "succeeded":
        message = error_message(result.error_code)
        st.markdown(
            f'<div class="error-panel"><h3>这次诊断没有完成</h3><p>{escape(message)}</p></div>',
            unsafe_allow_html=True,
        )
        st.error(message)
        st.info("无需重新输入。你可以使用已保存的解释直接重试。")
        st.caption(f"错误标识：{result.error_code or 'UNKNOWN_ERROR'}")
        return

    assert result.observation is not None
    assert result.decision is not None
    assert result.next_action is not None

    decision = result.decision
    observation = result.observation
    mastery = mastery_label(decision.mastery_level)
    badge_class = "badge-good" if decision.mastery_level.value == "solid" else "badge-warn"
    evidence_items = (
        "".join(
            f"<li>{escape(item.claim)}<br><span class='row-meta'>"
            f"“{escape(item.answer_excerpt)}”</span></li>"
            for item in observation.evidence
        )
        or "<li class='row-meta'>当前解释中还没有足够的正向掌握证据。</li>"
    )

    gap_parts = [
        f"<li>{escape(item.description)} <span class='row-meta'>"
        f"· {severity_label(item.severity)}</span></li>"
        for item in observation.gaps
    ]
    gap_parts.extend(
        f"<li><strong>可能的误区：</strong>{escape(item.description)}"
        f"<br><span class='row-meta'>“{escape(item.answer_excerpt)}”</span></li>"
        for item in observation.possible_misconceptions
    )
    gap_items = "".join(gap_parts) or "<li class='row-meta'>本次没有发现明显缺口或误区。</li>"

    st.markdown(
        '<div class="diagnosis-panel">'
        '<div class="diagnosis-head">'
        f'<span class="badge {badge_class}">{escape(mastery)}</span>'
        f"<h2>{escape(mastery)}</h2><p>{escape(decision.reason)}</p></div>"
        '<div class="diagnosis-grid">'
        f'<div class="diagnosis-cell"><h3>你已经讲清楚的部分</h3><ul>{evidence_items}</ul></div>'
        f'<div class="diagnosis-cell"><h3>还缺少的关键点</h3><ul>{gap_items}</ul></div>'
        "</div>"
        '<div class="next-step">'
        f"<strong>{escape(action_heading(result.next_action.action_type))}</strong>"
        f"<p>{escape(result.next_action.instruction)}</p></div></div>",
        unsafe_allow_html=True,
    )

    with st.expander("查看原始解释与判断边界"):
        st.markdown("**你提交的解释**")
        st.write(result.answer_text)
        if observation.limitations:
            st.markdown("**这次判断的限制**")
            for limitation in observation.limitations:
                st.markdown(f"- {limitation}")
        st.caption(
            f"Mastery Protocol：{decision.protocol_version} · "
            f"Learning Policy：{result.next_action.policy_version}"
        )


def _render_result_actions(service: LearningService, result: DiagnosisView) -> None:
    if result.retryable:
        retry_scenario = st.selectbox(
            "重试时使用的 Fake 场景",
            options=list(SCENARIO_LABELS),
            index=0,
            format_func=SCENARIO_LABELS.__getitem__,
        )
        if st.button("使用已保存的解释重试", type="primary"):
            try:
                st.session_state.last_diagnosis = service.retry(
                    explanation_id=result.explanation_id,
                    scenario=retry_scenario,
                    request_id=str(uuid4()),
                )
            except (InvalidSessionState, LookupError) as error:
                st.error(str(error))
            else:
                st.rerun()
        st.button("开始其他主题", on_click=_reset_flow)
        return

    assert result.next_action is not None
    action_type = result.next_action.action_type.value
    if action_type == "re_explain":
        st.button(
            action_label(action_type),
            type="primary",
            on_click=_restart_concept,
            args=(service, result.concept),
        )
    else:
        st.button(
            f"{action_label(action_type)} · 后续开放",
            type="primary",
            disabled=True,
            help="当前后端尚未提供对应活动；本轮不扩展核心学习协议。",
        )
        st.button(
            "用新的解释继续验证",
            on_click=_restart_concept,
            args=(service, result.concept),
        )
    st.button("开始其他主题", on_click=_reset_flow)


def _render_progress(service: LearningService) -> None:
    history = service.list_history()
    st.markdown('<div class="eyebrow">进度 · 有证据的学习记录</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">看见理解如何变化</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-copy">这里只展示真实发生过的解释与诊断，不用虚构百分比包装掌握程度。</p>',
        unsafe_allow_html=True,
    )
    if not history:
        st.info("还没有可展示的学习记录。完成第一次解释后，这里会形成主题时间线。")
        st.button("开始第一次学习", type="primary", on_click=_navigate, args=("学习",))
        return

    grouped: dict[str, list[HistoryItem]] = defaultdict(list)
    for item in history:
        grouped[item.concept].append(item)

    st.markdown('<div class="section-label">主题概览</div>', unsafe_allow_html=True)
    for concept, records in grouped.items():
        latest = records[0]
        latest_diagnosed = next((item for item in records if item.mastery_level), None)
        latest_mastery = mastery_label(latest_diagnosed.mastery_level if latest_diagnosed else None)
        explanation_count = sum(
            item.status in {"answered", "diagnosed", "diagnosis_failed"} for item in records
        )
        st.markdown(
            '<div class="progress-row">'
            f'<div><div class="row-title">{escape(concept)}</div>'
            f'<div class="row-meta">最近：{escape(local_datetime(latest.started_at))}</div></div>'
            f'<div><div class="row-title">{explanation_count}</div>'
            '<div class="row-meta">次解释</div></div>'
            f'<div><div class="row-title">{escape(latest_mastery)}</div>'
            '<div class="row-meta">最新判断</div></div>'
            f'<div><div class="row-title">{escape(status_label(latest.status))}</div>'
            '<div class="row-meta">记录状态</div></div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    selected_concept = st.selectbox("查看主题时间线", options=list(grouped))
    records = grouped[selected_concept]
    labels = {
        item.session_id: (
            f"{local_datetime(item.started_at)} · {mastery_label(item.mastery_level)}"
        )
        for item in records
    }
    selected_index = next(
        (
            index
            for index, item in enumerate(records)
            if item.status in {"diagnosed", "diagnosis_failed"}
        ),
        0,
    )
    selected_session = st.selectbox(
        "选择一次解释",
        options=[item.session_id for item in records],
        index=selected_index,
        format_func=labels.__getitem__,
    )
    result = service.get_session_diagnosis(selected_session)
    if result is None:
        st.info("这次学习尚未产生诊断结果。")
    else:
        _render_diagnosis(result)


def _render_system_status(*, settings: Settings, health_report: HealthReport) -> None:
    st.markdown('<div class="eyebrow">系统 · 本地运行状态</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">系统状态</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-copy">运行环境、数据与 Provider 的只读检查。'
        "不会展示 API Key 或学习内容。</p>",
        unsafe_allow_html=True,
    )

    states = (
        ("应用进程", health_report.liveness.detail, health_report.liveness.state),
        ("SQLite 数据库", health_report.readiness.detail, health_report.readiness.state),
        (
            "Fake Provider",
            health_report.provider_dependency.detail,
            health_report.provider_dependency.state,
        ),
    )
    for name, detail, state in states:
        badge = "正常" if state is HealthState.HEALTHY else "需注意"
        badge_class = "badge-good" if state is HealthState.HEALTHY else "badge-warn"
        st.markdown(
            '<div class="status-row">'
            f'<div class="row-title">{escape(name)}</div>'
            f'<div class="row-meta">{escape(detail)}</div>'
            f'<span class="badge {badge_class}">{badge}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    left, right = st.columns(2)
    left.markdown("**运行模式**")
    left.write(settings.app_env)
    left.markdown("**Provider / Model**")
    left.write(f"{settings.llm_provider} / {settings.llm_model}")
    right.markdown("**数据库迁移版本**")
    right.write(f"{health_report.database_version} / {health_report.available_database_version}")
    right.markdown("**内容日志 / 遥测**")
    right.write(
        f"{'开启' if settings.log_content_enabled else '关闭'} / "
        f"{'开启' if settings.telemetry_enabled else '关闭'}"
    )
    st.caption("当前仅使用 Fake Provider，不访问外部模型，不产生 API 费用。")


def _history_row(item: HistoryItem) -> None:
    st.markdown(
        '<div class="progress-row">'
        f'<div><div class="row-title">{escape(item.concept)}</div>'
        f'<div class="row-meta">{escape(local_datetime(item.started_at))}</div></div>'
        '<div><div class="row-title">1</div><div class="row-meta">次解释</div></div>'
        f'<div><div class="row-title">{escape(mastery_label(item.mastery_level))}</div>'
        '<div class="row-meta">掌握证据</div></div>'
        f'<div><div class="row-title">{escape(status_label(item.status))}</div>'
        '<div class="row-meta">状态</div></div></div>',
        unsafe_allow_html=True,
    )


def _navigate(page: str) -> None:
    st.session_state.active_page = page


def _set_current_session(session_id: str) -> None:
    st.session_state.current_session_id = session_id
    st.session_state.pop("last_diagnosis", None)
    st.session_state.pop("draft_answer", None)


def _restart_concept(service: LearningService, concept: str) -> None:
    session = service.start_session(concept=concept, request_id=str(uuid4()))
    _set_current_session(session.session_id)
    _navigate("学习")


def _resume_session(session_id: str) -> None:
    _set_current_session(session_id)
    _navigate("学习")


def _reset_flow() -> None:
    for key in ("current_session_id", "last_diagnosis", "draft_answer"):
        st.session_state.pop(key, None)
    _navigate("学习")
