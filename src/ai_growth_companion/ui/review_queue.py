"""Service-backed due review queue and retest interaction."""

from collections.abc import Iterable, Sequence
from html import escape
from uuid import uuid4

import streamlit as st

from ai_growth_companion.application.learning_service import LearningService
from ai_growth_companion.application.models import ReviewQueueItemView, ReviewResultView
from ai_growth_companion.config import Settings
from ai_growth_companion.domain.review import ReviewAttemptStatus, ReviewOutcome
from ai_growth_companion.domain.session import InputValidationError, InvalidSessionState
from ai_growth_companion.domain.wrong_items import WrongItemStatus
from ai_growth_companion.providers.fake import FakeScenario
from ai_growth_companion.ui.presentation import (
    SCENARIO_LABELS,
    action_heading,
    error_message,
    local_datetime,
    mastery_label,
    review_attempt_status_label,
    review_outcome_label,
    severity_label,
)

_SCENARIO_OPTIONS = tuple(SCENARIO_LABELS)
_DEFAULT_SCENARIO_INDEX = _SCENARIO_OPTIONS.index(FakeScenario.PARTIAL)


def render_review_queue(service: LearningService, *, settings: Settings) -> None:
    """Render the persisted due queue and one idempotent retest at a time."""
    st.markdown('<div class="eyebrow">复习 · 今日到期队列</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">用一次复测检验真正留下的理解</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-copy">题目来自你的薄弱回答。提交后，下一次复习时间完全由后端'
        "调度结果决定，本页只展示状态和建议。</p>",
        unsafe_allow_html=True,
    )

    if notice := st.session_state.pop("review_notice", None):
        st.success(str(notice))
    if error := st.session_state.pop("review_error", None):
        st.error(str(error))

    try:
        with st.spinner("正在刷新今日复习队列……"):
            queue = service.list_review_queue(limit=100)
    except Exception:
        st.error("复习队列暂时无法读取，请稍后重试。")
        if st.button("重新加载复习队列", type="primary"):
            st.rerun()
        return

    result = st.session_state.get("review_result")
    if not isinstance(result, ReviewResultView):
        result = None
    _sync_requested_item(queue, result=result)
    completed_count = len(st.session_state.get("review_completed_attempt_ids", ()))
    _render_review_summary(queue, completed_count=completed_count)

    if result is not None:
        _render_result(service, result, queue=queue, settings=settings)
        return

    if not queue:
        st.markdown(
            """
            <div class="empty-state">
              <div class="section-label">今日复习</div>
              <h2>今天没有到期的复习任务</h2>
              <p>完成一次存在薄弱点的解释后，后端会创建复习项目；到期时会自动出现在这里。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button("去学习新主题", type="primary", on_click=_navigate, args=("学习",))
        return

    current = _current_item(queue)
    _render_current_retest(service, current, settings=settings)
    _render_queue_list(queue, current_id=current.review_item_id)


def _sync_requested_item(
    queue: Sequence[ReviewQueueItemView],
    *,
    result: ReviewResultView | None,
) -> None:
    requested_wrong_id = st.session_state.pop("review_wrong_item_id", None)
    if requested_wrong_id is not None:
        st.session_state.review_source_wrong_item_id = requested_wrong_id
        match = next(
            (item for item in queue if item.wrong_item_id == requested_wrong_id),
            None,
        )
        if match is None:
            st.info("这条错题当前不在今日到期队列中，可能尚未到期或已经掌握。")
        else:
            st.session_state.current_review_item_id = match.review_item_id
            if result is not None and result.review_item.review_item_id != match.review_item_id:
                st.session_state.pop("review_result", None)


def _render_review_summary(
    queue: Sequence[ReviewQueueItemView],
    *,
    completed_count: int,
) -> None:
    remaining_count = len(queue)
    total_count = completed_count + remaining_count
    next_due = local_datetime(queue[0].due_at) if queue else "今日已清空"
    st.markdown(
        '<div class="workspace-summary review-summary">'
        f"<div><strong>{remaining_count}</strong><span>今日到期</span></div>"
        f"<div><strong>{completed_count}</strong><span>本轮已完成</span></div>"
        f"<div><strong>{total_count}</strong><span>本轮任务总数</span></div>"
        "<div><strong class='summary-date'>"
        f"{escape(next_due)}</strong><span>队首到期时间</span></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    if total_count:
        st.progress(
            completed_count / total_count,
            text=f"当前复习进度：已完成 {completed_count}，还剩 {remaining_count}",
        )


def _current_item(queue: Sequence[ReviewQueueItemView]) -> ReviewQueueItemView:
    selected_id = st.session_state.get("current_review_item_id")
    selected = next((item for item in queue if item.review_item_id == selected_id), None)
    if selected is not None:
        return selected
    current = queue[0]
    st.session_state.current_review_item_id = current.review_item_id
    return current


def _render_current_retest(
    service: LearningService,
    item: ReviewQueueItemView,
    *,
    settings: Settings,
) -> None:
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">当前复习题</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="review-question">'
        '<div class="question-kicker">费曼复测</div>'
        f"<h2>{escape(item.concept)}</h2>"
        f"<p>{escape(item.question_text)}</p>"
        '<div class="review-question-meta">'
        f"<span>到期：{escape(local_datetime(item.due_at))}</span>"
        f"<span>已复测 {item.attempt_count} 次</span>"
        f"<span>上次结果：{escape(review_outcome_label(item.last_result))}</span>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    answer_key = f"review_answer_{item.review_item_id}"
    with st.form(f"review-form-{item.review_item_id}"):
        answer = st.text_area(
            "你的复测回答",
            key=answer_key,
            height=210,
            placeholder="重新解释核心机制、适用边界，并给出一个例子……",
        )
        scenario = FakeScenario.PARTIAL
        if settings.is_fake_mode:
            with st.expander("测试复测结果（仅 Fake Provider）"):
                scenario = st.selectbox(
                    "复测场景",
                    options=_SCENARIO_OPTIONS,
                    index=_DEFAULT_SCENARIO_INDEX,
                    format_func=SCENARIO_LABELS.__getitem__,
                    key=f"review_scenario_{item.review_item_id}",
                    help="只控制本地 Fake Provider，不访问真实模型。",
                )
        submitted = st.form_submit_button("提交复测", type="primary")

    if submitted:
        _submit_retest(
            service,
            item=item,
            answer=answer,
            scenario=scenario,
        )

    postpone, mastered = st.columns(2)
    postpone.button(
        "延后复习",
        key=f"review_postpone_{item.review_item_id}",
        disabled=True,
        help="当前正式服务契约没有手动延后接口；前端不会自行修改到期时间。",
        use_container_width=True,
    )
    mastered.button(
        "标记已掌握",
        key=f"review_master_{item.review_item_id}",
        on_click=_mark_mastered,
        args=(service, item),
        use_container_width=True,
    )
    st.caption("复习间隔和下一次日期由后端调度；当前契约尚不支持手动延后。")


def _submit_retest(
    service: LearningService,
    *,
    item: ReviewQueueItemView,
    answer: str,
    scenario: FakeScenario,
) -> None:
    st.session_state[f"review_saved_answer_{item.review_item_id}"] = answer
    request_key = f"review_request_id_{item.review_item_id}"
    request_id = str(st.session_state.setdefault(request_key, str(uuid4())))
    try:
        with st.spinner("正在保存回答并生成复测反馈……"):
            result = service.submit_retest(
                review_item_id=item.review_item_id,
                answer_text=answer,
                scenario=scenario,
                request_id=request_id,
            )
    except (InputValidationError, InvalidSessionState, LookupError, ValueError) as error:
        st.error(str(error))
        return
    st.session_state.pop(request_key, None)
    st.session_state.review_result = result
    _remember_completed_attempt(result)
    st.rerun()


def _render_result(
    service: LearningService,
    result: ReviewResultView,
    *,
    queue: Sequence[ReviewQueueItemView],
    settings: Settings,
) -> None:
    item = result.review_item
    answer = str(st.session_state.get(f"review_saved_answer_{item.review_item_id}", ""))
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">本次复测反馈</div>', unsafe_allow_html=True)

    if result.status is not ReviewAttemptStatus.SUCCEEDED:
        message = error_message(result.error_code)
        st.markdown(
            f'<div class="error-panel"><h3>这次复测没有完成</h3><p>{escape(message)}</p></div>',
            unsafe_allow_html=True,
        )
        st.error(message)
        st.info("你的复测回答已经保存，本页也会保留输入，可直接使用原回答重试。")
        st.markdown("**已保存的复测回答**")
        st.write(answer)
        st.caption(
            f"{review_attempt_status_label(result.status)} · 错误标识："
            f"{result.error_code or 'UNKNOWN_ERROR'}"
        )
        _render_retry(service, result, answer=answer, settings=settings)
        return

    assert result.observation is not None
    assert result.decision is not None
    assert result.next_action is not None
    outcome = review_outcome_label(result.result)
    badge_class = "badge-good" if result.result is ReviewOutcome.CORRECT else "badge-warn"
    observation = result.observation
    evidence_items = _observation_items(
        ((evidence.claim, f"“{evidence.answer_excerpt}”") for evidence in observation.evidence),
        empty_copy="本次回答还没有提供足够的正向证据。",
    )
    gap_items = _observation_items(
        (
            (gap.description, f"重要程度：{severity_label(gap.severity)}")
            for gap in observation.gaps
        ),
        empty_copy="本次没有发现额外的关键缺口。",
    )
    misconception_items = _observation_items(
        (
            (misconception.description, f"“{misconception.answer_excerpt}”")
            for misconception in observation.possible_misconceptions
        ),
        empty_copy="本次没有发现有证据支持的明确误区。",
    )
    st.markdown(
        '<div class="review-result">'
        '<div class="review-result-head">'
        f'<span class="badge {badge_class}">{escape(outcome)}</span>'
        f"<h2>{escape(mastery_label(result.decision.mastery_level))}</h2>"
        f"<p>{escape(result.decision.reason)}</p></div>"
        '<div class="review-result-grid">'
        f"<section><h3>已经讲清楚</h3><ul>{evidence_items}</ul></section>"
        f"<section><h3>仍需补充</h3><ul>{gap_items}</ul></section>"
        "</div>"
        '<div class="review-result-misconception">'
        f"<h3>可能的误区</h3><ul>{misconception_items}</ul></div>"
        '<div class="next-step">'
        f"<strong>{escape(action_heading(result.next_action.action_type))}</strong>"
        f"<p>{escape(result.next_action.instruction)}</p></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.success(
        f"后端已重新安排下次复习：{local_datetime(item.due_at)}（间隔 {item.interval_days} 天）。"
    )
    with st.expander("查看本次复测原回答"):
        st.write(answer)

    next_item, mastered = st.columns(2)
    next_item.button(
        "下一题" if queue else "完成本轮复习",
        type="primary",
        on_click=_continue_after_result,
        args=(queue,),
        use_container_width=True,
    )
    mastered.button(
        "标记这个错题为已掌握",
        on_click=_mark_mastered,
        args=(service, item),
        use_container_width=True,
    )


def _render_retry(
    service: LearningService,
    result: ReviewResultView,
    *,
    answer: str,
    settings: Settings,
) -> None:
    scenario = FakeScenario.PARTIAL
    if settings.is_fake_mode:
        scenario = st.selectbox(
            "重试复测场景",
            options=_SCENARIO_OPTIONS,
            index=_DEFAULT_SCENARIO_INDEX,
            format_func=SCENARIO_LABELS.__getitem__,
            key=f"review_retry_scenario_{result.attempt_id}",
        )
    if st.button("使用已保存回答重试复测", type="primary"):
        _submit_retest(
            service,
            item=result.review_item,
            answer=answer,
            scenario=scenario,
        )
    st.button("返回今日队列", on_click=_clear_result)


def _render_queue_list(
    queue: Sequence[ReviewQueueItemView],
    *,
    current_id: str,
) -> None:
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">今日复习队列</div>', unsafe_allow_html=True)
    for index, item in enumerate(queue, start=1):
        selected = item.review_item_id == current_id
        with st.container(key=f"review_queue_{item.review_item_id}"):
            details, action = st.columns([4, 1], vertical_alignment="center")
            details.markdown(
                '<div class="queue-row">'
                f"<strong>{index}. {escape(item.concept)}</strong>"
                f"<span>{escape(local_datetime(item.due_at))} · "
                f"{escape(review_outcome_label(item.last_result))}</span></div>",
                unsafe_allow_html=True,
            )
            action.button(
                "当前题" if selected else "开始这题",
                key=f"review_select_{item.review_item_id}",
                disabled=selected,
                on_click=_select_review_item,
                args=(item.review_item_id,),
                use_container_width=True,
            )


def _observation_items(
    items: Iterable[tuple[str, str]],
    *,
    empty_copy: str,
) -> str:
    rendered = "".join(
        f"<li>{escape(title)}<br><span class='row-meta'>{escape(detail)}</span></li>"
        for title, detail in items
    )
    return rendered or f'<li class="row-meta">{escape(empty_copy)}</li>'


def _remember_completed_attempt(result: ReviewResultView) -> None:
    if result.status is not ReviewAttemptStatus.SUCCEEDED:
        return
    attempts = list(st.session_state.get("review_completed_attempt_ids", ()))
    if result.attempt_id not in attempts:
        attempts.append(result.attempt_id)
    st.session_state.review_completed_attempt_ids = attempts


def _mark_mastered(
    service: LearningService,
    item: ReviewQueueItemView,
) -> None:
    try:
        service.update_wrong_item_status(
            wrong_item_id=item.wrong_item_id,
            status=WrongItemStatus.MASTERED,
            request_id=str(uuid4()),
        )
    except (LookupError, ValueError) as error:
        st.session_state.review_error = str(error)
    else:
        st.session_state.review_notice = "已标记为掌握，关联复习项目已从队列移除。"
        st.session_state.pop("review_result", None)
        st.session_state.pop("current_review_item_id", None)


def _continue_after_result(queue: Sequence[ReviewQueueItemView]) -> None:
    st.session_state.pop("review_result", None)
    st.session_state.pop("current_review_item_id", None)
    if queue:
        st.session_state.current_review_item_id = queue[0].review_item_id


def _select_review_item(review_item_id: str) -> None:
    st.session_state.current_review_item_id = review_item_id
    st.session_state.pop("review_result", None)


def _clear_result() -> None:
    st.session_state.pop("review_result", None)


def _navigate(page: str) -> None:
    st.session_state.active_page = page
