"""Tests for local teaching-material extraction."""

import pytest

from ai_growth_companion.application.document_library import DocumentValidationError
from ai_growth_companion.application.knowledge_extraction import extract_knowledge


def _minimal_text_pdf(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 20 100 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n").encode(
            "ascii"
        )
    )
    return bytes(pdf)


def test_markdown_is_normalized_and_bounded() -> None:
    result = extract_knowledge("notes.md", b"  # Topic  \n\nfirst line  \n")

    assert result.text == "# Topic\n\nfirst line"
    assert result.page_count is None
    assert result.truncated is False


def test_pdf_text_is_extracted_locally() -> None:
    result = extract_knowledge("lesson.pdf", _minimal_text_pdf("limit definition"))

    assert "limit definition" in result.text
    assert result.page_count == 1


@pytest.mark.parametrize(
    ("filename", "content", "message"),
    [
        ("scan.pdf", b"not a pdf", "PDF 无法读取"),
        ("scan.pdf", _minimal_text_pdf(""), "没有可提取"),
        ("lesson.docx", b"unsupported", "只支持"),
        ("legacy.txt", b"\x80\x81not utf-8", "必须使用 UTF-8"),
    ],
)
def test_unreadable_or_unsupported_material_is_rejected(
    filename: str,
    content: bytes,
    message: str,
) -> None:
    with pytest.raises(DocumentValidationError, match=message):
        extract_knowledge(filename, content)


def test_long_material_is_truncated_with_a_flag() -> None:
    result = extract_knowledge("long.txt", ("x" * 30_100).encode())

    assert len(result.text) == 30_000
    assert result.truncated is True
