"""Teaching workspace: upload knowledge, generate a lesson, then study it."""

from collections.abc import Callable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from hashlib import sha256
from html import escape
from time import monotonic, sleep
from uuid import uuid4

import streamlit as st

from ai_growth_companion.application.document_library import DocumentLibraryService
from ai_growth_companion.application.teaching_service import (
    TeachingActivityAttemptView,
    TeachingInputError,
    TeachingLessonView,
    TeachingReportView,
    TeachingService,
)
from ai_growth_companion.application.topic_suggestions import TopicSuggestion
from ai_growth_companion.providers.base import ProviderError
from ai_growth_companion.schemas.teaching import LessonEvidence, LessonSource

StartLesson = Callable[[str, str | None, str | None], str | None]

LEARNING_GOAL_CHOICES: tuple[tuple[str, str | None], ...] = (
    ("不指定（由 AI 自动安排）", None),
    ("理解核心概念", "能用自己的话解释核心概念、定义和关键术语"),
    ("理解机制与步骤", "能说明知识的运作机制、推导步骤和因果关系"),
    ("掌握适用条件与边界", "能判断适用条件、限制和常见误区"),
    ("能够通过例子应用", "能把知识应用到一个新例子或实际问题"),
    ("综合掌握并迁移", "能综合解释概念、机制、边界，并迁移到新情境"),
)
_GENERATION_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="ai-selflearner-teaching",
)


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
    if teaching_service.provider.provider_name == "fake":
        st.warning(
            "当前是 Fake Provider 流程演示：它只验证资料→课程→进度管道，"
            "不会判断真实教材语义。要验收真实内容，请切换到 Ollama 本地文本模式或"
            "已授权的 DeepSeek 视觉模式。"
        )
    elif teaching_service.provider.provider_name == "ollama":
        st.info(
            "当前使用 Ollama 本地文本模型生成常规教学内容；扫描版或乱码 PDF 只有在"
            "显式配置 DeepSeek 视觉 Provider 后才能使用视觉读取。英文资料会先尝试用"
            "本地 Qwen 0.8B 翻译成中文，翻译失败时自动保留英文原文继续生成。"
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
                "分析哪些资料（默认全部）",
                options=tuple(document_labels),
                format_func=document_labels.__getitem__,
                default=tuple(document_labels),
                key="teaching_selected_documents",
                help="系统会先从这些资料总结学习主题；你不需要自己填写主题。",
            )
        )
        topic_result = teaching_service.get_topic_suggestions(
            selected_ids,
            request_id="ui-topic-analysis",
        )
        if topic_result.status == "pending":
            st.info(
                "AI 正在阅读资料并整理学习主题。主题生成在后台进行，不会阻塞资料上传；"
                "当前先显示临时主题，不会阻塞课程生成；完成后点击下方按钮刷新为 AI 候选。"
            )
            if st.button("刷新 AI 主题候选", key="teaching_refresh_topics"):
                st.rerun()
        elif topic_result.status == "fallback":
            st.warning("AI 主题分析暂时不可用，当前显示的是根据资料标题生成的临时选项。")
        elif topic_result.status == "unavailable":
            st.warning("当前资料暂时无法提取文字，无法自动总结主题。")

        suggestions = topic_result.suggestions
        suggestion_by_id = {item.suggestion_id: item for item in suggestions}
        vision_available = teaching_service.provider.supports_vision
        with st.form("teaching_generate_form", clear_on_submit=False):
            if suggestions:
                topic_selection_key = (
                    "teaching_topic_suggestion_"
                    + sha256("|".join(selected_ids).encode()).hexdigest()[:12]
                )
                suggestion_id = st.selectbox(
                    (
                        "选择 AI 总结的学习主题"
                        if topic_result.status != "pending"
                        else "选择学习主题（AI 分析完成后可刷新替换）"
                    ),
                    options=tuple(suggestion_by_id),
                    format_func=lambda value: suggestion_by_id[value].title,
                    key=topic_selection_key,
                )
                selected_suggestion: TopicSuggestion = suggestion_by_id[suggestion_id]
                topic = selected_suggestion.title
                st.caption(selected_suggestion.summary)
                if selected_suggestion.key_concepts:
                    st.caption("关键概念：" + "、".join(selected_suggestion.key_concepts))
            else:
                topic = ""

            source_selection = None
            if topic and selected_ids:
                source_selection = teaching_service.recommend_sources(
                    topic=topic,
                    document_ids=selected_ids,
                    limit=8,
                )
                recommended_ids = source_selection.selected_document_ids or selected_ids
                final_document_ids = tuple(
                    st.multiselect(
                        "本次使用的资料分卷（AI 已推荐，可调整）",
                        options=selected_ids,
                        default=recommended_ids,
                        format_func=document_labels.__getitem__,
                        key=("teaching_final_documents_" + sha256(topic.encode()).hexdigest()[:12]),
                        help="默认使用与主题最相关的分卷；你可以增删，但不需要手动寻找分卷。",
                    )
                )
                if source_selection.confidence == "low":
                    st.caption("暂未找到高置信度匹配，已暂用你选定的资料范围。")
                elif source_selection.requires_confirmation:
                    st.caption("AI 已按主题推荐资料范围，请在生成前确认是否需要调整。")
            else:
                final_document_ids = selected_ids

            has_selected_pdf = any(
                document.document_id in final_document_ids and document.extension == ".pdf"
                for document in documents
            )
            goal_choice = st.selectbox(
                "学习目标",
                options=tuple(label for label, _ in LEARNING_GOAL_CHOICES),
                key="teaching_goal_choice",
                help="选择希望课程重点照顾的方向；不指定时由 AI 按资料自动安排。",
            )
            goal = dict(LEARNING_GOAL_CHOICES)[goal_choice]
            st.session_state["teaching_goal_value"] = goal
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
            use_vision = st.checkbox(
                "使用视觉读取 PDF 页面",
                value=False,
                disabled=not has_selected_pdf or not vision_available,
                key="teaching_use_vision",
                help=(
                    "仅对本次选中的 PDF 页面发送图片；适合扫描版、乱码或公式较多的资料。"
                    "当前模型端点必须支持图片输入；Fake Provider 不会伪装成视觉模式。"
                ),
            )
            submitted = st.form_submit_button(
                "生成我的教学内容",
                type="primary",
                disabled=not topic or not final_document_ids,
            )
        if submitted:
            try:
                lesson = _generate_lesson_with_countdown(
                    teaching_service,
                    topic=topic,
                    document_ids=final_document_ids,
                    learning_goal=goal,
                    learner_level=level or None,
                    request_id=str(uuid4()),
                    use_vision=use_vision,
                )
            except ProviderError as error:
                st.error(str(error))
                st.caption(f"错误代码：{error.code}")
            except (TeachingInputError, LookupError) as error:
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

    _render_learning_report(teaching_service.get_learning_report(limit=len(lessons)))
    st.markdown('<div class="section-label">我的课程</div>', unsafe_allow_html=True)
    for lesson in lessons:
        activity_count = len(lesson.lesson.interactive_checks)
        completed_count = lesson.progress.completed_activity_count
        status = "已完成" if lesson.progress.completed_at is not None else "学习中"
        latest_attempts = _latest_attempts(lesson)
        answered_count = len(latest_attempts)
        correct_count = sum(1 for attempt in latest_attempts.values() if attempt.is_correct)
        result = f" · 小测 {correct_count}/{answered_count}" if answered_count else ""
        with st.container(border=True):
            st.markdown(f"**{escape(lesson.lesson.title)}**")
            st.caption(
                f"主题：{escape(lesson.lesson.topic)} · {status} · "
                f"互动进度 {completed_count}/{activity_count}{result}"
            )
            if st.button(
                "打开课程" if lesson.progress.completed_at is not None else "继续课程",
                key=f"teaching_resume_{lesson.lesson_id}",
                type="primary" if lesson.progress.completed_at is None else "secondary",
            ):
                st.session_state.teaching_lesson_id = lesson.lesson_id
                st.rerun()


