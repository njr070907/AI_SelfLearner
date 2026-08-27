"""Small, local-only text extraction for uploaded teaching materials."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Literal

from pypdf import PdfReader

from ai_growth_companion.application.document_library import DocumentValidationError

MAX_TEACHING_SOURCE_CHARS = 30_000
MAX_SOURCE_UNIT_CHARS = 12_000


@dataclass(frozen=True)
class KnowledgeUnit:
    """One page or text block that can be cited by a generated lesson."""

    page_number: int | None
    text: str
    quality: Literal["clear", "sparse"]


@dataclass(frozen=True)
class ExtractedKnowledge:
    """Text sent to the lesson provider, with page-aware source units."""

    text: str
    page_count: int | None
    truncated: bool
    units: tuple[KnowledgeUnit, ...] = ()
    encoding: str = "utf-8"


def extract_knowledge(filename: str, content: bytes) -> ExtractedKnowledge:
    """Extract readable text without uploading or persisting a second raw copy."""
    extension = Path(filename).suffix.lower()
    units: tuple[KnowledgeUnit, ...]
    if extension in {".md", ".markdown", ".txt"}:
        text, encoding = _decode_text(content)
        page_count = None
        normalized = _normalize(text)
        if not normalized:
            raise DocumentValidationError("资料中没有可提取的文字")
        units = tuple(KnowledgeUnit(None, chunk, "clear") for chunk in _chunk_text(normalized))
    elif extension == ".pdf":
        try:
            reader = PdfReader(BytesIO(content))
            page_texts = []
            units_list: list[KnowledgeUnit] = []
            for page_number, page in enumerate(reader.pages, start=1):
                try:
                    page_text = page.extract_text() or ""
                except Exception:
                    page_text = ""
                normalized_page = _normalize(page_text)
                page_texts.append(normalized_page)
                if normalized_page:
                    units_list.append(
                        KnowledgeUnit(
                            page_number,
                            normalized_page[:MAX_SOURCE_UNIT_CHARS],
                            "clear" if len(normalized_page) >= 80 else "sparse",
                        )
                    )
                else:
                    units_list.append(KnowledgeUnit(page_number, "", "sparse"))
            text = "\n\n".join(page_texts)
            units = tuple(units_list)
            page_count = len(reader.pages)
        except Exception as error:
            raise DocumentValidationError(
                "PDF 无法读取，请确认文件未损坏或改用 Markdown/TXT"
            ) from error
    else:
        raise DocumentValidationError("教学内容只支持 PDF、Markdown 和 TXT")

    normalized = _normalize(text)
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
        units=units,
        encoding=encoding if extension in {".md", ".markdown", ".txt"} else "pdf-text",
    )


def _normalize(text: str) -> str:
    """Keep paragraph boundaries while removing extraction-only trailing noise."""
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def _decode_text(content: bytes) -> tuple[str, str]:
    """Decode common text encodings without silently replacing damaged bytes."""
    candidates: list[str] = []
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        candidates.extend(["utf-16", "utf-16-le", "utf-16-be"])
    elif content.startswith(b"\xef\xbb\xbf"):
        candidates.append("utf-8-sig")
    candidates.extend(["utf-8", "gb18030", "big5", "utf-16-le", "utf-16-be"])

    for encoding in dict.fromkeys(candidates):
        try:
            text = content.decode(encoding)
        except UnicodeDecodeError:
            continue
        if _plausible_text(text):
            return text, encoding

    raise DocumentValidationError(
        "Markdown/TXT 必须使用 UTF-8 或可安全识别的常见编码，无法安全生成教学内容"
    )


def decode_text_content(content: bytes) -> str:
    """Decode a stored Markdown/TXT payload for previews using the same safe rules."""
    text, _encoding = _decode_text(content)
    return text


def _plausible_text(text: str) -> bool:
    """Reject binary-looking decodes so a fallback codec cannot hide corruption."""
    if not text.strip() or "\ufffd" in text:
        return False
    control_count = sum(
        1 for character in text if ord(character) < 32 and character not in {"\n", "\r", "\t"}
    )
    return control_count / max(len(text), 1) <= 0.01


def _chunk_text(text: str) -> tuple[str, ...]:
    """Split long notes on paragraph boundaries so later topics remain searchable."""
    chunks: list[str] = []
    current = ""
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) > MAX_SOURCE_UNIT_CHARS:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(
                paragraph[index : index + MAX_SOURCE_UNIT_CHARS]
                for index in range(0, len(paragraph), MAX_SOURCE_UNIT_CHARS)
            )
            continue
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > MAX_SOURCE_UNIT_CHARS:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return tuple(chunks)
