"""Document ingestion workflow: validate, extract, normalize, chunk and index."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.errors import ApplicationError, ProviderError
from app.domain.entities import Chunk, Document
from app.domain.ports import AIProvider, DocumentRepository
from app.domain.text_chunker import TextChunker
from app.domain.text_normalizer import PersianTextNormalizer
from app.infrastructure.parsers.document_parser import DocumentParser


class DocumentService:
    def __init__(
        self,
        settings: Settings,
        repository: DocumentRepository,
        parser: DocumentParser,
        normalizer: PersianTextNormalizer,
        chunker: TextChunker,
        ai_provider: AIProvider,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.parser = parser
        self.normalizer = normalizer
        self.chunker = chunker
        self.ai_provider = ai_provider

    async def add_document(
        self,
        filename: str,
        media_type: str,
        raw: bytes,
        category: str = "عمومی",
    ) -> dict[str, Any]:
        if not raw:
            raise ApplicationError("فایل خالی است.")
        if len(raw) > self.settings.max_file_bytes:
            max_mb = self.settings.max_file_bytes // (1024 * 1024)
            raise ApplicationError(f"حجم فایل باید کمتر از {max_mb} مگابایت باشد.")

        safe_filename = Path(filename.replace("\\", "/")).name[:180] or "document.txt"
        content_hash = hashlib.sha256(raw).hexdigest()
        existing = self.repository.find_by_hash(content_hash)
        if existing:
            return {
                "id": existing.id,
                "title": existing.title,
                "filename": existing.filename,
                "chunks": existing.chunk_count,
                "embedded": existing.embedded_count,
                "duplicate": True,
            }

        extracted = self.parser.extract_text(safe_filename, media_type, raw)
        normalized = self.normalizer.normalize_document(extracted)
        pieces = self.chunker.split(normalized)
        if not pieces:
            raise ApplicationError("از این سند قطعه‌ی قابل‌بازیابی ساخته نشد.")

        document_id = uuid.uuid4().hex
        chunks: list[Chunk] = []
        warning: str | None = None
        embedded_count = 0
        for chunk_index, (content, heading_path) in enumerate(pieces):
            embedding = None
            if self.ai_provider.is_configured and warning is None:
                try:
                    embedding = await self.ai_provider.embed_text(content)
                    embedded_count += 1
                except ProviderError as error:
                    warning = str(error)
            chunks.append(
                Chunk(
                    id=uuid.uuid4().hex,
                    document_id=document_id,
                    chunk_index=chunk_index,
                    content=content,
                    heading_path=heading_path,
                    embedding=embedding,
                )
            )

        title = Path(safe_filename).stem.replace("_", " ").replace("-", " ").strip() or "سند بدون عنوان"
        clean_category = " ".join(str(category).split())[:60] or "عمومی"
        document = Document(
            id=document_id,
            title=title[:180],
            filename=safe_filename,
            category=clean_category,
            media_type=media_type or "application/octet-stream",
            byte_size=len(raw),
            char_count=len(normalized),
            content_hash=content_hash,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            chunk_count=len(chunks),
            embedded_count=embedded_count,
        )
        self.repository.add_document(document, chunks)
        return {
            "id": document.id,
            "title": document.title,
            "filename": document.filename,
            "chunks": len(chunks),
            "embedded": embedded_count,
            "duplicate": False,
            "warning": warning,
        }

    def list_documents(self) -> list[dict[str, Any]]:
        return [asdict(document) for document in self.repository.list_documents()]

    def stats(self) -> dict[str, int]:
        return self.repository.stats()

    def delete_document(self, document_id: str) -> bool:
        return self.repository.delete_document(document_id)

    async def import_samples(self) -> list[dict[str, Any]]:
        if not self.settings.sample_documents_path.is_dir():
            return []
        results = []
        for sample in sorted(self.settings.sample_documents_path.glob("*.md")):
            result = await self.add_document(
                filename=sample.name,
                media_type="text/markdown",
                raw=sample.read_bytes(),
                category="نمونه آموزشی",
            )
            results.append(result)
        return results