def _render_learning_report(report: TeachingReportView) -> None:
    """Summarize course activity without presenting it as a mastery decision."""
    with st.container(border=True):
        st.markdown('<div class="section-label">学习报告</div>', unsafe_allow_html=True)
        st.markdown(
            f"已生成课程 **{report.lesson_count}** 门 · "
            f"已完成 **{report.completed_lesson_count}** 门 · "
            f"互动题完成率 **{report.completion_rate}%** · "
            f"已答题正确率 **{report.accuracy}%** · "
            f"来源资料 **{report.source_document_count}** 份"
        )
        if report.partial_lesson_count or report.draft_lesson_count:
            st.caption(
                f"来源状态：已核验 {report.verified_lesson_count} 门 · "
                f"部分核验 {report.partial_lesson_count} 门 · "
                f"导读草稿 {report.draft_lesson_count} 门。"
            )
        st.caption(
            "这里统计的是常规课程的阅读/互动记录，不直接代表长期掌握度；掌握结论请看掌握检测和复习记录。"
        )


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
    _render_grounding_status(content)
    _render_translation_status(content)
    activity_count = len(content.interactive_checks)
    completed_count = lesson.progress.completed_activity_count
    st.progress(
        completed_count / activity_count if activity_count else 1.0,
        text=f"课程互动进度：{completed_count}/{activity_count}",
    )
    if lesson.progress.completed_at is not None:
        st.success("这门课程已经完成，可以继续复习或进行可选掌握检测。")
        _render_completion_report(lesson)
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
            _render_source_excerpts(content.sources, section.source_document_ids)
        _render_evidence(section.evidence)

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
                st.session_state.get("teaching_goal_value") or None,
                st.session_state.get("teaching_level") or None,
            )
            if start_error:
                st.error(start_error)
            else:
                st.rerun()


