"""Local document-library service for upload, inspection, replacement and deletion."""

import hashlib
import io
import mimetypes
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader, PdfWriter

from ai_growth_companion.application.models import DocumentView
from ai_growth_companion.domain.events import LOCAL_USER_ID
from ai_growth_companion.repositories.database import PROJECT_ROOT
from ai_growth_companion.repositories.document_repository import (
    DocumentRecord,
    SQLiteDocumentRepository,
)

ALLOWED_EXTENSIONS = frozenset({".pdf", ".md", ".markdown", ".txt"})
MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
AUTO_SPLIT_TARGET_BYTES = 19 * 1024 * 1024
DEFAULT_DOCUMENT_STORAGE = PROJECT_ROOT / "data" / "documents"
MIME_TYPES = {
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
}


class DocumentValidationError(ValueError):
    """Raised when an upload does not fit the local-library contract."""


class DocumentLibraryService:
    """Keep SQLite metadata and generated on-disk files in sync."""

    def __init__(
        self,
        repository: SQLiteDocumentRepository,
        *,
        storage_root: Path | None = None,
    ) -> None:
        self.repository = repository
        self.storage_root = (storage_root or DEFAULT_DOCUMENT_STORAGE).resolve()
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def list_documents(self, *, limit: int = 100) -> tuple[DocumentView, ...]:
        return tuple(self._view(record) for record in self.repository.list(limit=limit))

    def upload(self, *, filename: str, content: bytes) -> DocumentView:
        """Upload a file, automatically splitting oversized material into safe chunks.

        The return value remains the first created document for backwards compatibility.
        Call ``upload_documents`` when callers need every generated chunk.
        """
        documents = self.upload_documents(filename=filename, content=content)
        return documents[0]

    def upload_documents(self, *, filename: str, content: bytes) -> tuple[DocumentView, ...]:
        """Upload one file or safely split oversized material into multiple documents."""
        normalized = self._validate_filename(filename)
        if not content:
            raise DocumentValidationError("不能上传空文件")
        if len(content) <= MAX_DOCUMENT_BYTES:
            return (self._upload_single(filename=normalized, content=content),)

        chunks = self._split_oversized_content(filename=normalized, content=content)
        created: list[DocumentView] = []
        try:
            for chunk_name, chunk_content in chunks:
                created.append(self._upload_single(filename=chunk_name, content=chunk_content))
        except Exception:
            for document in created:
                with suppress(LookupError, OSError):
                    self.delete(document.document_id)
            raise
        return tuple(created)

    def _upload_single(self, *, filename: str, content: bytes) -> DocumentView:
        normalized, mime_type = self._validate_upload(filename, content)
        document_id = str(uuid4())
        storage_name = f"{document_id}{Path(normalized).suffix.lower()}"
        self._write_bytes(storage_name, content)
        try:
            record = self.repository.create(
                document_id=document_id,
                filename=normalized,
                storage_name=storage_name,
                mime_type=mime_type,
                size_bytes=len(content),
                sha256=self._digest(content),
                user_id=LOCAL_USER_ID,
            )
        except Exception:
            self._remove_file(storage_name)
            raise
        return self._view(record)

    @classmethod
    def _split_oversized_content(
        cls,
        *,
        filename: str,
        content: bytes,
    ) -> tuple[tuple[str, bytes], ...]:
        extension = Path(filename).suffix.lower()
        if extension == ".pdf":
            return cls._split_pdf(filename=filename, content=content)
        if extension in {".md", ".markdown", ".txt"}:
            return cls._split_text(filename=filename, content=content)
        raise DocumentValidationError("只支持 PDF、Markdown 和 TXT 文件")

    @classmethod
    def _split_pdf(cls, *, filename: str, content: bytes) -> tuple[tuple[str, bytes], ...]:
        try:
            reader = PdfReader(io.BytesIO(content))
            page_count = len(reader.pages)
        except Exception as error:
            raise DocumentValidationError("PDF 无法拆分，请确认文件未损坏") from error
        if page_count == 0:
            raise DocumentValidationError("PDF 没有可拆分的页面")

        target_bytes = cls._split_target_bytes()
        estimated_pages = max(
            1,
            int(page_count * target_bytes / len(content) * 0.9),
        )
        ranges: list[tuple[int, int, bytes]] = []
        for start in range(0, page_count, estimated_pages):
            ranges.extend(
                cls._split_pdf_range(
                    reader=reader,
                    source_name=filename,
                    start=start,
                    end=min(page_count, start + estimated_pages),
                )
            )
        return tuple(
            (
                cls._chunk_filename(
                    filename,
                    part=index,
                    start=start + 1,
                    end=end,
                    unit="pages",
                ),
                chunk,
            )
            for index, (start, end, chunk) in enumerate(ranges, start=1)
        )

    @classmethod
    def _split_pdf_range(
        cls,
        *,
        reader: PdfReader,
        source_name: str,
        start: int,
        end: int,
    ) -> list[tuple[int, int, bytes]]:
        chunk = cls._serialize_pdf_range(reader, source_name=source_name, start=start, end=end)
        if len(chunk) <= cls._split_target_bytes():
            return [(start, end, chunk)]
        if end - start <= 1:
            raise DocumentValidationError(
                "PDF 中存在无法放入 20 MB 限制的单页，请先压缩该 PDF 或拆分页面"
            )
        middle = start + (end - start) // 2
        return cls._split_pdf_range(
            reader=reader,
            source_name=source_name,
            start=start,
            end=middle,
        ) + cls._split_pdf_range(
            reader=reader,
            source_name=source_name,
            start=middle,
            end=end,
        )

    @staticmethod
    def _serialize_pdf_range(
        reader: PdfReader,
        *,
        source_name: str,
        start: int,
        end: int,
    ) -> bytes:
        stream = io.BytesIO()
        writer = PdfWriter()
        for page in reader.pages[start:end]:
            writer.add_page(page)
        writer.add_metadata({"/Title": f"{source_name} pages {start + 1}-{end}"})
        writer.write(stream)
        return stream.getvalue()

    @classmethod
    def _split_text(cls, *, filename: str, content: bytes) -> tuple[tuple[str, bytes], ...]:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise DocumentValidationError(
                "Markdown/TXT 必须使用 UTF-8 编码，无法安全拆分其他编码的文件"
            ) from error
        lines = text.splitlines(keepends=True)
        if not lines:
            raise DocumentValidationError("不能上传空文件")

        target_bytes = cls._split_target_bytes()
        blocks: list[list[str]] = []
        current_block: list[str] = []
        for line in lines:
            current_block.append(line)
            if not line.rstrip("\r\n").strip():
                blocks.append(current_block)
                current_block = []
        if current_block:
            blocks.append(current_block)

        chunks: list[bytes] = []
        current_lines: list[str] = []
        current_bytes = 0
        for block in blocks:
            block_bytes = len("".join(block).encode("utf-8"))
            if block_bytes > target_bytes:
                if current_lines:
                    chunks.append("".join(current_lines).encode("utf-8"))
                    current_lines = []
                    current_bytes = 0
                chunks.extend(cls._split_text_block(block, target_bytes=target_bytes))
                continue
            if current_lines and current_bytes + block_bytes > target_bytes:
                chunks.append("".join(current_lines).encode("utf-8"))
                current_lines = []
                current_bytes = 0
            current_lines.extend(block)
            current_bytes += block_bytes
        if current_lines:
            chunks.append("".join(current_lines).encode("utf-8"))

        suffix = Path(filename).suffix
        return tuple(
            (
                cls._chunk_filename(
                    filename,
                    part=index,
                    start=1,
                    end=1,
                    unit="chunk",
                    suffix=suffix,
                ),
                chunk,
            )
            for index, chunk in enumerate(chunks, start=1)
        )

    @classmethod
    def _split_text_block(cls, lines: list[str], *, target_bytes: int) -> list[bytes]:
        chunks: list[bytes] = []
        current: list[str] = []
        current_bytes = 0
        for line in lines:
            line_bytes = len(line.encode("utf-8"))
            if line_bytes > target_bytes:
                if current:
                    chunks.append("".join(current).encode("utf-8"))
                    current = []
                    current_bytes = 0
                chunks.extend(cls._split_long_text_line(line, target_bytes=target_bytes))
                continue
            if current and current_bytes + line_bytes > target_bytes:
                chunks.append("".join(current).encode("utf-8"))
                current = []
                current_bytes = 0
            current.append(line)
            current_bytes += line_bytes
        if current:
            chunks.append("".join(current).encode("utf-8"))
        return chunks

    @classmethod
    def _split_long_text_line(cls, line: str, *, target_bytes: int) -> list[bytes]:
        chunks: list[bytes] = []
        current: list[str] = []
        current_bytes = 0
        for character in line:
            character_bytes = len(character.encode("utf-8"))
            if current and current_bytes + character_bytes > target_bytes:
                chunks.append("".join(current).encode("utf-8"))
                current = []
                current_bytes = 0
            current.append(character)
            current_bytes += character_bytes
        if current:
            chunks.append("".join(current).encode("utf-8"))
        return chunks

    @staticmethod
    def _split_target_bytes() -> int:
        """Keep generated chunks below the configured upload ceiling."""
        return max(1, min(AUTO_SPLIT_TARGET_BYTES, MAX_DOCUMENT_BYTES))

    @staticmethod
    def _chunk_filename(
        filename: str,
        *,
        part: int,
        start: int,
        end: int,
        unit: str,
        suffix: str | None = None,
    ) -> str:
        extension = suffix or Path(filename).suffix
        stem = Path(filename).stem
        label = f"_part_{part:02d}_{unit}"
        if unit == "pages":
            label += f"_{start:04d}-{end:04d}"
        available = max(1, 255 - len(extension) - len(label))
        return f"{stem[:available]}{label}{extension}"

    def get(self, document_id: str) -> DocumentView:
        return self._view(self.repository.get(document_id))

    def read(self, document_id: str) -> tuple[DocumentView, bytes]:
        record = self.repository.get(document_id)
        path = self._path_for(record.storage_name)
        if not path.is_file():
            raise LookupError("资料文件不存在，可能已被移除")
        return self._view(record), path.read_bytes()

    def rename(self, document_id: str, *, filename: str) -> DocumentView:
        normalized = self._validate_filename(filename)
        current = self.repository.get(document_id)
        current_extension = Path(current.filename).suffix.lower()
        if Path(normalized).suffix.lower() != current_extension:
            raise DocumentValidationError("重命名时不能改变文件类型；请使用替换资料")
        return self._view(self.repository.rename(document_id, filename=normalized))

    def replace(self, document_id: str, *, filename: str, content: bytes) -> DocumentView:
        documents = self.replace_documents(document_id, filename=filename, content=content)
        return documents[0]

    def replace_documents(
        self,
        document_id: str,
        *,
        filename: str,
        content: bytes,
    ) -> tuple[DocumentView, ...]:
        """Replace one entry, splitting oversized replacement material safely."""
        normalized = self._validate_filename(filename)
        if not content:
            raise DocumentValidationError("不能上传空文件")
        if len(content) <= MAX_DOCUMENT_BYTES:
            return (self._replace_single(document_id, filename=normalized, content=content),)

        chunks = self._split_oversized_content(filename=normalized, content=content)
        created: list[DocumentView] = []
        try:
            for chunk_name, chunk_content in chunks[1:]:
                created.append(self._upload_single(filename=chunk_name, content=chunk_content))
            first = self._replace_single(
                document_id,
                filename=chunks[0][0],
                content=chunks[0][1],
            )
        except Exception:
            for document in created:
                with suppress(LookupError, OSError):
                    self.delete(document.document_id)
            raise
        return (first, *created)

    def _replace_single(self, document_id: str, *, filename: str, content: bytes) -> DocumentView:
        normalized, mime_type = self._validate_upload(filename, content)
        current = self.repository.get(document_id)
        storage_name = f"{document_id}-{uuid4()}{Path(normalized).suffix.lower()}"
        self._write_bytes(storage_name, content)
        try:
            record = self.repository.replace(
                document_id,
                filename=normalized,
                storage_name=storage_name,
                mime_type=mime_type,
                size_bytes=len(content),
                sha256=self._digest(content),
            )
        except Exception:
            self._remove_file(storage_name)
            raise
        self._remove_file(current.storage_name)
        return self._view(record)

    def delete(self, document_id: str) -> None:
        record = self.repository.delete(document_id)
        self._remove_file(record.storage_name)

    @staticmethod
    def _validate_filename(filename: str) -> str:
        normalized = filename.strip()
        if not normalized or normalized in {".", ".."}:
            raise DocumentValidationError("文件名不能为空")
        if len(normalized) > 255:
            raise DocumentValidationError("文件名不能超过 255 个字符")
        if "/" in normalized or "\\" in normalized:
            raise DocumentValidationError("文件名不能包含目录路径")
        extension = Path(normalized).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise DocumentValidationError("只支持 PDF、Markdown 和 TXT 文件")
        return normalized

    @classmethod
    def _validate_upload(cls, filename: str, content: bytes) -> tuple[str, str]:
        normalized = cls._validate_filename(filename)
        if not content:
            raise DocumentValidationError("不能上传空文件")
        if len(content) > MAX_DOCUMENT_BYTES:
            raise DocumentValidationError("文件大小不能超过 20 MB")
        extension = Path(normalized).suffix.lower()
        if extension in {".md", ".markdown", ".txt"}:
            try:
                content.decode("utf-8")
            except UnicodeDecodeError as error:
                raise DocumentValidationError(
                    "Markdown/TXT 必须使用 UTF-8 编码，无法安全保存教学资料"
                ) from error
        mime_type = MIME_TYPES.get(
            extension,
            mimetypes.types_map.get(extension, "application/octet-stream"),
        )
        return normalized, mime_type

    def _write_bytes(self, storage_name: str, content: bytes) -> None:
        path = self._path_for(storage_name)
        temporary = path.with_name(f".{path.name}.{uuid4()}.tmp")
        temporary.write_bytes(content)
        temporary.replace(path)

    def _path_for(self, storage_name: str) -> Path:
        path = (self.storage_root / storage_name).resolve()
        if path.parent != self.storage_root or Path(storage_name).name != storage_name:
            raise DocumentValidationError("资料存储路径无效")
        return path

    def _remove_file(self, storage_name: str) -> None:
        path = self._path_for(storage_name)
        with suppress(FileNotFoundError):
            path.unlink()

    @staticmethod
    def _digest(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def _view(record: DocumentRecord) -> DocumentView:
        return DocumentView(
            document_id=record.document_id,
            filename=record.filename,
            extension=Path(record.filename).suffix.lower(),
            mime_type=record.mime_type,
            size_bytes=record.size_bytes,
            sha256=record.sha256,
            status=record.status,
            created_at=_parse_datetime(record.created_at),
            updated_at=_parse_datetime(record.updated_at),
        )


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
