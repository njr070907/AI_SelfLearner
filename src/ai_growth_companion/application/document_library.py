"""Local document-library service for upload, inspection, replacement and deletion."""

import hashlib
import mimetypes
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from ai_growth_companion.application.models import DocumentView
from ai_growth_companion.domain.events import LOCAL_USER_ID
from ai_growth_companion.repositories.database import PROJECT_ROOT
from ai_growth_companion.repositories.document_repository import (
    DocumentRecord,
    SQLiteDocumentRepository,
)

ALLOWED_EXTENSIONS = frozenset({".pdf", ".md", ".markdown", ".txt"})
MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
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
