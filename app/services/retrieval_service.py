"""Hybrid vector and lexical retrieval with Reciprocal Rank Fusion."""

from __future__ import annotations

import math
from collections import Counter, defaultdict

from app.core.errors import ProviderError
from app.domain.entities import IndexedChunk, RetrievedSource
from app.domain.ports import AIProvider, DocumentRepository
from app.domain.text_normalizer import PersianTextNormalizer


class HybridRetriever:
    STOP_WORDS = {
        "از", "به", "با", "در", "برای", "که", "را", "و", "یا", "این", "آن", "یک", "چه", "چطور", "چگونه",
        "است", "هست", "شود", "شده", "می", "من", "ما", "شما", "رو", "هم", "تا", "اگر", "پس", "اما", "روی",
    }

    def __init__(
        self,
        repository: DocumentRepository,
        ai_provider: AIProvider,
        normalizer: PersianTextNormalizer,
        top_k: int = 6,
        rrf_constant: int = 60,
        similarity_floor: float = 0.24,
    ) -> None:
        self.repository = repository
        self.ai_provider = ai_provider
        self.normalizer = normalizer
        self.top_k = top_k
        self.rrf_constant = rrf_constant
        self.similarity_floor = similarity_floor

    async def retrieve(self, query: str) -> list[RetrievedSource]:
        chunks = self.repository.list_indexed_chunks()
        if not chunks:
            return []
        query_terms = self._terms(query)
        keyword_rank = self._rank_keywords(chunks, query_terms)
        vector_rank: list[tuple[float, int]] = []
        if self.ai_provider.is_configured and any(chunk.embedding for chunk in chunks):
            try:
                query_vector = await self.ai_provider.embed_text(query)
                vector_rank = sorted(
                    (
                        (self._cosine(query_vector, chunk.embedding), index)
                        for index, chunk in enumerate(chunks)
                        if chunk.embedding
                    ),
                    reverse=True,
                )
            except ProviderError:
                # Keyword retrieval remains available during provider outages.
                vector_rank = []

        fused_scores: defaultdict[int, float] = defaultdict(float)
        for rank, (_, index) in enumerate(vector_rank, start=1):
            fused_scores[index] += 1 / (self.rrf_constant + rank)
        for rank, (_, index) in enumerate(keyword_rank, start=1):
            fused_scores[index] += 1 / (self.rrf_constant + rank)

        vector_scores = {index: score for score, index in vector_rank}
        keyword_scores = {index: score for score, index in keyword_rank}
        candidates = sorted(fused_scores, key=fused_scores.__getitem__, reverse=True)
        results: list[RetrievedSource] = []
        for index in candidates:
            vector_score = vector_scores.get(index, 0.0)
            keyword_score = keyword_scores.get(index, 0.0)
            if vector_score < self.similarity_floor and keyword_score <= 0:
                continue
            chunk = chunks[index]
            results.append(
                RetrievedSource(
                    id=chunk.document_id,
                    chunk_id=chunk.id,
                    title=chunk.title,
                    filename=chunk.filename,
                    category=chunk.category,
                    heading_path=chunk.heading_path,
                    snippet=chunk.content,
                    score=round(max(vector_score, min(keyword_score / 4, 1.0)), 4),
                )
            )
            if len(results) == self.top_k:
                break
        return results

    def _rank_keywords(self, chunks: list[IndexedChunk], query_terms: list[str]) -> list[tuple[float, int]]:
        if not query_terms:
            return []
        term_counts = [Counter(self._terms(chunk.content)) for chunk in chunks]
        document_frequency = Counter(term for counts in term_counts for term in counts.keys())
        total_documents = len(chunks)
        average_length = sum(sum(counts.values()) for counts in term_counts) / max(total_documents, 1)
        ranked: list[tuple[float, int]] = []
        for index, counts in enumerate(term_counts):
            length = sum(counts.values()) or 1
            score = 0.0
            for term in query_terms:
                frequency = counts.get(term, 0)
                if not frequency:
                    continue
                frequency_in_corpus = document_frequency[term]
                inverse = math.log(1 + (total_documents - frequency_in_corpus + 0.5) / (frequency_in_corpus + 0.5))
                score += inverse * (frequency * 2.2) / (
                    frequency + 1.2 * (0.25 + 0.75 * length / max(average_length, 1))
                )
            if score > 0:
                ranked.append((score, index))
        return sorted(ranked, reverse=True)

    def _terms(self, text: str) -> list[str]:
        return [term for term in self.normalizer.tokenize(text) if len(term) > 1 and term not in self.STOP_WORDS]

    @staticmethod
    def _cosine(first: list[float], second: list[float] | None) -> float:
        if not second or len(first) != len(second):
            return 0.0
        dot = sum(left * right for left, right in zip(first, second))
        norm_first = math.sqrt(sum(value * value for value in first))
        norm_second = math.sqrt(sum(value * value for value in second))
        return dot / (norm_first * norm_second) if norm_first and norm_second else 0.0
