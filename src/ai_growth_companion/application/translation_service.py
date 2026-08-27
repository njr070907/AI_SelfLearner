"""Best-effort local translation for source-grounded Chinese lessons.

Translation is deliberately a derived view of a source, never a replacement for
the source itself.  The original text stays in ``TeachingSourceUnit.text`` so
that evidence quotes and PDF page numbers remain auditable after translation.
"""

from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Literal

from ai_growth_companion.providers.base import (
    TeachingSourceUnit,
    TranslationProvider,
    TranslationRequest,
)

TranslationStatus = Literal["not_needed", "pending", "translated", "fallback_original"]

# Small-model calls should remain bounded.  Paragraph boundaries are preferred;
# a hard split is only used for a single oversized paragraph.
MAX_TRANSLATION_CHUNK_CHARS = 4_000
MAX_TRANSLATION_CHUNKS = 24
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TRANSLATION_CACHE_ROOT = PROJECT_ROOT / "data" / "translations"
_BACKGROUND_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="ai-selflearner-translation",
)
_BACKGROUND_JOBS: dict[Path, Future[None]] = {}
_BACKGROUND_LOCK = Lock()


@dataclass(frozen=True)
class TranslationResult:
    """Translated source units plus a user-visible status and model name."""

    units: tuple[TeachingSourceUnit, ...]
    status: TranslationStatus
    model_name: str | None = None
    translated_unit_count: int = 0
    failed_unit_count: int = 0


def detect_source_language(text: str) -> Literal["zh", "en", "mixed", "unknown"]:
    """Detect the dominant script without asking a model or rejecting a file."""
    cjk = len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", text))
    latin_words = re.findall(r"[A-Za-z]{2,}", text)
    latin = sum(len(word) for word in latin_words)
    if cjk == 0 and latin >= 20:
        return "en"
    if latin == 0 and cjk >= 10:
        return "zh"
    if cjk and latin:
        if latin >= cjk * 4:
            return "en"
        if cjk >= latin * 4:
            return "zh"
        return "mixed"
    return "unknown"


def should_translate(text: str) -> bool:
    """Return true only for content that is substantially English/Latin text."""
    return detect_source_language(text) in {"en", "mixed"} and bool(
        re.search(r"[A-Za-z]{2,}", text)
    )


