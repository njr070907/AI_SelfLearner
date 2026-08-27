"""Application composition with an explicit real-Provider safety gate."""

from pathlib import Path

from ai_growth_companion.application.document_library import DocumentLibraryService
from ai_growth_companion.application.learning_service import LearningService
from ai_growth_companion.application.provider_factory import build_provider_factory
from ai_growth_companion.application.teaching_service import TeachingService
from ai_growth_companion.config import Settings
from ai_growth_companion.providers.base import TeachingProvider
from ai_growth_companion.providers.deepseek_evaluation import DEEPSEEK_MODEL
from ai_growth_companion.providers.deepseek_teaching import DeepSeekTeachingProvider
from ai_growth_companion.providers.fake import FakeLLMProvider
from ai_growth_companion.providers.ollama import (
    OLLAMA_FAST_MODEL,
    OLLAMA_QUALITY_MODEL,
    OllamaTeachingProvider,
    OllamaTopicSuggestionProvider,
    OllamaTranslationProvider,
    RoutedTeachingProvider,
)
from ai_growth_companion.repositories.database import Database
from ai_growth_companion.repositories.document_repository import SQLiteDocumentRepository
from ai_growth_companion.repositories.lesson_progress_repository import (
    SQLiteLessonProgressRepository,
)
from ai_growth_companion.repositories.lesson_repository import SQLiteLessonRepository
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


def build_teaching_service(database: Database, settings: Settings) -> TeachingService:
    """Build source-grounded teaching with explicit local/remote model routing."""
    document_library = build_document_library(database)
    provider: TeachingProvider
    translation_provider: OllamaTranslationProvider | None = None
    topic_provider: OllamaTopicSuggestionProvider | None = None
    if settings.is_fake_mode:
        provider = FakeLLMProvider()
    elif settings.llm_provider.casefold() == "ollama":
        quality_model = (
            settings.ollama_quality_model
            if settings.llm_model.casefold().startswith("fake")
            else settings.llm_model
        )
        text_provider = OllamaTeachingProvider(
            model=quality_model or OLLAMA_QUALITY_MODEL,
            base_url=settings.ollama_base_url,
            timeout_seconds=settings.ollama_timeout_seconds,
            max_output_tokens=4_000,
        )
        translation_provider = OllamaTranslationProvider(
            model=settings.ollama_fast_model or OLLAMA_FAST_MODEL,
            base_url=settings.ollama_base_url,
            timeout_seconds=settings.ollama_translation_timeout_seconds,
            max_output_tokens=2_000,
        )
        topic_provider = OllamaTopicSuggestionProvider(
            model=settings.ollama_balanced_model,
            base_url=settings.ollama_base_url,
            timeout_seconds=settings.ollama_translation_timeout_seconds,
            max_output_tokens=2_000,
        )
        vision_provider: TeachingProvider | None = None
        if settings.llm_api_key is not None and settings.llm_paid_calls_allowed:
            vision_provider = DeepSeekTeachingProvider(
                api_key=settings.llm_api_key.get_secret_value(),
                model=DEEPSEEK_MODEL,
                timeout_seconds=settings.llm_timeout_seconds,
            )
        provider = RoutedTeachingProvider(text_provider, vision_provider)
    else:
        if settings.llm_provider.casefold() != "deepseek":
            raise ValueError("教学内容目前只支持 Fake、Ollama 或 DeepSeek Provider")
        if not settings.llm_paid_calls_allowed:
            raise ValueError("DeepSeek 教学模式需要显式付费许可")
        if settings.llm_api_key is None:
            raise ValueError("DeepSeek 教学模式需要 LLM_API_KEY")
        if settings.llm_model != DEEPSEEK_MODEL:
            raise ValueError(f"DeepSeek model must be exactly {DEEPSEEK_MODEL}")
        provider = DeepSeekTeachingProvider(
            api_key=settings.llm_api_key.get_secret_value(),
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
        # Keep translation local even when DeepSeek is selected for the main lesson.
        # If Ollama is unavailable, TeachingService transparently uses the English source.
        translation_provider = OllamaTranslationProvider(
            model=settings.ollama_fast_model or OLLAMA_FAST_MODEL,
            base_url=settings.ollama_base_url,
            timeout_seconds=settings.ollama_translation_timeout_seconds,
            max_output_tokens=2_000,
        )
        topic_provider = OllamaTopicSuggestionProvider(
            model=settings.ollama_balanced_model,
            base_url=settings.ollama_base_url,
            timeout_seconds=settings.ollama_translation_timeout_seconds,
            max_output_tokens=2_000,
        )
    return TeachingService(
        document_library,
        SQLiteLessonRepository(database),
        provider,
        SQLiteLessonProgressRepository(database),
        translation_provider=translation_provider,
        topic_provider=topic_provider,
    )
