"""Repository that maps domain documents and chunks to SQLite rows."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.domain.entities import Chunk, Document, IndexedChunk
from app.infrastructure.persistence.sqlite_database import SQLiteDatabase


class SQLiteDocumentRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def find_by_hash(self, content_hash: str) -> Document | None:
        with self.database.connection() as connection:
            row = connection.execute(
                """SELECT d.*, COUNT(c.id) AS chunk_count,
                          SUM(CASE WHEN c.embedding IS NOT NULL THEN 1 ELSE 0 END) AS embedded_count
                   FROM documents d LEFT JOIN chunks c ON c.document_id=d.id
                   WHERE d.content_hash = ? GROUP BY d.id""",
                (content_hash,),
            ).fetchone()
            if row is None:
                return None
            return self._document_from_row(row)

    def add_document(self, document: Document, chunks: list[Chunk]) -> None:
        with self.database.connection() as connection:
            connection.execute(
                """INSERT INTO documents(id,title,filename,category,media_type,byte_size,char_count,content_hash,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    document.id,
                    document.title,
                    document.filename,
                    document.category,
                    document.media_type,
                    document.byte_size,
                    document.char_count,
                    document.content_hash,
                    document.created_at,
                ),
            )
            connection.executemany(
                """INSERT INTO chunks(id,document_id,chunk_index,content,heading_path,embedding)
                   VALUES(?,?,?,?,?,?)""",
                [
                    (
                        chunk.id,
                        chunk.document_id,
                        chunk.chunk_index,
                        chunk.content,
                        chunk.heading_path,
                        json.dumps(chunk.embedding, separators=(",", ":")) if chunk.embedding else None,
                    )
                    for chunk in chunks
                ],
            )

    def list_documents(self) -> list[Document]:
        with self.database.connection() as connection:
            rows = connection.execute(
                """SELECT d.*, COUNT(c.id) AS chunk_count,
                          SUM(CASE WHEN c.embedding IS NOT NULL THEN 1 ELSE 0 END) AS embedded_count
                   FROM documents d LEFT JOIN chunks c ON c.document_id=d.id
                   GROUP BY d.id ORDER BY d.created_at DESC"""
            ).fetchall()
        return [self._document_from_row(row) for row in rows]

    def list_indexed_chunks(self) -> list[IndexedChunk]:
        with self.database.connection() as connection:
            rows = connection.execute(
                """SELECT c.id,c.document_id,c.content,c.heading_path,c.embedding,
                          d.title,d.filename,d.category
                   FROM chunks c JOIN documents d ON d.id=c.document_id"""
            ).fetchall()
        return [self._indexed_chunk_from_row(row) for row in rows]

    def delete_document(self, document_id: str) -> bool:
        with self.database.connection() as connection:
            cursor = connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            return cursor.rowcount > 0

    def stats(self) -> dict[str, int]:
        with self.database.connection() as connection:
            row = connection.execute(
                """SELECT COUNT(DISTINCT d.id) AS documents, COUNT(c.id) AS chunks,
                          SUM(CASE WHEN c.embedding IS NOT NULL THEN 1 ELSE 0 END) AS embedded_chunks
                   FROM documents d LEFT JOIN chunks c ON c.document_id=d.id"""
            ).fetchone()
        return {
            "documents": int(row["documents"] or 0),
            "chunks": int(row["chunks"] or 0),
            "embedded_chunks": int(row["embedded_chunks"] or 0),
        }

    @staticmethod
    def _document_from_row(row: sqlite3.Row) -> Document:
        keys = set(row.keys())
        return Document(
            id=row["id"],
            title=row["title"],
            filename=row["filename"],
            category=row["category"],
            media_type=row["media_type"],
            byte_size=int(row["byte_size"]),
            char_count=int(row["char_count"]),
            content_hash=row["content_hash"],
            created_at=row["created_at"],
            chunk_count=int(row["chunk_count"] or 0) if "chunk_count" in keys else 0,
            embedded_count=int(row["embedded_count"] or 0) if "embedded_count" in keys else 0,
        )

    @staticmethod
    def _indexed_chunk_from_row(row: sqlite3.Row) -> IndexedChunk:
        embedding: list[float] | None = None
        if row["embedding"]:
            try:
                embedding = [float(value) for value in json.loads(row["embedding"])]
            except (TypeError, ValueError, json.JSONDecodeError):
                embedding = None
        return IndexedChunk(
            id=row["id"],
            document_id=row["document_id"],
            content=row["content"],
            heading_path=row["heading_path"],
            embedding=embedding,
            title=row["title"],
            filename=row["filename"],
            category=row["category"],
        )