class TranslationService:
    """Translate selected source units while preserving original evidence."""

    def __init__(
        self,
        provider: TranslationProvider | None = None,
        *,
        cache_root: Path | None = None,
    ) -> None:
        self.provider = provider
        self.cache_root = (cache_root or DEFAULT_TRANSLATION_CACHE_ROOT).resolve()

    def schedule_units(
        self,
        units: tuple[TeachingSourceUnit, ...],
        *,
        source_sha256: str,
        request_id: str,
    ) -> bool:
        """Queue translation work and return immediately.

        The executor and cache live at module scope so Streamlit reruns do not
        discard a job.  A content hash makes replacement files use a new cache
        without invalidating the original document's derived translation.
        """
        if (
            self.provider is None
            or not units
            or not should_translate("\n".join(unit.text for unit in units))
        ):
            return False
        cache_path = self._cache_path(source_sha256)
        if cache_path.is_file():
            return False
        self.cache_root.mkdir(parents=True, exist_ok=True)
        with _BACKGROUND_LOCK:
            existing = _BACKGROUND_JOBS.get(cache_path)
            if existing is not None and not existing.done():
                return False
            future = _BACKGROUND_EXECUTOR.submit(
                self._run_background_job,
                units,
                source_sha256,
                request_id,
            )
            _BACKGROUND_JOBS[cache_path] = future
        return True

    def prepare_units(
        self,
        units: tuple[TeachingSourceUnit, ...],
        *,
        source_hashes: dict[str, str],
        request_id: str,
    ) -> TranslationResult:
        """Apply completed upload-time translations without blocking generation."""
        if self.provider is None or not units:
            return TranslationResult(units=units, status="not_needed")
        if not should_translate("\n".join(unit.text for unit in units)):
            return TranslationResult(units=units, status="not_needed")

        by_document: dict[str, list[TeachingSourceUnit]] = {}
        for unit in units:
            by_document.setdefault(unit.document_id, []).append(unit)
        result_units: list[TeachingSourceUnit] = []
        translated_count = 0
        failed_count = 0
        pending = False
        for document_id, document_units in by_document.items():
            source_sha256 = source_hashes.get(document_id, "")
            cache = self._read_cache(source_sha256) if source_sha256 else None
            raw_translations = cache.get("translations", {}) if cache else {}
            translations = raw_translations if isinstance(raw_translations, dict) else {}
            cache_status = cache.get("status") if cache else None
            for unit in document_units:
                translated = translations.get(_unit_key(unit))
                if isinstance(translated, str) and translated.strip():
                    result_units.append(_with_translation(unit, translated))
                    translated_count += 1
                else:
                    result_units.append(unit)
            selected_count = sum(1 for unit in document_units if should_translate(unit.text))
            cached_count = sum(
                1 for unit in document_units if isinstance(translations.get(_unit_key(unit)), str)
            )
            if selected_count and cached_count < selected_count:
                cache_path = self._cache_path(source_sha256) if source_sha256 else None
                if cache_path is not None and _job_is_pending(cache_path):
                    pending = True
                elif source_sha256:
                    queued = self.schedule_units(
                        tuple(document_units),
                        source_sha256=source_sha256,
                        request_id=f"{request_id}:background:{document_id}",
                    )
                    pending = (
                        pending
                        or queued
                        or (cache_path is not None and _job_is_pending(cache_path))
                    )
            if cache_status in {"fallback_original", "translated"}:
                cached_failed = cache.get("failed_unit_count", 0) if cache else 0
                failed_count += max(
                    0,
                    int(cached_failed) if isinstance(cached_failed, int) else 0,
                    selected_count - cached_count,
                )

        if pending:
            status: TranslationStatus = "pending"
        elif translated_count:
            status = "translated"
        else:
            status = "fallback_original"
        return TranslationResult(
            units=tuple(result_units),
            status=status,
            model_name=self.provider.model_name,
            translated_unit_count=translated_count,
            failed_unit_count=failed_count,
        )

    def _run_background_job(
        self,
        units: tuple[TeachingSourceUnit, ...],
        source_sha256: str,
        request_id: str,
    ) -> None:
        cache_path = self._cache_path(source_sha256)
        try:
            result = self.translate_units(units, request_id=request_id)
            translations = {
                _unit_key(unit): unit.translated_text
                for unit in result.units
                if unit.translated_text
            }
            self._write_cache(
                source_sha256,
                {
                    "status": result.status,
                    "model_name": result.model_name,
                    "translated_unit_count": result.translated_unit_count,
                    "failed_unit_count": result.failed_unit_count,
                    "translations": translations,
                },
            )
        finally:
            with _BACKGROUND_LOCK:
                _BACKGROUND_JOBS.pop(cache_path, None)

    def _cache_path(self, source_sha256: str) -> Path:
        safe_hash = (
            source_sha256
            if re.fullmatch(r"[a-fA-F0-9]{32,128}", source_sha256)
            else hashlib.sha256(source_sha256.encode()).hexdigest()
        )
        return self.cache_root / f"{safe_hash.lower()}.json"

    def _read_cache(self, source_sha256: str) -> dict[str, object] | None:
        path = self._cache_path(source_sha256)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def _write_cache(self, source_sha256: str, value: dict[str, object]) -> None:
        path = self._cache_path(source_sha256)
        self.cache_root.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)

    def translate_units(
        self,
        units: tuple[TeachingSourceUnit, ...],
        *,
        request_id: str,
    ) -> TranslationResult:
        """Translate English units; failures fall back to the original text.

        A failed fragment never prevents a lesson from being generated.  Each
        successful translation is attached to its original unit and can therefore
        be used for comprehension while evidence matching still uses ``text``.
        """
        if self.provider is None or not units:
            return TranslationResult(units=units, status="not_needed")
        if not should_translate("\n".join(unit.text for unit in units)):
            return TranslationResult(units=units, status="not_needed")

        translated_units: list[TeachingSourceUnit] = []
        translated_count = 0
        failed_count = 0
        attempted_chunks = 0
        provider_failed = False
        for unit_index, unit in enumerate(units):
            if not should_translate(unit.text):
                translated_units.append(unit)
                continue
            if provider_failed:
                failed_count += 1
                translated_units.append(unit)
                continue
            parts: list[str] = []
            failed = False
            for chunk_index, chunk in enumerate(_split_for_translation(unit.text)):
                if attempted_chunks >= MAX_TRANSLATION_CHUNKS:
                    failed = True
                    break
                attempted_chunks += 1
                try:
                    response = self.provider.translate(
                        TranslationRequest(text=chunk),
                        request_id=f"{request_id}:unit-{unit_index + 1}:chunk-{chunk_index + 1}",
                    )
                    translated = _translated_text(response.content)
                except Exception:
                    # Translation is an optional derived step.  An adapter/runtime
                    # failure must never prevent the original-language lesson from
                    # being generated and saved.  Stop trying subsequent units after
                    # a provider-wide failure so a slow/unavailable local model cannot
                    # occupy the background worker for every paragraph.
                    failed = True
                    provider_failed = True
                    break
                if not translated:
                    failed = True
                    break
                parts.append(translated)
            if failed or not parts:
                failed_count += 1
                translated_units.append(unit)
                continue
            translated_count += 1
            translated_units.append(
                TeachingSourceUnit(
                    document_id=unit.document_id,
                    filename=unit.filename,
                    page_number=unit.page_number,
                    text=unit.text,
                    quality=unit.quality,
                    translated_text="\n\n".join(parts),
                )
            )

        status: TranslationStatus = "fallback_original" if translated_count == 0 else "translated"
        return TranslationResult(
            units=tuple(translated_units),
            status=status,
            model_name=self.provider.model_name,
            translated_unit_count=translated_count,
            failed_unit_count=failed_count,
        )


