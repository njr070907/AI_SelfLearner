"""Deterministic, local topic-to-document selection for conventional teaching."""

from __future__ import annotations

import io
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pypdf import PdfReader

from ai_growth_companion.application.document_library import (
    DocumentLibraryService,
    DocumentValidationError,
)
from ai_growth_companion.application.models import DocumentView

MAX_SAMPLE_CHARS = 80_000
DEFAULT_RECOMMENDATION_LIMIT = 3
MAX_RECOMMENDATIONS = 8

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]+")
_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,}")
_PAGE_RANGE_PATTERN = re.compile(r"_pages_(\d+)-(\d+)", re.IGNORECASE)

# These aliases cover the first materials already in the local library. They are
# deliberately small and deterministic; adding a large semantic ontology here
# would turn this MVP helper into an unreviewable pseudo-RAG system.
_TOPIC_ALIASES: dict[str, tuple[str, ...]] = {
    "函数": ("function", "functions"),
    "函数极限": ("limit", "limits", "function", "functions"),
    "极限": ("limit", "limits"),
    "导数": ("derivative", "derivatives"),
    "积分": ("integral", "integrals"),
    "向量": ("vector", "vectors"),
    "矩阵": ("matrix", "matrices"),
    "线性代数": ("linear algebra", "matrix", "matrices", "vector", "vectors"),
    "特征值": ("eigenvalue", "eigenvalues"),
}


