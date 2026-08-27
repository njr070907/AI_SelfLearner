"""Background AI topic extraction for source-first conventional teaching."""

from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from ai_growth_companion.providers.base import (
    TopicSuggestionProvider,
    TopicSuggestionRequest,
)

TopicSuggestionStatus = Literal["pending", "ready", "fallback", "unavailable"]
MAX_TOPIC_SOURCE_CHARS = 50_000
MAX_TOPIC_COUNT = 8
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TOPIC_CACHE_ROOT = PROJECT_ROOT / "data" / "topic_suggestions"
_TOPIC_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="ai-selflearner-topics",
)
_TOPIC_JOBS: dict[Path, Future[None]] = {}
_TOPIC_LOCK = Lock()


class TopicSuggestion(BaseModel):
    """One learner-facing topic choice derived from uploaded source material."""

    model_config = ConfigDict(frozen=True)

    suggestion_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=600)
    key_concepts: tuple[str, ...] = Field(default=(), max_length=8)
    confidence: Literal["high", "medium", "low"] = "medium"
    source_document_ids: tuple[str, ...] = Field(default=(), max_length=20)


@dataclass(frozen=True)
class TopicSuggestionResult:
    """Typed topic analysis state suitable for the Streamlit page."""

    suggestions: tuple[TopicSuggestion, ...]
    status: TopicSuggestionStatus
    model_name: str | None = None


class TopicSuggestionService:
    """Queue topic extraction and persist content-addressed results locally."""

    def __init__(
        self,
        provider: TopicSuggestionProvider | None = None,
        *,
        cache_root: Path | None = None,
    ) -> None:
        self.provider = provider
        self.cache_root = (cache_root or DEFAULT_TOPIC_CACHE_ROOT).resolve()

    def get_or_schedule(
        self,
        *,
        source_text: str,
        source_labels: tuple[tuple[str, str], ...],
        source_signature: str,
        request_id: str,
    ) -> TopicSuggestionResult:
        """Return cached AI topics or queue extraction without blocking the page."""
        fallback = _fallback_topics(source_text, source_labels)
        if not source_text.strip():
            return TopicSuggestionResult(suggestions=fallback, status="unavailable")
        cache = self._read_cache(source_signature)
        if cache is not None:
            suggestions = _parse_topics(
                cache.get("topics"),
                source_signature=source_signature,
                source_document_ids=tuple(document_id for document_id, _ in source_labels),
            )
            if suggestions:
                status = cache.get("status")
                return TopicSuggestionResult(
                    suggestions=suggestions,
                    status="fallback" if status == "fallback" else "ready",
                    model_name=(str(cache.get("model_name")) if cache.get("model_name") else None),
                )
            return TopicSuggestionResult(suggestions=fallback, status="fallback")

        if self.provider is None:
            return TopicSuggestionResult(suggestions=fallback, status="fallback")

        self.schedule(
            source_text=source_text,
            source_labels=source_labels,
            source_signature=source_signature,
            request_id=request_id,
        )
        return TopicSuggestionResult(
            # Keep a clearly labelled deterministic choice available while the
            # optional model runs.  Topic analysis must improve the choices, but
            # it must never become a hard dependency for saving a lesson.
            suggestions=fallback,
            status="pending",
            model_name=self.provider.model_name,
        )

    def schedule(
        self,
        *,
        source_text: str,
        source_labels: tuple[tuple[str, str], ...],
        source_signature: str,
        request_id: str,
    ) -> bool:
        """Submit one topic-analysis job and return immediately."""
        if self.provider is None or not source_text.strip():
            return False
        cache_path = self._cache_path(source_signature)
        if cache_path.is_file():
            return False
        self.cache_root.mkdir(parents=True, exist_ok=True)
        with _TOPIC_LOCK:
            current = _TOPIC_JOBS.get(cache_path)
            if current is not None and not current.done():
                return False
            _TOPIC_JOBS[cache_path] = _TOPIC_EXECUTOR.submit(
                self._run_job,
                source_text,
                source_labels,
                source_signature,
                request_id,
            )
        return True

    def _run_job(
        self,
        source_text: str,
        source_labels: tuple[tuple[str, str], ...],
        source_signature: str,
        request_id: str,
    ) -> None:
        cache_path = self._cache_path(source_signature)
        status = "fallback"
        topics: object = []
        model_name: str | None = self.provider.model_name if self.provider else None
        try:
            if self.provider is None:
                return
            response = self.provider.suggest_topics(
                TopicSuggestionRequest(
                    source_text=source_text[:MAX_TOPIC_SOURCE_CHARS],
                    source_labels=source_labels,
                    max_topics=MAX_TOPIC_COUNT,
                ),
                request_id=request_id,
            )
            parsed = _parse_topics(
                response.content.get("topics") if isinstance(response.content, dict) else None,
                source_signature=source_signature,
                source_document_ids=tuple(document_id for document_id, _ in source_labels),
            )
            if parsed:
                topics = [item.model_dump(mode="json") for item in parsed]
                status = "ready"
                model_name = response.metadata.model
            else:
                topics = [
                    item.model_dump(mode="json")
                    for item in _fallback_topics(source_text, source_labels)
                ]
        except Exception:
            # Background analysis is an enhancement.  Any adapter/runtime
            # failure (including an unexpected local Ollama exception) is
            # converted into a cacheable, selectable fallback.
            topics = [
                item.model_dump(mode="json")
                for item in _fallback_topics(source_text, source_labels)
            ]
        finally:
            self._write_cache(
                source_signature,
                {
                    "status": status,
                    "model_name": model_name,
                    "topics": topics,
                },
            )
            with _TOPIC_LOCK:
                _TOPIC_JOBS.pop(cache_path, None)

    def _cache_path(self, source_signature: str) -> Path:
        safe = hashlib.sha256(source_signature.encode("utf-8")).hexdigest()
        return self.cache_root / f"{safe}.json"

    def _read_cache(self, source_signature: str) -> dict[str, object] | None:
        path = self._cache_path(source_signature)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def _write_cache(self, source_signature: str, value: dict[str, object]) -> None:
        path = self._cache_path(source_signature)
        self.cache_root.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)


