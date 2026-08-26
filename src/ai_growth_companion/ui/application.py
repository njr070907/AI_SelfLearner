"""Chinese-first Streamlit interface for the evidence-based learning loop."""

from collections import defaultdict
from collections.abc import Sequence
from html import escape
from uuid import uuid4

import streamlit as st

from ai_growth_companion.application.document_library import DocumentLibraryService
from ai_growth_companion.application.health import HealthReport, HealthState
from ai_growth_companion.application.learning_service import LearningService
from ai_growth_companion.application.models import DiagnosisView, HistoryItem, WorkspaceSnapshot
from ai_growth_companion.config import Settings
from ai_growth_companion.domain.events import ConceptState
from ai_growth_companion.domain.feedback import FeedbackVerdict
from ai_growth_companion.domain.session import InputValidationError, InvalidSessionState
from ai_growth_companion.domain.wrong_items import WrongItemStatus
from ai_growth_companion.providers.fake import FakeScenario
from ai_growth_companion.ui.document_library import render_document_library
from ai_growth_companion.ui.mistake_notebook import render_mistake_notebook
from ai_growth_companion.ui.motion import render_pointer_glow
from ai_growth_companion.ui.presentation import (
    SCENARIO_LABELS,
    action_heading,
    action_label,
    concept_trend_label,
    error_message,
    feedback_verdict_label,
    local_datetime,
    mastery_label,
    severity_label,
    status_label,
)
from ai_growth_companion.ui.review_queue import render_review_queue
from ai_growth_companion.ui.shell import (
    render_search_results,
    render_sidebar,
    render_top_toolbar,
)
from ai_growth_companion.ui.state import current_preferences, initialize_ui_state
from ai_growth_companion.ui.theme import apply_design_system

FAKE_SCENARIO_OPTIONS = tuple(SCENARIO_LABELS)
DEFAULT_FAKE_SCENARIO_INDEX = FAKE_SCENARIO_OPTIONS.index(FakeScenario.PARTIAL)


def render_application(
    service: LearningService,
    *,
    document_library: DocumentLibraryService | None = None,
    settings: Settings,
    health_report: HealthReport,
) -> None:
    """Render product navigation while keeping business behavior in the service."""
    initialize_ui_state()
    preferences = current_preferences()
    apply_design_system(preferences)
    page = str(st.session_state.active_page)
    provider_label = "Fake Provider" if settings.is_fake_mode else "DeepSeek Provider"
    provider_detail = "本地模式 · 零 API 费用" if settings.is_fake_mode else "固定模型 · 按次调用"
    render_sidebar(
        preferences=preferences,
        active_page=page,
        navigate=_navigate,
        provider_label=provider_label,
        provider_detail=provider_detail,
    )
    search_query = render_top_toolbar(active_page=page, preferences=preferences)
    render_search_results(
        history=service.list_history(),
        query=search_query,
        open_result=_open_search_result,
    )

    view_slugs = {
        "今日": "today",
        "学习": "learn",
        "资料库": "documents",
        "错题": "mistakes",
        "复习": "review",
        "进度": "progress",
        "系统": "system",
    }
    with st.container(key=f"view-{view_slugs.get(page, 'today')}"):
        if page == "今日":
            _render_today(service)
        elif page == "学习":
            _render_learning_flow(service, settings=settings)
        elif page == "资料库":
            if document_library is None:
                st.error("资料库服务尚未配置。")
            else:
                render_document_library(document_library)
        elif page == "错题":
            render_mistake_notebook(
                service,
                open_review=_open_review_from_wrong,
                resume_learning=_resume_session,
            )
        elif page == "复习":
            render_review_queue(service, settings=settings)
        elif page == "进度":
            _render_progress(service)
        else:
            _render_system_status(settings=settings, health_report=health_report)
    render_pointer_glow()


