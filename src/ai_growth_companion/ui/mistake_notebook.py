"""Service-backed mistake notebook page for weak and incorrect explanations."""

from collections.abc import Callable, Iterable, Sequence
from html import escape
from uuid import uuid4

import streamlit as st

from ai_growth_companion.application.learning_service import LearningService
from ai_growth_companion.application.models import WrongItemView
from ai_growth_companion.domain.wrong_items import WrongItemStatus, WrongItemType
from ai_growth_companion.ui.presentation import (
    local_datetime,
    severity_label,
    wrong_item_status_label,
    wrong_item_type_label,
)

_STATUS_OPTIONS: tuple[WrongItemStatus | None, ...] = (None, *WrongItemStatus)
_TYPE_OPTIONS: tuple[WrongItemType | None, ...] = (None, *WrongItemType)
_SORT_OPTIONS = ("updated", "created", "concept")


def render_mistake_notebook(
    service: LearningService,
    *,
    open_review: Callable[[str], None],
    resume_learning: Callable[[str], None],
) -> None:
    """Render list, filters, traceable detail, and service-backed actions."""
    st.markdown('<div class="eyebrow">错题 · 需要再次弄清的地方</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">把薄弱点变成下一次进步</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-copy">每条记录都来自真实回答和诊断证据。你可以回看原解释、'
        "安排复习，或围绕同一知识点重新作答。</p>",
        unsafe_allow_html=True,
    )

    if notice := st.session_state.pop("wrong_status_notice", None):
        st.success(str(notice))
    if error := st.session_state.pop("wrong_status_error", None):
        st.error(str(error))

    selected_id = st.session_state.get("selected_wrong_item_id")
    if selected_id:
        _render_detail(
            service,
            wrong_item_id=str(selected_id),
            open_review=open_review,
            resume_learning=resume_learning,
        )
        return

    try:
        with st.spinner("正在读取错题记录……"):
            all_items = service.list_wrong_items(limit=100)
    except Exception:
        st.error("错题记录暂时无法读取，请稍后重试。")
        if st.button("重新加载错题", type="primary"):
            st.rerun()
        return

    if not all_items:
        st.markdown(
            """
            <div class="empty-state">
              <div class="section-label">错题本</div>
              <h2>目前没有需要整理的错题</h2>
              <p>当一次解释存在关键缺口、明确误区或证据不足时，系统会把对应的原题、回答和诊断证据保存在这里。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    _render_summary(all_items)
    status_filter, type_filter, sort_order = _render_filters()
    visible_items = _filter_and_sort(
        all_items,
        status=status_filter,
        error_type=type_filter,
        sort_order=sort_order,
    )

    st.markdown('<div class="section-label">错题记录</div>', unsafe_allow_html=True)
    if not visible_items:
        st.info("当前筛选条件下没有错题。调整筛选条件即可查看其他记录。")
        return

    for item in visible_items:
        _render_list_item(
            service,
            item,
            open_review=open_review,
        )


def _render_summary(items: Sequence[WrongItemView]) -> None:
    open_count = sum(item.status is WrongItemStatus.OPEN for item in items)
    snoozed_count = sum(item.status is WrongItemStatus.SNOOZED for item in items)
    mastered_count = sum(item.status is WrongItemStatus.MASTERED for item in items)
    st.markdown(
        '<div class="workspace-summary">'
        f"<div><strong>{len(items)}</strong><span>全部记录</span></div>"
        f"<div><strong>{open_count}</strong><span>待处理</span></div>"
        f"<div><strong>{snoozed_count}</strong><span>已暂缓</span></div>"
        f"<div><strong>{mastered_count}</strong><span>已掌握</span></div>"
        "</div>",
        unsafe_allow_html=True,
    )


def _render_filters() -> tuple[WrongItemStatus | None, WrongItemType | None, str]:
    status_column, type_column, sort_column = st.columns(3)
    status = status_column.selectbox(
        "当前状态",
        options=_STATUS_OPTIONS,
        format_func=lambda value: "全部状态" if value is None else wrong_item_status_label(value),
        key="wrong_status_filter",
    )
    error_type = type_column.selectbox(
        "错题类型",
        options=_TYPE_OPTIONS,
        format_func=lambda value: "全部类型" if value is None else wrong_item_type_label(value),
        key="wrong_type_filter",
    )
    sort_order = sort_column.selectbox(
        "排序方式",
        options=_SORT_OPTIONS,
        format_func={
            "updated": "最近更新",
            "created": "最新创建",
            "concept": "知识点名称",
        }.__getitem__,
        key="wrong_sort_order",
    )
    return status, error_type, sort_order


def _filter_and_sort(
    items: Sequence[WrongItemView],
    *,
    status: WrongItemStatus | None,
    error_type: WrongItemType | None,
    sort_order: str,
) -> list[WrongItemView]:
    visible = [
        item
        for item in items
        if (status is None or item.status is status)
        and (error_type is None or item.error_type is error_type)
    ]
    if sort_order == "concept":
        return sorted(visible, key=lambda item: (item.concept.casefold(), item.updated_at))
    if sort_order == "created":
        return sorted(visible, key=lambda item: item.created_at, reverse=True)
    return sorted(visible, key=lambda item: item.updated_at, reverse=True)


def _render_list_item(
    service: LearningService,
    item: WrongItemView,
    *,
    open_review: Callable[[str], None],
) -> None:
    status_class = "badge-good" if item.status is WrongItemStatus.MASTERED else "badge-warn"
    with st.container(key=f"wrong_item_{item.wrong_item_id}"):
        st.markdown(
            '<div class="mistake-row">'
            '<div class="mistake-row-main">'
            f'<span class="badge {status_class}">'
            f"{escape(wrong_item_status_label(item.status))}</span>"
            f'<span class="mistake-type">{escape(wrong_item_type_label(item.error_type))}</span>'
            f"<h3>{escape(item.concept)}</h3>"
            f"<p>{escape(item.error_summary)}</p>"
            f'<div class="row-meta">更新于 {escape(local_datetime(item.updated_at))}</div>'
            "</div></div>",
            unsafe_allow_html=True,
        )
        detail, review, status = st.columns([1.15, 1.15, 1.25])
        if detail.button(
            "查看详情",
            key=f"wrong_detail_{item.wrong_item_id}",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.selected_wrong_item_id = item.wrong_item_id
            st.rerun()
        review.button(
            "安排复习",
            key=f"wrong_review_{item.wrong_item_id}",
            disabled=item.status is WrongItemStatus.MASTERED,
            on_click=open_review,
            args=(item.wrong_item_id,),
            use_container_width=True,
        )
        if item.status is WrongItemStatus.MASTERED:
            status.button(
                "恢复待处理",
                key=f"wrong_reopen_{item.wrong_item_id}",
                on_click=_change_status,
                args=(service, item.wrong_item_id, WrongItemStatus.OPEN),
                use_container_width=True,
            )
        else:
            status.button(
                "标记已掌握",
                key=f"wrong_master_{item.wrong_item_id}",
                on_click=_change_status,
                args=(service, item.wrong_item_id, WrongItemStatus.MASTERED),
                use_container_width=True,
            )


def _render_detail(
    service: LearningService,
    *,
    wrong_item_id: str,
    open_review: Callable[[str], None],
    resume_learning: Callable[[str], None],
) -> None:
    if st.button("返回错题列表", icon=":material/arrow_back:"):
        st.session_state.pop("selected_wrong_item_id", None)
        st.rerun()

    try:
        with st.spinner("正在读取错题详情……"):
            item = service.get_wrong_item(wrong_item_id)
    except LookupError:
        st.error("这条错题记录不存在或已经无法读取。")
        if st.button("回到错题列表", type="primary"):
            st.session_state.pop("selected_wrong_item_id", None)
            st.rerun()
        return
    except Exception:
        st.error("错题详情暂时无法读取，请稍后重试。")
        if st.button("重试读取", type="primary"):
            st.rerun()
        return

    status_class = "badge-good" if item.status is WrongItemStatus.MASTERED else "badge-warn"
    st.markdown(
        '<div class="mistake-detail-head">'
        '<div class="question-kicker">错题详情</div>'
        f'<span class="badge {status_class}">{escape(wrong_item_status_label(item.status))}</span>'
        f"<h2>{escape(item.concept)}</h2>"
        f"<p>{escape(wrong_item_type_label(item.error_type))} · {escape(item.error_summary)}</p>"
        f'<div class="row-meta">记录于 {escape(local_datetime(item.created_at))}</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label">当时的题目与回答</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="source-answer-grid">'
        "<section><h3>原题</h3>"
        f"<p>{escape(item.question_text)}</p></section>"
        "<section><h3>你的原回答</h3>"
        f"<p>{escape(item.answer_text)}</p></section>"
        "</div>",
        unsafe_allow_html=True,
    )

    observation = item.evidence
    evidence_items = _observation_items(
        ((evidence.claim, f"“{evidence.answer_excerpt}”") for evidence in observation.evidence),
        empty_copy="当时的回答里没有足够的正向掌握证据。",
    )
    gap_items = _observation_items(
        (
            (gap.description, f"重要程度：{severity_label(gap.severity)}")
            for gap in observation.gaps
        ),
        empty_copy="诊断没有记录额外的关键缺口。",
    )
    misconception_items = _observation_items(
        (
            (misconception.description, f"“{misconception.answer_excerpt}”")
            for misconception in observation.possible_misconceptions
        ),
        empty_copy="诊断没有记录有证据支持的明确误区。",
    )
    st.markdown(
        '<div class="mistake-evidence-grid">'
        f"<section><h3>已经讲清楚的证据</h3><ul>{evidence_items}</ul></section>"
        f"<section><h3>缺少的关键点</h3><ul>{gap_items}</ul></section>"
        "</div>"
        '<div class="mistake-correction">'
        f"<section><h3>可能的误区</h3><ul>{misconception_items}</ul></section>"
        '<section class="correct-idea"><h3>正确思路</h3>'
        f"<p>{escape(item.correction_text)}</p></section>"
        "</div>",
        unsafe_allow_html=True,
    )

    if observation.limitations:
        with st.expander("查看诊断边界"):
            for limitation in observation.limitations:
                st.markdown(f"- {limitation}")

    st.markdown(
        '<div class="section-label mistake-actions-label">下一步</div>', unsafe_allow_html=True
    )
    review, relearn, status = st.columns(3)
    review.button(
        "安排复习",
        key=f"wrong_detail_review_{item.wrong_item_id}",
        type="primary",
        disabled=item.status is WrongItemStatus.MASTERED,
        on_click=open_review,
        args=(item.wrong_item_id,),
        use_container_width=True,
    )
    if relearn.button(
        "围绕此知识点重新作答",
        key=f"wrong_detail_reanswer_{item.wrong_item_id}",
        use_container_width=True,
    ):
        try:
            with st.spinner("正在生成新的费曼问题……"):
                session = service.start_session(
                    concept=item.concept,
                    request_id=str(uuid4()),
                )
        except (LookupError, ValueError) as error:
            st.error(str(error))
        else:
            resume_learning(session.session_id)
            st.rerun()
    target_status = (
        WrongItemStatus.OPEN
        if item.status is WrongItemStatus.MASTERED
        else WrongItemStatus.MASTERED
    )
    status.button(
        "恢复待处理" if target_status is WrongItemStatus.OPEN else "标记已掌握",
        key=f"wrong_detail_status_{item.wrong_item_id}",
        on_click=_change_status,
        args=(service, item.wrong_item_id, target_status),
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


def _change_status(
    service: LearningService,
    wrong_item_id: str,
    status: WrongItemStatus,
) -> None:
    try:
        service.update_wrong_item_status(
            wrong_item_id=wrong_item_id,
            status=status,
            request_id=str(uuid4()),
        )
    except (LookupError, ValueError) as error:
        st.session_state.wrong_status_error = str(error)
    else:
        st.session_state.wrong_status_notice = (
            "已标记为掌握，关联复习项目已同步更新。"
            if status is WrongItemStatus.MASTERED
            else "已恢复为待处理。"
        )
