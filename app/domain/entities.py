"""Core entities shared by the application's services and adapters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    title: str
    filename: str
    category: str
    media_type: str
    byte_size: int
    char_count: int
    content_hash: str
    created_at: str
    chunk_count: int = 0
    embedded_count: int = 0


@dataclass(frozen=True, slots=True)
class Chunk:
    id: str
    document_id: str
    chunk_index: int
    content: str
    heading_path: str
    embedding: list[float] | None = None


@dataclass(frozen=True, slots=True)
class IndexedChunk:
    id: str
    document_id: str
    content: str
    heading_path: str
    embedding: list[float] | None
    title: str
    filename: str
    category: str


@dataclass(frozen=True, slots=True)
class RetrievedSource:
    id: str
    chunk_id: str
    title: str
    filename: str
    category: str
    snippet: str
    score: float
    heading_path: str = ""


@dataclass(frozen=True, slots=True)
class ChatAnswer:
    answer: str
    sources: list[RetrievedSource]
    refused: bool