def _render_today(service: LearningService) -> None:
    snapshot = service.get_workspace_snapshot(limit=100)
    history = snapshot.history
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

    _render_workspace_shortcuts(snapshot)

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
    elif latest.status in {"diagnosed", "diagnosis_failed"}:
        st.button(
            "继续本次会话",
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


def _render_workspace_shortcuts(snapshot: WorkspaceSnapshot) -> None:
    open_wrong_count = sum(item.status is WrongItemStatus.OPEN for item in snapshot.wrong_items)
    st.markdown(
        '<div class="workspace-summary home-summary">'
        f"<div><strong>{len(snapshot.history)}</strong><span>学习记录</span></div>"
        f"<div><strong>{open_wrong_count}</strong><span>待处理错题</span></div>"
        f"<div><strong>{len(snapshot.review_queue)}</strong><span>今日到期复习</span></div>"
        f"<div><strong>{len(snapshot.concept_states)}</strong><span>长期状态主题</span></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    learn, mistakes, review, progress = st.columns(4)
    learn.button(
        "继续学习",
        type="primary",
        on_click=_navigate,
        args=("学习",),
        use_container_width=True,
    )
    mistakes.button(
        "查看错题",
        on_click=_navigate,
        args=("错题",),
        use_container_width=True,
    )
    review.button(
        "开始复习",
        on_click=_navigate,
        args=("复习",),
        use_container_width=True,
    )
    progress.button(
        "查看进度",
        on_click=_navigate,
        args=("进度",),
        use_container_width=True,
    )


def _render_learning_flow(service: LearningService, *, settings: Settings) -> None:
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
    if not isinstance(result, DiagnosisView) or result.session_id != session.session_id:
        result = service.get_session_diagnosis(session.session_id)
        if result is not None:
            st.session_state.last_diagnosis = result
    if isinstance(result, DiagnosisView):
        _render_diagnosis(result)
        _render_diagnosis_feedback(service, result)
        _render_result_actions(service, result, settings=settings)
        return

    with st.form("answer-form"):
        answer = st.text_area(
            "你的解释",
            key="draft_answer",
            height=220,
            placeholder="例如：它是什么、为什么有效、在什么情况下不成立……",
        )
        scenario = FakeScenario.PARTIAL
        if settings.is_fake_mode:
            with st.expander("测试不同诊断结果（仅 Fake Provider）"):
                scenario = st.selectbox(
                    "诊断场景",
                    options=FAKE_SCENARIO_OPTIONS,
                    index=DEFAULT_FAKE_SCENARIO_INDEX,
                    format_func=SCENARIO_LABELS.__getitem__,
                    help="只控制本地 Fake Provider 的固定返回，不会访问任何真实模型。",
                )
        else:
            st.caption(
                "当前使用 DeepSeek `deepseek-v4-flash-vision-exp` 进行结构化证据提取；"
                "不会显示 Fake 场景，也不会自动重试。"
            )
        submitted = st.form_submit_button("提交解释并查看诊断", type="primary")

    if submitted:
        try:
            with st.spinner("正在保存解释并生成诊断……"):
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
            with st.spinner("正在创建学习会话并生成费曼问题……"):
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
    answer_type = "首次解释" if result.answer_type == "main" else "后续解释"
    st.caption(
        f"第 {result.sequence_no} 次回答 · {answer_type}。"
        "系统只根据本次解释中的证据给出判断，不把一次回答当作永久结论。"
    )

    if result.status != "succeeded":
        message = error_message(result.error_code)
        st.markdown(
            f'<div class="error-panel"><h3>这次诊断没有完成</h3><p>{escape(message)}</p></div>',
            unsafe_allow_html=True,
        )
        st.error(message)
        st.info("无需重新输入。你可以使用已保存的解释直接重试。")
        st.markdown("**已保存的原始回答**")
        st.write(result.answer_text)
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

    gap_items = (
        "".join(
            f"<li>{escape(item.description)} <span class='row-meta'>"
            f"· {severity_label(item.severity)}</span></li>"
            for item in observation.gaps
        )
        or "<li class='row-meta'>本次没有发现明确的关键缺口。</li>"
    )
    misconception_items = (
        "".join(
            f"<li>{escape(item.description)}"
            f"<br><span class='row-meta'>“{escape(item.answer_excerpt)}”</span></li>"
            for item in observation.possible_misconceptions
        )
        or "<li class='row-meta'>本次没有发现有回答证据支持的明显误区。</li>"
    )

    st.markdown(
        '<div class="diagnosis-panel">'
        '<div class="diagnosis-head">'
        '<div class="question-kicker">当前掌握判断</div>'
        f'<span class="badge {badge_class}">{escape(mastery)}</span>'
        f"<h2>{escape(mastery)}</h2><p>{escape(decision.reason)}</p></div>"
        '<div class="diagnosis-grid">'
        f'<div class="diagnosis-cell"><h3>你已经讲清楚的证据</h3><ul>{evidence_items}</ul></div>'
        f'<div class="diagnosis-cell"><h3>缺少的关键点</h3><ul>{gap_items}</ul></div>'
        "</div>"
        '<div class="misconception-band">'
        f"<h3>可能的误区</h3><ul>{misconception_items}</ul></div>"
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


def _render_diagnosis_feedback(
    service: LearningService,
    result: DiagnosisView,
) -> None:
    """Let the learner append feedback without mutating the original diagnosis."""
    if result.status != "succeeded" or result.diagnosis_id is None:
        return

    sent_key = f"diagnosis_feedback_sent_{result.diagnosis_id}"
    if notice := st.session_state.get(sent_key):
        st.success(str(notice))
        return

    with st.expander("这次诊断符合你的理解吗？"):
        st.caption("反馈会作为新的学习事件保存，不会覆盖原诊断或原回答。")
        with st.form(f"diagnosis-feedback-{result.diagnosis_id}"):
            verdict = st.selectbox(
                "你的判断",
                options=tuple(FeedbackVerdict),
                format_func=feedback_verdict_label,
                key=f"feedback_verdict_{result.diagnosis_id}",
            )
            note = st.text_area(
                "补充说明或修正",
                key=f"feedback_note_{result.diagnosis_id}",
                height=120,
                placeholder="如果诊断不准确，请写清被遗漏或判断错误的具体部分。",
            )
            submitted = st.form_submit_button("提交诊断反馈")

        if submitted:
            if verdict is FeedbackVerdict.INACCURATE and not note.strip():
                st.error("选择“诊断不准确”时，请写下具体修正。")
                return
            request_key = f"feedback_request_{result.diagnosis_id}"
            request_id = str(st.session_state.setdefault(request_key, str(uuid4())))
            try:
                with st.spinner("正在保存你的反馈……"):
                    if verdict is FeedbackVerdict.INACCURATE:
                        service.record_user_correction(
                            diagnosis_id=result.diagnosis_id,
                            correction=note,
                            request_id=request_id,
                        )
                    else:
                        service.submit_feedback(
                            diagnosis_id=result.diagnosis_id,
                            verdict=verdict,
                            note=note or None,
                            request_id=request_id,
                        )
            except (LookupError, ValueError) as error:
                st.error(str(error))
            else:
                st.session_state.pop(request_key, None)
                st.session_state[sent_key] = "反馈已保存，长期状态已由后端重新生成。"
                st.rerun()


def _render_follow_up_form(
    service: LearningService,
    result: DiagnosisView,
    *,
    settings: Settings,
) -> None:
    """Submit another explanation without leaving the current learning session."""
    assert result.next_action is not None
    st.markdown('<div class="section-label">继续本次会话</div>', unsafe_allow_html=True)
    st.subheader(action_heading(result.next_action.action_type))
    st.write(result.next_action.instruction)

    with st.form(f"follow-up-form-{result.sequence_no}"):
        answer = st.text_area(
            "你的后续解释",
            key=f"follow_up_answer_{result.sequence_no}",
            height=190,
            placeholder="根据上面的建议补充机制、边界，或换一种说法重新解释……",
        )
        scenario = FakeScenario.PARTIAL
        if settings.is_fake_mode:
            with st.expander("测试后续诊断结果（仅 Fake Provider）"):
                scenario = st.selectbox(
                    "后续诊断场景",
                    options=FAKE_SCENARIO_OPTIONS,
                    index=DEFAULT_FAKE_SCENARIO_INDEX,
                    format_func=SCENARIO_LABELS.__getitem__,
                    help="只控制本地 Fake Provider 的固定返回，不会访问任何真实模型。",
                    key=f"follow_up_scenario_{result.sequence_no}",
                )
        submitted = st.form_submit_button("提交后续解释", type="primary")

    if submitted:
        try:
            with st.spinner("正在保存后续解释并更新诊断……"):
                diagnosis = service.submit_follow_up(
                    session_id=result.session_id,
                    answer_text=answer,
                    scenario=scenario,
                    request_id=str(uuid4()),
                )
        except (InputValidationError, InvalidSessionState, LookupError) as error:
            st.error(str(error))
        else:
            st.session_state.last_diagnosis = diagnosis
            st.session_state.pop("show_follow_up_form", None)
            st.rerun()

    st.button("暂不继续", on_click=_hide_follow_up_form)


def _render_success_actions(service: LearningService, result: DiagnosisView) -> None:
    """Offer service-backed next turns without interpreting the policy in the UI."""
    assert result.next_action is not None
    try:
        session = service.get_session(result.session_id)
    except LookupError:
        st.error("当前学习记录无法读取，请重新开始。")
        return

    if not session.can_submit_follow_up:
        st.warning("当前会话暂时不能继续提交，请稍后重新打开。")
        return

    action_type = result.next_action.action_type.value
    st.button(
        action_label(action_type),
        type="primary",
        on_click=_show_follow_up_form,
    )
    if action_type != "re_explain":
        st.button("重新解释", on_click=_show_follow_up_form)


def _render_result_actions(
    service: LearningService,
    result: DiagnosisView,
    *,
    settings: Settings,
) -> None:
    if result.retryable:
        retry_scenario = FakeScenario.PARTIAL
        if settings.is_fake_mode:
            retry_scenario = st.selectbox(
                "重试时使用的 Fake 场景",
                options=FAKE_SCENARIO_OPTIONS,
                index=DEFAULT_FAKE_SCENARIO_INDEX,
                format_func=SCENARIO_LABELS.__getitem__,
            )
        else:
            st.caption(
                "真实模式重试仍使用固定 DeepSeek 模型；系统不会自动重试，"
                "只有你点击下面的按钮才会再次请求。"
            )
        if st.button("使用已保存的解释重试", type="primary"):
            try:
                with st.spinner("正在使用已保存的解释重试诊断……"):
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

    if st.session_state.get("show_follow_up_form"):
        _render_follow_up_form(service, result, settings=settings)
    else:
        _render_success_actions(service, result)
    st.button("开始其他主题", on_click=_reset_flow)


def _render_progress(service: LearningService) -> None:
    snapshot = service.get_workspace_snapshot(limit=100)
    history = snapshot.history
    st.markdown('<div class="eyebrow">进度 · 有证据的学习记录</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">看见理解如何变化</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-copy">这里只展示后端根据真实解释、反馈和复测生成的长期状态，'
        "不用虚构百分比包装掌握程度。</p>",
        unsafe_allow_html=True,
    )
    if not history:
        st.info("还没有可展示的学习记录。完成第一次解释后，这里会形成主题时间线。")
        st.button("开始第一次学习", type="primary", on_click=_navigate, args=("学习",))
        return

    concept_names = _concept_name_map(service, history)
    _render_longitudinal_states(snapshot.concept_states, concept_names=concept_names)

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
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
    concept_options = list(grouped)
    requested_concept = st.session_state.pop("progress_concept", None)
    concept_index = (
        concept_options.index(requested_concept) if requested_concept in concept_options else 0
    )
    selected_concept = st.selectbox(
        "查看主题时间线",
        options=concept_options,
        index=concept_index,
    )
    records = grouped[selected_concept]
    labels = {
        item.session_id: (
            f"{local_datetime(item.started_at)} · {mastery_label(item.mastery_level)}"
        )
        for item in records
    }
    requested_session = st.session_state.pop("progress_session_id", None)
    selected_index = next(
        (index for index, item in enumerate(records) if item.session_id == requested_session),
        next(
            (
                index
                for index, item in enumerate(records)
                if item.status in {"diagnosed", "diagnosis_failed"}
            ),
            0,
        ),
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
        _render_diagnosis_feedback(service, result)


def _concept_name_map(
    service: LearningService,
    history: Sequence[HistoryItem],
) -> dict[str, str]:
    names: dict[str, str] = {}
    for item in history:
        try:
            session = service.get_session(item.session_id)
        except LookupError:
            continue
        names[session.concept_id] = session.concept
    return names


def _render_longitudinal_states(
    states: Sequence[ConceptState],
    *,
    concept_names: dict[str, str],
) -> None:
    st.markdown('<div class="section-label">长期状态</div>', unsafe_allow_html=True)
    if not states:
        st.info("当前还没有可展示的长期状态投影。")
        return

    ordered = sorted(states, key=lambda state: state.updated_at, reverse=True)
    for state in ordered:
        concept = concept_names.get(state.concept_id, f"知识点 {state.concept_id[:8]}")
        st.markdown(
            '<div class="concept-state-row">'
            f'<div><div class="row-title">{escape(concept)}</div>'
            f'<div class="row-meta">{escape(concept_trend_label(state.trend))}</div></div>'
            f'<div><div class="row-title">{escape(mastery_label(state.mastery_level))}</div>'
            '<div class="row-meta">后端掌握判断</div></div>'
            f'<div><div class="row-title">{state.evidence_count}</div>'
            '<div class="row-meta">条诊断证据</div></div>'
            f'<div><div class="row-title">{state.open_wrong_item_count}</div>'
            '<div class="row-meta">条待处理错题</div></div></div>',
            unsafe_allow_html=True,
        )

    labels = {
        state.concept_id: concept_names.get(
            state.concept_id,
            f"知识点 {state.concept_id[:8]}",
        )
        for state in ordered
    }
    selected_id = st.selectbox(
        "查看长期状态详情",
        options=[state.concept_id for state in ordered],
        format_func=labels.__getitem__,
    )
    selected = next(state for state in ordered if state.concept_id == selected_id)
    score_delta = f"{selected.score_delta:+d}"
    st.markdown(
        '<div class="state-detail-grid">'
        f"<div><strong>{escape(concept_trend_label(selected.trend))}</strong>"
        f"<span>证据评分变化 {score_delta}</span></div>"
        f"<div><strong>{selected.open_wrong_item_count} / {selected.wrong_item_count}</strong>"
        "<span>待处理 / 全部错题</span></div>"
        f"<div><strong>{selected.review_success_count} / {selected.review_attempt_count}</strong>"
        "<span>复测正确 / 全部复测</span></div>"
        f"<div><strong>{selected.feedback_inaccurate_count} / {selected.feedback_count}</strong>"
        "<span>修正反馈 / 全部反馈</span></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    if selected.repeated_misconceptions:
        st.markdown("**重复出现的误区**")
        for misconception in selected.repeated_misconceptions:
            st.markdown(f"- {misconception}")
    else:
        st.caption("当前没有重复出现的误区记录。")
    st.caption(f"长期状态最后更新：{local_datetime(selected.updated_at)}")


def _render_system_status(*, settings: Settings, health_report: HealthReport) -> None:
    st.markdown('<div class="eyebrow">系统 · 本地运行状态</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">系统状态</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-copy">运行环境、数据与 Provider 的只读检查。'
        "不会展示 API Key 或学习内容。</p>",
        unsafe_allow_html=True,
    )

    provider_label = "Fake Provider" if settings.is_fake_mode else "DeepSeek Provider"
    states = (
        ("应用进程", health_report.liveness.detail, health_report.liveness.state),
        ("SQLite 数据库", health_report.readiness.detail, health_report.readiness.state),
        (
            provider_label,
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
    if settings.is_fake_mode:
        st.caption("当前仅使用 Fake Provider，不访问外部模型，不产生 API 费用。")
    else:
        st.caption(
            "当前使用固定 DeepSeek 模型进行证据提取；每次调用都由你的提交操作触发，"
            "系统不会自动重试。"
        )


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


def _open_search_result(session_id: str, concept: str) -> None:
    st.session_state.progress_session_id = session_id
    st.session_state.progress_concept = concept
    st.session_state.ui_search_query = ""
    _navigate("进度")


def _open_review_from_wrong(wrong_item_id: str) -> None:
    st.session_state.review_wrong_item_id = wrong_item_id
    _navigate("复习")


def _set_current_session(session_id: str) -> None:
    st.session_state.current_session_id = session_id
    st.session_state.pop("last_diagnosis", None)
    st.session_state.pop("draft_answer", None)
    st.session_state.pop("show_follow_up_form", None)


def _show_follow_up_form() -> None:
    st.session_state.show_follow_up_form = True


def _hide_follow_up_form() -> None:
    st.session_state.pop("show_follow_up_form", None)


def _resume_session(session_id: str) -> None:
    _set_current_session(session_id)
    _navigate("学习")


def _reset_flow() -> None:
    flow_keys = {
        "current_session_id",
        "last_diagnosis",
        "draft_answer",
        "show_follow_up_form",
    }
    flow_keys.update(
        key
        for key in st.session_state
        if str(key).startswith(("follow_up_answer_", "follow_up_scenario_"))
    )
    for key in flow_keys:
        st.session_state.pop(key, None)
    _navigate("学习")