def _parse_topics(
    raw_topics: object,
    *,
    source_signature: str,
    source_document_ids: tuple[str, ...],
) -> tuple[TopicSuggestion, ...]:
    if not isinstance(raw_topics, (list, tuple)):
        return ()
    parsed: list[TopicSuggestion] = []
    seen: set[str] = set()
    for raw in list(raw_topics)[:MAX_TOPIC_COUNT]:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title", "")).strip()
        summary = str(raw.get("summary", "")).strip()
        if not title or not summary or title.casefold() in seen:
            continue
        title, summary = _ensure_chinese_labels(title, summary)
        concepts_raw = raw.get("key_concepts", [])
        concepts = (
            tuple(str(item).strip() for item in concepts_raw if str(item).strip())[:8]
            if isinstance(concepts_raw, list)
            else ()
        )
        raw_confidence = raw.get("confidence")
        confidence: Literal["high", "medium", "low"] = (
            cast(Literal["high", "medium", "low"], raw_confidence)
            if raw_confidence in {"high", "medium", "low"}
            else "medium"
        )
        suggestion_id = hashlib.sha256(f"{source_signature}\x00{title}".encode()).hexdigest()[:24]
        parsed.append(
            TopicSuggestion(
                suggestion_id=suggestion_id,
                title=title,
                summary=summary,
                key_concepts=concepts,
                confidence=confidence,
                source_document_ids=source_document_ids,
            )
        )
        seen.add(title.casefold())
    return tuple(parsed)


def _ensure_chinese_labels(title: str, summary: str) -> tuple[str, str]:
    """Keep learner-facing topic choices readable when a model ignores language."""
    if not re.search(r"[\u3400-\u4dbf\u4e00-\u9fff]", title):
        title = f"资料主题：{title}"
    if not re.search(r"[\u3400-\u4dbf\u4e00-\u9fff]", summary):
        summary = f"根据资料整理：{summary}"
    return title[:160], summary[:600]


def _fallback_topics(
    source_text: str,
    source_labels: tuple[tuple[str, str], ...],
) -> tuple[TopicSuggestion, ...]:
    """Produce honest temporary choices when AI analysis is unavailable."""
    candidates: list[str] = []
    for line in source_text.splitlines():
        cleaned = re.sub(r"^\s{0,3}#{1,6}\s*", "", line).strip(" -*•\t")
        if 2 <= len(cleaned) <= 100 and not re.fullmatch(r"[\d\W]+", cleaned):
            candidates.append(cleaned)
    if not candidates:
        for _, filename in source_labels:
            stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
            if stem:
                candidates.append(stem)
    unique = list(dict.fromkeys(candidates))[:MAX_TOPIC_COUNT]
    document_ids = tuple(document_id for document_id, _ in source_labels)
    result: list[TopicSuggestion] = []
    for title in unique:
        suggestion_id = hashlib.sha256(title.encode("utf-8")).hexdigest()[:24]
        localized_title, localized_summary = _ensure_chinese_labels(
            title,
            "AI 主题分析暂时不可用；这是根据资料标题或段落生成的临时选项。",
        )
        result.append(
            TopicSuggestion(
                suggestion_id=f"fallback-{suggestion_id}",
                title=localized_title,
                summary=localized_summary,
                key_concepts=(),
                confidence="low",
                source_document_ids=document_ids,
            )
        )
    return tuple(result)


def source_signature(
    source_labels: tuple[tuple[str, str, str], ...],
) -> str:
    """Build a stable signature from selected document IDs, names and bytes hashes."""
    return json.dumps(source_labels, ensure_ascii=False, separators=(",", ":"))