def _generate_lesson_with_countdown(
    teaching_service: TeachingService,
    *,
    topic: str,
    document_ids: tuple[str, ...],
    learning_goal: str | None,
    learner_level: str | None,
    request_id: str,
    use_vision: bool,
) -> TeachingLessonView:
    """Run generation off the UI thread while keeping a live, honest time estimate."""
    estimate_seconds = _generation_estimate_seconds(teaching_service)
    started = monotonic()
    job: Future[TeachingLessonView] = _GENERATION_EXECUTOR.submit(
        teaching_service.generate_lesson,
        topic=topic,
        document_ids=document_ids,
        learning_goal=learning_goal,
        learner_level=learner_level,
        request_id=request_id,
        use_vision=use_vision,
    )
    progress = st.progress(0.0, text="正在启动教学内容生成……")
    status = st.empty()
    while not job.done():
        elapsed = monotonic() - started
        remaining = max(0.0, estimate_seconds - elapsed)
        if remaining > 0:
            status.info(
                f"正在阅读资料并生成教学内容 · 已用 {_format_duration(elapsed)} · "
                f"预计剩余约 {_format_duration(remaining)}"
            )
        else:
            status.warning(
                f"已超过预计 {_format_duration(estimate_seconds)}，模型仍在返回；"
                f"已等待 {_format_duration(elapsed)}，请不要重复提交。"
            )
        progress.progress(
            min(0.99, elapsed / estimate_seconds),
            text=f"生成中 · 预计剩余约 {_format_duration(remaining)}",
        )
        sleep(0.5)

    lesson = job.result()
    elapsed = monotonic() - started
    progress.progress(1.0, text="教学内容生成完成")
    status.success(f"教学内容已生成，用时 {_format_duration(elapsed)}")
    return lesson


def _generation_estimate_seconds(teaching_service: TeachingService) -> int:
    """Return a conservative UI estimate, not a promise about model latency."""
    provider_name = str(getattr(teaching_service.provider, "provider_name", "")).casefold()
    if provider_name == "fake":
        return 5
    if provider_name == "ollama":
        return 300
    return 120


def _format_duration(seconds: float) -> str:
    """Format a countdown so users can scan it without doing mental arithmetic."""
    total_seconds = max(0, int(seconds + 0.999))
    minutes, remainder = divmod(total_seconds, 60)
    if minutes:
        return f"{minutes} 分 {remainder:02d} 秒"
    return f"{remainder} 秒"


def _render_interactive_checks(
    lesson: TeachingLessonView,
    *,
    teaching_service: TeachingService,
) -> None:
    checks = lesson.lesson.interactive_checks
    if not checks:
        return

    st.markdown('<div class="section-label">第 3 步 · 互动小测</div>', unsafe_allow_html=True)
    latest_attempts = _latest_attempts(lesson)
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
                _render_evidence(check.evidence)
                st.info(f"正确答案：{check.correct_answer}\n\n解析：{check.explanation}")


