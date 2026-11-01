"""Markdown-aware chunking that carries section headings into each chunk."""

from __future__ import annotations

import re


class TextChunker:
    def __init__(self, target_chars: int, overlap_chars: int) -> None:
        self.target_chars = target_chars
        self.overlap_chars = min(overlap_chars, target_chars // 2)

    def split(self, text: str) -> list[tuple[str, str]]:
        sections = self._sections(text)
        chunks: list[tuple[str, str]] = []
        for heading_path, content in sections:
            chunks.extend(self._split_section(heading_path, content))
        return chunks

    @staticmethod
    def _sections(text: str) -> list[tuple[str, str]]:
        headings: list[str] = []
        sections: list[tuple[str, str]] = []
        current_lines: list[str] = []

        def flush() -> None:
            content = "\n".join(current_lines).strip()
            if content:
                sections.append((" > ".join(headings), content))
            current_lines.clear()

        for line in text.splitlines():
            match = re.match(r"^(#{1,3})\s+(.+?)\s*#*\s*$", line)
            if match:
                flush()
                level = len(match.group(1))
                headings[:] = headings[: level - 1]
                headings.append(match.group(2).strip())
            else:
                current_lines.append(line)
        flush()
        return sections or [("", text.strip())]

    def _split_section(self, heading_path: str, content: str) -> list[tuple[str, str]]:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
        pieces: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if len(paragraph) > self.target_chars:
                if current:
                    pieces.append(current)
                    current = ""
                pieces.extend(self._split_long_paragraph(paragraph))
                continue
            candidate = f"{current}\n\n{paragraph}" if current else paragraph
            if len(candidate) > self.target_chars and current:
                pieces.append(current)
                current = paragraph
            else:
                current = candidate
        if current:
            pieces.append(current)
        prefix = f"{heading_path}\n" if heading_path else ""
        return [(f"{prefix}{piece}".strip(), heading_path) for piece in pieces]

    def _split_long_paragraph(self, paragraph: str) -> list[str]:
        result: list[str] = []
        start = 0
        while start < len(paragraph):
            end = min(start + self.target_chars, len(paragraph))
            if end < len(paragraph):
                floor = start + int(self.target_chars * 0.65)
                boundary = max(
                    paragraph.rfind(" ", floor, end),
                    paragraph.rfind("۔", floor, end),
                    paragraph.rfind("؟", floor, end),
                )
                if boundary > floor:
                    end = boundary + 1
            piece = paragraph[start:end].strip()
            if piece:
                result.append(piece)
            if end >= len(paragraph):
                break
            start = max(start + 1, end - self.overlap_chars)
        return result
