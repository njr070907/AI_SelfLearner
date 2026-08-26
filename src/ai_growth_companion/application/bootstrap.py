"""Application composition with an explicit real-Provider safety gate."""

from pathlib import Path

from ai_growth_companion.application.document_library import DocumentLibraryService
from ai_growth_companion.application.learning_service import LearningService
from ai_growth_companion.application.provider_factory import build_provider_factory
from ai_growth_companion.config import Settings
from ai_growth_companion.repositories.database import Database
from ai_growth_companion.repositories.document_repository import SQLiteDocumentRepository
from ai_growth_companion.repositories.session_repository import SQLiteSessionRepository


def build_learning_service(database: Database, settings: Settings) -> LearningService:
    """Build the interactive service without silently enabling paid network calls."""
    provider_factory = build_provider_factory(
        settings,
        paid_calls_allowed=settings.llm_paid_calls_allowed,
    )
    return LearningService(
        SQLiteSessionRepository(database),
        provider_factory=provider_factory,
    )


def build_document_library(database: Database) -> DocumentLibraryService:
    """Build the local metadata-and-files service without external dependencies."""
    storage_root = database.path.parent / "documents" if isinstance(database.path, Path) else None
    return DocumentLibraryService(
        SQLiteDocumentRepository(database),
        storage_root=storage_root,
    )