class SourceSelectionMatch(BaseModel):
    """A document candidate with an explainable local match score."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    filename: str
    score: int = Field(ge=0)
    matched_terms: tuple[str, ...]
    rationale: str
    page_range: str | None = None


class TopicSourceSelection(BaseModel):
    """Topic-based recommendations that the UI can accept or override."""

    model_config = ConfigDict(frozen=True)

    topic: str
    confidence: Literal["high", "medium", "low"]
    requires_manual_selection: bool
    requires_confirmation: bool
    selected_document_ids: tuple[str, ...]
    matches: tuple[SourceSelectionMatch, ...]


class TopicSourceSelector:
    """Select likely material chunks without a network call or vector database."""

    def __init__(self, document_library: DocumentLibraryService) -> None:
        self.document_library = document_library
        self._sample_cache: dict[tuple[str, str], str] = {}

    def recommend(
        self,
        *,
        topic: str,
        document_ids: tuple[str, ...] | None = None,
        limit: int = DEFAULT_RECOMMENDATION_LIMIT,
    ) -> TopicSourceSelection:
        normalized_topic = topic.strip()
        if not normalized_topic:
            raise ValueError("请先填写学习主题，再自动选择资料")
        bounded_limit = max(1, min(limit, MAX_RECOMMENDATIONS))
        documents = self._documents(document_ids)
        primary_terms, related_terms = self._terms_for_topic(normalized_topic)
        matches: list[SourceSelectionMatch] = []
        for document in documents:
            try:
                sample = self._sample_document(document)
            except (DocumentValidationError, LookupError):
                continue
            score, matched_terms = self._score(
                topic=normalized_topic,
                primary_terms=primary_terms,
                related_terms=related_terms,
                filename=document.filename,
                sample=sample,
            )
            if score <= 0:
                continue
            matches.append(
                SourceSelectionMatch(
                    document_id=document.document_id,
                    filename=document.filename,
                    score=score,
                    matched_terms=tuple(matched_terms),
                    rationale=self._rationale(score, matched_terms),
                    page_range=self._page_range(document.filename),
                )
            )

        matches.sort(key=lambda item: (-item.score, item.filename.casefold()))
        confidence = self._confidence(matches)
        selected = self._selected_matches(matches, confidence=confidence, limit=bounded_limit)
        return TopicSourceSelection(
            topic=normalized_topic,
            confidence=confidence,
            requires_manual_selection=confidence == "low",
            requires_confirmation=confidence != "high",
            selected_document_ids=tuple(match.document_id for match in selected),
            matches=tuple(matches[:MAX_RECOMMENDATIONS]),
        )

    def _documents(self, document_ids: tuple[str, ...] | None) -> tuple[DocumentView, ...]:
        if document_ids is None:
            return self.document_library.list_documents()
        return tuple(self.document_library.get(document_id) for document_id in document_ids)

    def _sample_document(self, document: DocumentView) -> str:
        cache_key = (document.document_id, document.sha256)
        cached = self._sample_cache.get(cache_key)
        if cached is not None:
            return cached
        _view, content = self.document_library.read(document.document_id)
        extension = Path(document.filename).suffix.casefold()
        if extension in {".md", ".markdown", ".txt"}:
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError as error:
                raise DocumentValidationError("资料不是 UTF-8 文本") from error
            sample = self._normalize(text[:MAX_SAMPLE_CHARS])
            self._sample_cache[cache_key] = sample
            return sample
        if extension != ".pdf":
            return ""
        try:
            reader = PdfReader(io.BytesIO(content))
            page_count = len(reader.pages)
            if page_count == 0:
                return ""
            indexes = {0, page_count // 2, page_count - 1}
            text = "\n\n".join(
                reader.pages[index].extract_text() or "" for index in sorted(indexes)
            )
        except Exception as error:
            raise DocumentValidationError("PDF 无法读取") from error
        sample = self._normalize(text[:MAX_SAMPLE_CHARS])
        self._sample_cache[cache_key] = sample
        return sample

    @classmethod
    def _score(
        cls,
        *,
        topic: str,
        primary_terms: tuple[str, ...],
        related_terms: tuple[str, ...],
        filename: str,
        sample: str,
    ) -> tuple[int, list[str]]:
        compact_topic = cls._compact(topic)
        compact_filename = cls._compact(filename)
        compact_sample = cls._compact(sample)
        score = 0
        matched: list[str] = []

        topic_hits = compact_sample.count(compact_topic)
        if topic_hits:
            score += min(topic_hits, 20) * 4
            matched.append(topic)
        if compact_topic in compact_filename:
            score += 10
            matched.append(f"文件名:{topic}")

        for term in primary_terms:
            hits = compact_sample.count(cls._compact(term))
            if hits:
                score += min(hits, 12)
                if term not in matched:
                    matched.append(term)
        for term in related_terms:
            hits = compact_sample.count(cls._compact(term))
            if hits:
                score += min(hits, 6) * 3
                if term not in matched:
                    matched.append(term)
            if cls._compact(term) in compact_filename:
                score += 4
                if term not in matched:
                    matched.append(f"文件名:{term}")
        return score, matched[:8]

    @staticmethod
    def _terms_for_topic(topic: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
        normalized = TopicSourceSelector._normalize(topic)
        primary: list[str] = [normalized]
        for token in _TOKEN_PATTERN.findall(normalized):
            if len(token) > 1 and token not in primary:
                primary.append(token)
            if token.endswith("ies") and len(token) > 3:
                primary.append(token[:-3] + "y")
            elif token.endswith("es") and len(token) > 3:
                primary.append(token[:-2])
            elif token.endswith("s") and len(token) > 2:
                primary.append(token[:-1])

        related = list(_TOPIC_ALIASES.get(normalized, ()))
        for phrase in _CJK_PATTERN.findall(normalized):
            for index in range(len(phrase) - 1):
                bigram = phrase[index : index + 2]
                if bigram not in primary:
                    primary.append(bigram)
        return tuple(dict.fromkeys(primary)), tuple(dict.fromkeys(related))

    @staticmethod
    def _confidence(matches: list[SourceSelectionMatch]) -> Literal["high", "medium", "low"]:
        if not matches:
            return "low"
        if matches[0].score >= 6 and (
            len(matches) == 1 or matches[0].score >= matches[1].score * 1.5
        ):
            return "high"
        return "medium"

    @staticmethod
    def _selected_matches(
        matches: list[SourceSelectionMatch],
        *,
        confidence: Literal["high", "medium", "low"],
        limit: int,
    ) -> tuple[SourceSelectionMatch, ...]:
        if not matches:
            return ()
        if confidence == "low":
            return ()
        threshold = max(2, int(matches[0].score * 0.45))
        selected = [match for match in matches if match.score >= threshold]
        if confidence == "medium":
            selected = selected[:limit]
        return tuple(selected[:limit])

    @staticmethod
    def _rationale(score: int, matched_terms: Iterable[str]) -> str:
        terms = "、".join(matched_terms) or "文字抽样"
        return f"本地文字抽样匹配分数 {score}；命中 {terms}"

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.casefold().split())

    @staticmethod
    def _compact(text: str) -> str:
        return re.sub(r"\s+", "", text.casefold())

    @staticmethod
    def _page_range(filename: str) -> str | None:
        match = _PAGE_RANGE_PATTERN.search(filename)
        if match is None:
            return None
        return f"第 {int(match.group(1))}-{int(match.group(2))} 页"
