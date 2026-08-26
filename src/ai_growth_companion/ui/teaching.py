"""Teaching workspace: upload knowledge, generate a lesson, then study it."""

from collections.abc import Callable, Sequence
from html import escape
from uuid import uuid4

import streamlit as st

from ai_growth_companion.application.document_library import DocumentLibraryService
from ai_growth_companion.application.teaching_service import (
    TeachingActivityAttemptView,
    TeachingInputError,
    TeachingLessonView,
    TeachingService,
)
from ai_growth_companion.providers.base import ProviderError
from ai_growth_companion.schemas.teaching import LessonSource

StartLesson = Callable[[str, str | None, str | None], str | None]


def render_teaching_workspace(
    teaching_service: TeachingService,
    document_library: DocumentLibraryService,
    *,
    start_lesson: StartLesson,
) -> None:
    """Render a conventional lesson with explanations and interactive checks."""
    st.markdown('<div class="eyebrow">教学 · 从资料生成课程</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">跟着课程学，再做互动练习</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-copy">上传讲义、笔记或教材后，系统会把资料整理成一份常规课程。'
        "课程包含讲解、例子和即时小测；掌握检测是后续可选步骤。</p>",
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
        _render_existing_lessons(teaching_service)
        _render_teaching_steps()
        return
    try:
        lesson = teaching_service.get_lesson(lesson_id)
    except LookupError as error:
        st.error(str(error))
        st.session_state.pop("teaching_lesson_id", None)
        return
    _render_lesson(
        lesson,
        teaching_service=teaching_service,
        start_lesson=start_lesson,
    )


def _render_existing_lessons(teaching_service: TeachingService) -> None:
    """Offer database-backed courses so a refresh does not hide prior learning."""
    lessons = teaching_service.list_lessons(limit=12)
    if not lessons:
        return

    st.markdown('<div class="section-label">我的课程</div>', unsafe_allow_html=True)
    for lesson in lessons:
        activity_count = len(lesson.lesson.interactive_checks)
        completed_count = lesson.progress.completed_activity_count
        status = "已完成" if lesson.progress.completed_at is not None else "学习中"
        with st.container(border=True):
            st.markdown(f"**{escape(lesson.lesson.title)}**")
            st.caption(
                f"主题：{escape(lesson.lesson.topic)} · {status} · "
                f"互动进度 {completed_count}/{activity_count}"
            )
            if st.button(
                "打开课程" if lesson.progress.completed_at is not None else "继续课程",
                key=f"teaching_resume_{lesson.lesson_id}",
                type="primary" if lesson.progress.completed_at is None else "secondary",
            ):
                st.session_state.teaching_lesson_id = lesson.lesson_id
                st.rerun()


def _render_teaching_steps() -> None:
    with st.container(border=True):
        st.markdown('<div class="section-label">你的学习流程</div>', unsafe_allow_html=True)
        st.markdown("1. 选择知识资料  →  2. 生成课程  →  3. 阅读讲解和例子  →  4. 完成互动小测")
        st.caption("AI 负责整理课程；掌握程度仍由互动结果和后续掌握检测共同判断。")


def _render_lesson(
    lesson: TeachingLessonView,
    *,
    teaching_service: TeachingService,
    start_lesson: StartLesson,
) -> None:
    content = lesson.lesson
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">第 2 步 · 阅读课程</div>', unsafe_allow_html=True)
    st.markdown(f"## {escape(content.title)}")
    source_names = ", ".join(escape(source.filename) for source in content.sources)
    st.caption(
        f"来源：{source_names} · 生成方式：{escape(lesson.provider)} / {escape(lesson.model_name)}"
    )
    activity_count = len(content.interactive_checks)
    completed_count = lesson.progress.completed_activity_count
    st.progress(
        completed_count / activity_count if activity_count else 1.0,
        text=f"课程互动进度：{completed_count}/{activity_count}",
    )
    if lesson.progress.completed_at is not None:
        st.success("这门课程已经完成，可以继续复习或进行可选掌握检测。")
    st.info(content.summary)

    section_count = len(content.sections)
    section_key = f"teaching_section_index_{lesson.lesson_id}"
    if section_key not in st.session_state:
        st.session_state[section_key] = min(lesson.progress.current_section, section_count - 1)
    section_index = max(0, min(int(st.session_state[section_key]), section_count - 1))
    st.markdown("**课程目录**")
    for index, section in enumerate(content.sections):
        marker = "▶" if index == section_index else "○"
        st.markdown(f"{marker} 第 {index + 1} 节 · {escape(section.title)}")

    with st.container(border=True):
        st.markdown("**学习目标**")
        for objective in content.learning_objectives:
            st.markdown(f"- {objective}")

    section = content.sections[section_index]
    with st.container(border=True):
        st.markdown(f"### 第 {section_index + 1} 节 · {escape(section.title)}")
        st.write(section.explanation)
        for point in section.key_points:
            st.markdown(f"- {point}")
        if section.example:
            st.markdown(f"**例子/练习：** {section.example}")
        section_sources = _source_names(content.sources, section.source_document_ids)
        if section_sources:
            st.caption(f"本节来源：{section_sources}")

    previous, next_step = st.columns(2)
    if previous.button(
        "上一节",
        disabled=section_index == 0,
        key=f"teaching_previous_{lesson.lesson_id}_{section_index}",
        use_container_width=True,
    ):
        teaching_service.update_position(
            lesson_id=lesson.lesson_id,
            current_section=section_index - 1,
        )
        st.session_state[section_key] = section_index - 1
        st.rerun()
    if next_step.button(
        "下一节",
        disabled=section_index >= section_count - 1,
        key=f"teaching_next_{lesson.lesson_id}_{section_index}",
        use_container_width=True,
    ):
        teaching_service.update_position(
            lesson_id=lesson.lesson_id,
            current_section=section_index + 1,
        )
        st.session_state[section_key] = section_index + 1
        st.rerun()

    if section_index == section_count - 1:
        _render_interactive_checks(lesson, teaching_service=teaching_service)
    else:
        st.markdown("**第 3 步 · 互动小测**将在阅读完所有课程章节后开放。")

    with st.container(border=True):
        st.markdown("**完成课程**")
        for question in content.check_questions:
            st.markdown(f"- {question}")
        can_complete = section_index == section_count - 1 and completed_count >= activity_count
        if lesson.progress.completed_at is None:
            if st.button(
                "完成本课程",
                type="primary",
                disabled=not can_complete,
                key="lesson_complete",
            ):
                try:
                    teaching_service.complete_lesson(lesson.lesson_id)
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.rerun()
            else:
                st.caption("阅读完所有章节并完成互动小测后，才能结束本课程。")
        st.caption("掌握检测不是常规教学的必经步骤；课程完成后可以按需进行。")
        if st.button(
            "进入掌握检测（可选）",
            type="primary",
            disabled=lesson.progress.completed_at is None,
            key="lesson_start_check",
        ):
            start_error = start_lesson(
                content.topic,
                st.session_state.get("teaching_goal") or None,
                st.session_state.get("teaching_level") or None,
            )
            if start_error:
                st.error(start_error)
            else:
                st.rerun()


def _render_interactive_checks(
    lesson: TeachingLessonView,
    *,
    teaching_service: TeachingService,
) -> None:
    checks = lesson.lesson.interactive_checks
    if not checks:
        return

    st.markdown('<div class="section-label">第 3 步 · 互动小测</div>', unsafe_allow_html=True)
    latest_attempts: dict[int, TeachingActivityAttemptView] = {}
    for attempt in lesson.progress.attempts:
        latest_attempts.setdefault(attempt.activity_index, attempt)
    for index, check in enumerate(checks, start=1):
        choice_key = f"teaching_check_choice_{lesson.lesson_id}_{index}"
        submitted_key = f"teaching_check_submitted_{lesson.lesson_id}_{index}"
        with st.container(border=True):
            st.markdown(f"**第 {index} 题**")
            choice = st.radio(
                check.prompt,
                options=check.options,
                index=None,
                key=choice_key,
            )
            if st.button("提交答案", key=f"teaching_check_submit_{lesson.lesson_id}_{index}"):
                if choice is None:
                    st.warning("请先选择一个答案。")
                else:
                    request_key = f"teaching_check_request_{lesson.lesson_id}_{index}"
                    request_id = str(st.session_state.setdefault(request_key, str(uuid4())))
                    try:
                        teaching_service.record_activity_attempt(
                            lesson_id=lesson.lesson_id,
                            activity_index=index,
                            selected_answer=choice,
                            request_id=request_id,
                        )
                    except (LookupError, ValueError) as error:
                        st.error(str(error))
                    else:
                        st.session_state[submitted_key] = True
                        st.session_state.pop(request_key, None)
                        st.rerun()

            saved_attempt = latest_attempts.get(index)
            if saved_attempt is not None:
                if saved_attempt.is_correct:
                    st.success("回答正确")
                else:
                    st.error("还需要再想一想")
                st.caption(f"已保存的回答：{saved_attempt.selected_answer}")
                source_names = _source_names(lesson.lesson.sources, check.source_document_ids)
                if source_names:
                    st.caption(f"本题来源：{source_names}")
                st.info(f"正确答案：{check.correct_answer}\n\n解析：{check.explanation}")


def _source_names(sources: Sequence[LessonSource], source_ids: list[str]) -> str:
    """Render selected source filenames without exposing raw document contents."""
    if not source_ids:
        return ""
    names = {source.document_id: source.filename for source in sources}
    return ", ".join(names[source_id] for source_id in source_ids if source_id in names)