def _render_completion_report(lesson: TeachingLessonView) -> None:
    """Show a transparent course report without turning quiz results into mastery."""
    latest_attempts = _latest_attempts(lesson)
    checks = lesson.lesson.interactive_checks
    correct_count = sum(
        1
        for index in range(1, len(checks) + 1)
        if (attempt := latest_attempts.get(index)) is not None and attempt.is_correct
    )
    incorrect_checks = [
        (index, checks[index - 1], latest_attempts[index])
        for index in range(1, len(checks) + 1)
        if index in latest_attempts and not latest_attempts[index].is_correct
    ]
    score = round(correct_count / len(checks) * 100) if checks else 100
    with st.container(border=True):
        st.markdown('<div class="section-label">学习小结</div>', unsafe_allow_html=True)
        st.markdown(
            f"已完成 {len(lesson.lesson.sections)} 个课程章节和 {len(checks)} 道互动题。"
            f"本次互动得分：**{correct_count}/{len(checks)}（{score}%）**。"
        )
        if not incorrect_checks:
            st.success("本次互动题全部答对，可以进入可选掌握检测或安排后续复习。")
            return
        st.warning("有些互动题还需要再巩固。下面保留错题和解析，建议先复习后再进行掌握检测。")
        for index, check, attempt in incorrect_checks:
            st.markdown(f"**第 {index} 题** · 你的回答：{attempt.selected_answer}")
            st.caption(f"正确答案：{check.correct_answer} · 解析：{check.explanation}")


def _latest_attempts(lesson: TeachingLessonView) -> dict[int, TeachingActivityAttemptView]:
    """Return one newest persisted attempt per activity."""
    latest_attempts: dict[int, TeachingActivityAttemptView] = {}
    for attempt in lesson.progress.attempts:
        latest_attempts.setdefault(attempt.activity_index, attempt)
    return latest_attempts


def _source_names(sources: Sequence[LessonSource], source_ids: list[str]) -> str:
    """Render selected source filenames without exposing raw document contents."""
    if not source_ids:
        return ""
    names = {source.document_id: source.filename for source in sources}
    return ", ".join(names[source_id] for source_id in source_ids if source_id in names)


def _render_source_excerpts(sources: Sequence[LessonSource], source_ids: list[str]) -> None:
    """Let learners verify the source text used for the visible lesson section."""
    selected = [source for source in sources if source.document_id in source_ids]
    if not selected:
        return
    with st.expander("查看本节参考原文"):
        for source in selected:
            st.markdown(f"**{escape(source.filename)}**")
            st.caption(source.excerpt)


def _render_evidence(evidence: Sequence[LessonEvidence]) -> None:
    """Show the exact source snippets that the generated unit claims to use."""
    if not evidence:
        return
    with st.expander("查看生成依据"):
        for item in evidence:
            location = f" · 第 {item.page_number} 页" if item.page_number else ""
            st.caption(f"原文依据{location}：{item.quote}")


def _render_grounding_status(content: object) -> None:
    """Explain degraded source verification without hiding a usable saved lesson."""
    status = getattr(content, "grounding_status", "verified")
    issues = getattr(content, "grounding_issues", [])
    if status == "verified":
        return
    labels = {
        "repaired": "来源证据已自动修复",
        "partial": "课程已保存，但部分来源证据待核验",
        "draft": "课程已保存为资料导读草稿，部分内容待完善",
    }
    message = labels.get(str(status), "课程已保存，来源证据待核验")
    if status == "repaired":
        st.info(message)
    elif status == "draft":
        st.warning(message)
    else:
        st.warning(message)
    if isinstance(issues, list) and issues:
        with st.expander("查看生成提示"):
            for issue in issues:
                st.caption(f"• {issue}")


def _render_translation_status(content: object) -> None:
    """Explain whether an English source was translated without blocking the lesson."""
    status = getattr(content, "translation_status", "not_needed")
    if status == "not_needed":
        return
    model = getattr(content, "translation_model", None)
    translated_count = getattr(content, "translated_unit_count", 0)
    failed_count = getattr(content, "translation_failed_unit_count", 0)
    if status == "pending":
        model_label = f"（{escape(str(model))}）" if model else ""
        st.info(
            f"英文资料正在后台翻译{model_label}；本次课程先使用原文生成，"
            "下次生成课程时会优先使用已完成的中文译文。"
        )
        return
    if status == "translated":
        model_label = f"（{escape(str(model))}）" if model else ""
        st.info(f"英文资料已先翻译成中文再生成课程{model_label}，原文证据仍已保留。")
        if failed_count:
            st.caption(
                f"其中 {failed_count} 个片段翻译失败，已自动保留原文；"
                f"成功翻译 {translated_count} 个片段。"
            )
        return
    st.warning("英文资料翻译暂不可用，课程已使用原文继续生成；不会影响课程保存。")
