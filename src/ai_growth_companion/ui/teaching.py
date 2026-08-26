"""Teaching workspace: upload knowledge, generate a lesson, then study it."""

from collections.abc import Callable
from html import escape
from uuid import uuid4

import streamlit as st

from ai_growth_companion.application.document_library import DocumentLibraryService
from ai_growth_companion.application.teaching_service import (
    TeachingInputError,
    TeachingLessonView,
    TeachingService,
)
from ai_growth_companion.providers.base import ProviderError

StartLesson = Callable[[str, str | None, str | None], str | None]


def render_teaching_workspace(
    teaching_service: TeachingService,
    document_library: DocumentLibraryService,
    *,
    start_lesson: StartLesson,
) -> None:
    """Render the conventional teaching flow before the diagnostic flow."""
    st.markdown('<div class="eyebrow">教学 · 从资料生成学习内容</div>', unsafe_allow_html=True)
    st.markdown(
        '<h1 class="hero-title">先把知识讲清楚，再检查你是否理解</h1>', unsafe_allow_html=True
    )
    st.markdown(
        '<p class="hero-copy">上传讲义、笔记或教材后，系统会把资料整理成一份可阅读的导学。'
        "你先学习导学，再进入费曼理解检查。</p>",
        unsafe_allow_html=True,
    )

    documents = document_library.list_documents()
    if not documents:
        st.info("资料库还没有知识文件。请先到“资料库”上传 PDF、Markdown 或 TXT。")
        st.button(
            "去资料库上传知识",
            type="primary",
            on_click=lambda: setattr(st.session_state, "active_page", "资料库"),
            key="teaching_open_documents_empty",
        )
        return

    document_labels = {document.document_id: document.filename for document in documents}
    with st.container(border=True):
        st.markdown(
            '<div class="section-label">第 1 步 · 选择知识来源</div>', unsafe_allow_html=True
        )
        selected_ids = tuple(
            st.multiselect(
                "选择一份或多份资料",
                options=tuple(document_labels),
                format_func=document_labels.__getitem__,
                key="teaching_selected_documents",
                help="教学内容只会根据你选择的资料生成，并保留来源文件记录。",
            )
        )
        topic = st.text_input(
            "这次要学习的知识主题",
            key="teaching_topic",
            placeholder="例如：函数极限、梯度下降、机会成本",
        )
        goal = st.text_input(
            "学习目标（可选）",
            key="teaching_goal",
            placeholder="例如：能解释定义、机制、边界并做一道新题",
        )
        level = st.selectbox(
            "当前基础（可选）",
            options=("", "beginner", "intermediate", "advanced"),
            format_func=lambda value: {
                "": "暂不填写",
                "beginner": "刚开始接触",
                "intermediate": "已有一些基础",
                "advanced": "希望学习得更深入",
            }[value],
            key="teaching_level",
        )
        if st.button(
            "生成我的教学内容",
            type="primary",
            disabled=not selected_ids or not topic.strip(),
            key="teaching_generate",
        ):
            try:
                with st.spinner("正在阅读资料并生成结构化导学……"):
                    lesson = teaching_service.generate_lesson(
                        topic=topic,
                        document_ids=selected_ids,
                        learning_goal=goal or None,
                        learner_level=level or None,
                        request_id=str(uuid4()),
                    )
            except (TeachingInputError, ProviderError, LookupError) as error:
                st.error(str(error))
            else:
                st.session_state.teaching_lesson_id = lesson.lesson_id
                st.rerun()

    lesson_id = st.session_state.get("teaching_lesson_id")
    if not isinstance(lesson_id, str):
        _render_teaching_steps()
        return
    try:
        lesson = teaching_service.get_lesson(lesson_id)
    except LookupError as error:
        st.error(str(error))
        st.session_state.pop("teaching_lesson_id", None)
        return
    _render_lesson(lesson, start_lesson=start_lesson)


def _render_teaching_steps() -> None:
    with st.container(border=True):
        st.markdown('<div class="section-label">你的学习流程</div>', unsafe_allow_html=True)
        st.markdown(
            "1. 选择知识资料  →  2. 生成结构化导学  →  "
            "3. 阅读定义、机制、边界和例子  →  4. 进入费曼理解检查"
        )
        st.caption("AI 负责整理资料；掌握程度仍由后续证据和 Mastery Engine 判断。")


def _render_lesson(lesson: TeachingLessonView, *, start_lesson: StartLesson) -> None:
    content = lesson.lesson
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">第 2 步 · 阅读教学内容</div>', unsafe_allow_html=True)
    st.markdown(f"## {escape(content.title)}")
    source_names = ", ".join(escape(source.filename) for source in content.sources)
    st.caption(
        f"来源：{source_names} · 生成方式：{escape(lesson.provider)} / {escape(lesson.model_name)}"
    )
    st.info(content.summary)

    with st.container(border=True):
        st.markdown("**学习目标**")
        for objective in content.learning_objectives:
            st.markdown(f"- {objective}")

    for index, section in enumerate(content.sections, start=1):
        with st.container(border=True):
            st.markdown(f"### {index}. {escape(section.title)}")
            st.write(section.explanation)
            for point in section.key_points:
                st.markdown(f"- {point}")
            if section.example:
                st.markdown(f"**例子/练习：** {section.example}")

    with st.container(border=True):
        st.markdown("**学完后先想一想**")
        for question in content.check_questions:
            st.markdown(f"- {question}")
        st.caption("读完后，再进入费曼理解检查；系统会根据你的回答判断哪里真正掌握了。")
        if st.button("第 3 步：进入费曼理解检查", type="primary", key="lesson_start_check"):
            error = start_lesson(
                content.topic,
                st.session_state.get("teaching_goal") or None,
                st.session_state.get("teaching_level") or None,
            )
            if error:
                st.error(error)
            else:
                st.rerun()