def build_bilingual_context(units: tuple[TeachingSourceUnit, ...]) -> str:
    """Build model context with Chinese first and exact original text second."""
    parts: list[str] = []
    for unit in units:
        page_label = f"第 {unit.page_number} 页" if unit.page_number is not None else "文本内容"
        translated = (unit.translated_text or "").strip()
        original = unit.text.strip()
        if translated and translated != original:
            parts.append(
                f"【{unit.filename} · {page_label}】\n"
                f"[中文译文]\n{translated}\n"
                f"[英文原文（证据引用必须从这里逐字复制）]\n{original}"
            )
        else:
            parts.append(f"【{unit.filename} · {page_label}】\n{original}")
    return "\n\n".join(parts)


def _translated_text(content: object) -> str:
    if not isinstance(content, dict):
        raise ValueError("translation response must be an object")
    translated = content.get("translated_text")
    if not isinstance(translated, str):
        raise ValueError("translation response is missing translated_text")
    normalized = translated.strip()
    if not normalized or "\ufffd" in normalized:
        raise ValueError("translation response is empty or garbled")
    return normalized


def _unit_key(unit: TeachingSourceUnit) -> str:
    """Identify one immutable source fragment for cache alignment."""
    # The filename is intentionally excluded: renaming a document must not throw
    # away a translation derived from the same bytes and document ID.
    raw = f"{unit.document_id}\x00{unit.page_number}\x00{unit.text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _with_translation(unit: TeachingSourceUnit, translated: str) -> TeachingSourceUnit:
    return TeachingSourceUnit(
        document_id=unit.document_id,
        filename=unit.filename,
        page_number=unit.page_number,
        text=unit.text,
        quality=unit.quality,
        translated_text=translated.strip(),
    )


def _job_is_pending(cache_path: Path) -> bool:
    with _BACKGROUND_LOCK:
        future = _BACKGROUND_JOBS.get(cache_path)
        return future is not None and not future.done()


def _split_for_translation(text: str) -> tuple[str, ...]:
    normalized = text.strip()
    if len(normalized) <= MAX_TRANSLATION_CHUNK_CHARS:
        return (normalized,)
    chunks: list[str] = []
    current = ""
    for paragraph in re.split(r"\n\s*\n", normalized):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) > MAX_TRANSLATION_CHUNK_CHARS:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(
                paragraph[index : index + MAX_TRANSLATION_CHUNK_CHARS]
                for index in range(0, len(paragraph), MAX_TRANSLATION_CHUNK_CHARS)
            )
            continue
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > MAX_TRANSLATION_CHUNK_CHARS:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return tuple(chunks) or (normalized[:MAX_TRANSLATION_CHUNK_CHARS],)
