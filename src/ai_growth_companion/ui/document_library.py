"""Streamlit page for the local document-library CRUD flow."""

from html import escape

import streamlit as st

from ai_growth_companion.application.document_library import (
    DocumentLibraryService,
    DocumentValidationError,
)
from ai_growth_companion.application.knowledge_extraction import decode_text_content
from ai_growth_companion.application.models import DocumentView


def render_document_library(service: DocumentLibraryService) -> None:
    """Render upload, list, download, rename, replacement and deletion controls."""
    st.markdown('<div class="eyebrow">资料库 · 你的学习材料</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">资料库</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-copy">把正在学习的讲义和笔记放在一起。当前版本支持 PDF、Markdown 和 TXT；'
        "文件保存在本地，不会自动上传到外部模型。</p>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown('<div class="section-label">新增资料</div>', unsafe_allow_html=True)
        uploads = st.file_uploader(
            "选择要上传的资料",
            type=["pdf", "md", "markdown", "txt"],
            accept_multiple_files=True,
            key="document_upload",
            help="超过 20 MB 的 PDF、Markdown 和 TXT 会自动按安全边界拆分后保存；原文内容不改写。",
        )
        if st.button(
            "上传资料",
            type="primary",
            key="document_upload_button",
            disabled=not uploads,
        ):
            uploaded = 0
            split_count = 0
            for item in uploads:
                try:
                    documents = service.upload_documents(
                        filename=item.name,
                        content=item.getvalue(),
                    )
                except DocumentValidationError as error:
                    st.error(f"{item.name}：{error}")
                else:
                    uploaded += 1
                    if len(documents) > 1:
                        split_count += len(documents)
                        st.info(f"{item.name} 超过 20 MB，已自动拆分为 {len(documents)} 个分卷。")
            if uploaded:
                suffix = f"，其中自动拆分生成 {split_count} 个分卷" if split_count else ""
                st.success(f"已上传 {uploaded} 个文件{suffix}。")

    documents = service.list_documents()
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-label">全部资料 · {len(documents)} 个文件</div>',
        unsafe_allow_html=True,
    )
    if not documents:
        st.info("资料库还是空的。上传第一份讲义或笔记后，它会出现在这里。")
        return

    for document in documents:
        _render_document(service, document)


def _render_document(service: DocumentLibraryService, document: DocumentView) -> None:
    with st.container(border=True):
        left, middle, right = st.columns([2.8, 1.5, 1.2], vertical_alignment="center")
        left.markdown(
            f'<div class="row-title">{escape(document.filename)}</div>'
            f'<div class="row-meta">{_format_size(document.size_bytes)} · '
            f"{escape(document.mime_type)} · {escape(document.status)}</div>",
            unsafe_allow_html=True,
        )
        middle.caption(f"更新于 {document.updated_at.astimezone().strftime('%Y-%m-%d %H:%M')}")
        try:
            _, content = service.read(document.document_id)
        except LookupError as error:
            right.error(str(error))
        else:
            right.download_button(
                "下载",
                data=content,
                file_name=document.filename,
                mime=document.mime_type,
                key=f"document_download_{document.document_id}",
                use_container_width=True,
            )

        if document.extension in {".md", ".markdown", ".txt"}:
            try:
                _, content = service.read(document.document_id)
            except LookupError:
                pass
            else:
                with st.expander("查看文本预览"):
                    try:
                        preview = decode_text_content(content)[:20_000]
                    except DocumentValidationError as error:
                        st.error(f"该文本资料无法安全预览：{error}")
                    else:
                        st.code(
                            preview,
                            language="markdown" if document.extension != ".txt" else None,
                        )
                        if len(preview) >= 20_000:
                            st.caption("预览已截取前 20,000 个字符，下载文件可查看完整内容。")

        edit, replace, remove = st.columns(3)
        with edit.form(key=f"document_rename_form_{document.document_id}"):
            new_name = st.text_input("修改文件名", value=document.filename)
            if st.form_submit_button("保存名称"):
                try:
                    service.rename(document.document_id, filename=new_name)
                except (DocumentValidationError, LookupError) as error:
                    st.error(str(error))
                else:
                    st.success("文件名已更新。")
                    st.rerun()

        with replace.form(key=f"document_replace_form_{document.document_id}"):
            replacement = st.file_uploader(
                "替换文件",
                type=["pdf", "md", "markdown", "txt"],
                key=f"document_replace_{document.document_id}",
            )
            if st.form_submit_button("替换资料") and replacement is not None:
                try:
                    documents = service.replace_documents(
                        document.document_id,
                        filename=replacement.name,
                        content=replacement.getvalue(),
                    )
                except (DocumentValidationError, LookupError) as error:
                    st.error(str(error))
                else:
                    if len(documents) > 1:
                        st.info(f"替换内容超过 20 MB，已自动拆分为 {len(documents)} 个分卷。")
                    st.success("资料内容已替换。")
                    st.rerun()

        with remove:
            confirmed = st.checkbox(
                "确认删除",
                key=f"document_delete_confirm_{document.document_id}",
            )
            if st.button(
                "删除",
                key=f"document_delete_{document.document_id}",
                type="secondary",
                disabled=not confirmed,
                use_container_width=True,
            ):
                try:
                    service.delete(document.document_id)
                except LookupError as error:
                    st.error(str(error))
                else:
                    st.success("资料已删除。")
                    st.rerun()


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"
