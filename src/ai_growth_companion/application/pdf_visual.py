"""Render selected PDF pages for an explicitly requested vision teaching call."""

from __future__ import annotations

import re
from collections.abc import Iterable
from io import BytesIO
from typing import Any, cast

from pypdf import PdfReader

from ai_growth_companion.application.document_library import DocumentValidationError
from ai_growth_companion.providers.base import TeachingPageImage

MAX_VISION_PAGES = 6
MAX_PAGE_IMAGE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_IMAGE_BYTES = 16 * 1024 * 1024
DEFAULT_RENDER_DPI = 144


def select_pdf_pages(
    content: bytes,
    *,
    topic: str,
    max_pages: int = MAX_VISION_PAGES,
) -> tuple[int, ...]:
    """Select topic-relevant 1-based pages, with a safe first-pages fallback."""
    if max_pages < 1:
        raise ValueError("max_pages must be positive")
    try:
        reader = PdfReader(BytesIO(content))
        page_count = len(reader.pages)
    except Exception as error:
        raise DocumentValidationError("PDF 无法读取，无法准备视觉页面") from error
    if page_count == 0:
        raise DocumentValidationError("PDF 没有可读取的页面")

    terms = _topic_terms(topic)
    scored: list[tuple[int, int]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        compact = _compact(text)
        score = sum(min(compact.count(_compact(term)), 12) for term in terms)
        scored.append((score, page_number))

    ranked = sorted(scored, key=lambda item: (-item[0], item[1]))
    selected = [page_number for score, page_number in ranked if score > 0][:max_pages]
    if not selected:
        selected = list(range(1, min(page_count, max_pages) + 1))
    return tuple(sorted(selected))


def render_pdf_pages(
    content: bytes,
    *,
    document_id: str,
    filename: str,
    page_numbers: Iterable[int],
    dpi: int = DEFAULT_RENDER_DPI,
) -> tuple[TeachingPageImage, ...]:
    """Render local PDF pages into bounded JPEG images for multimodal input."""
    if dpi < 72 or dpi > 220:
        raise ValueError("dpi must be between 72 and 220")
    selected = tuple(dict.fromkeys(page_numbers))
    if not selected:
        raise DocumentValidationError("没有选择需要视觉读取的 PDF 页面")
    if len(selected) > MAX_VISION_PAGES:
        raise DocumentValidationError(f"一次最多视觉读取 {MAX_VISION_PAGES} 页")

    try:
        import pymupdf as fitz

        pdf: Any = fitz.open(  # type: ignore[no-untyped-call]
            stream=content,
            filetype="pdf",
        )
    except Exception as error:
        raise DocumentValidationError("PDF 无法渲染为图片，请确认文件未损坏") from error

    try:
        page_count = pdf.page_count
        if any(page_number < 1 or page_number > page_count for page_number in selected):
            raise DocumentValidationError("视觉页面范围超出 PDF 页数")

        rendered: list[TeachingPageImage] = []
        total_bytes = 0
        for page_number in selected:
            page = pdf.load_page(page_number - 1)
            image = _render_page(page, fitz=fitz, dpi=dpi)
            total_bytes += len(image)
            if total_bytes > MAX_TOTAL_IMAGE_BYTES:
                raise DocumentValidationError(
                    f"视觉页面总大小不能超过 {MAX_TOTAL_IMAGE_BYTES // (1024 * 1024)} MB"
                )
            rendered.append(
                TeachingPageImage(
                    document_id=document_id,
                    filename=filename,
                    page_number=page_number,
                    media_type="image/jpeg",
                    content=image,
                )
            )
        return tuple(rendered)
    finally:
        pdf.close()


def _render_page(page: Any, *, fitz: Any, dpi: int) -> bytes:
    """Render one page and reduce quality before rejecting an oversized image."""
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    for quality in (82, 72, 62):
        image = cast(bytes, pixmap.tobytes("jpeg", jpg_quality=quality))
        if len(image) <= MAX_PAGE_IMAGE_BYTES:
            return image
    raise DocumentValidationError(
        f"PDF 页面渲染后仍超过 {MAX_PAGE_IMAGE_BYTES // (1024 * 1024)} MB"
    )


def _topic_terms(topic: str) -> tuple[str, ...]:
    normalized = topic.casefold().strip()
    tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", normalized)
    return tuple(dict.fromkeys((normalized, *tokens)))


def _compact(text: str) -> str:
    return "".join(text.casefold().split())
