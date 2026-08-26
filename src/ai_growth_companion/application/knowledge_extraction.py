"""Small, local-only text extraction for uploaded teaching materials."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from ai_growth_companion.application.document_library import DocumentValidationError

MAX_TEACHING_SOURCE_CHARS = 30_000


@dataclass(frozen=True)
class ExtractedKnowledge:
    """Text sent to the lesson provider, with a transparent truncation marker."""

    text: str
    page_count: int | None
    truncated: bool


def extract_knowledge(filename: str, content: bytes) -> ExtractedKnowledge:
    """Extract readable text without uploading or persisting a second raw copy."""
    extension = Path(filename).suffix.lower()
    if extension in {".md", ".markdown", ".txt"}:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise DocumentValidationError(
                "Markdown/TXT 必须使用 UTF-8 编码，无法安全生成教学内容"
            ) from error
        page_count = None
    elif extension == ".pdf":
        try:
            reader = PdfReader(BytesIO(content))
            text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
            page_count = len(reader.pages)
        except Exception as error:
            raise DocumentValidationError(
                "PDF 无法读取，请确认文件未损坏或改用 Markdown/TXT"
            ) from error
    else:
        raise DocumentValidationError("教学内容只支持 PDF、Markdown 和 TXT")

    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not normalized:
        raise DocumentValidationError("资料中没有可提取的文字；扫描版 PDF 需要先 OCR")
    if "\ufffd" in normalized:
        raise DocumentValidationError(
            "PDF 文字层包含乱码，无法安全生成教学内容；请改用视觉读取或先 OCR"
        )
    truncated = len(normalized) > MAX_TEACHING_SOURCE_CHARS
    return ExtractedKnowledge(
        text=normalized[:MAX_TEACHING_SOURCE_CHARS],
        page_count=page_count,
        truncated=truncated,
    )
