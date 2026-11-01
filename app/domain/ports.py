"""Ports implemented by infrastructure adapters."""

from __future__ import annotations

from typing import Any, Protocol

from app.domain.entities import Chunk, Document, IndexedChunk


class DocumentRepository(Protocol):
    def find_by_hash(self, content_hash: str) -> Document | None: ...

    def add_document(self, document: Document, chunks: list[Chunk]) -> None: ...

    def list_documents(self) -> list[Document]: ...

    def list_indexed_chunks(self) -> list[IndexedChunk]: ...

    def delete_document(self, document_id: str) -> bool: ...

    def stats(self) -> dict[str, int]: ...


class AIProvider(Protocol):
    @property
    def is_configured(self) -> bool: ...

    async def embed_text(self, text: str) -> list[float]: ...

    async def complete(self, messages: list[dict[str, str]]) -> str: ...
