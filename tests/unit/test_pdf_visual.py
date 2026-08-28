"""Offline tests for bounded PDF page rendering used by vision teaching."""

from io import BytesIO

from pypdf import PdfWriter

from ai_growth_companion.application.pdf_visual import (
    MAX_VISION_PAGES,
    render_pdf_pages,
    select_pdf_pages,
)


def blank_pdf(page_count: int = 2) -> bytes:
    stream = BytesIO()
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=320, height=240)
    writer.write(stream)
    return stream.getvalue()


def test_page_selection_falls_back_to_first_pages_for_image_only_pdf() -> None:
    selected = select_pdf_pages(blank_pdf(4), topic="函数极限", max_pages=3)

    assert selected == (1, 2, 3)


def test_pdf_pages_render_to_bounded_jpeg_images() -> None:
    pages = render_pdf_pages(
        blank_pdf(),
        document_id="doc-1",
        filename="教材.pdf",
        page_numbers=(1, 2),
    )

    assert len(pages) == 2
    assert all(page.media_type == "image/jpeg" for page in pages)
    assert all(page.content.startswith(b"\xff\xd8") for page in pages)
    assert all(page.page_number <= MAX_VISION_PAGES for page in pages)
