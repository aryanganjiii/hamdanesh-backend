"""Consistent Persian normalization for both indexing and user queries."""

from __future__ import annotations

import re
import unicodedata


class PersianTextNormalizer:
    _translation = str.maketrans(
        {
            "ي": "ی",
            "ى": "ی",
            "ك": "ک",
            "ۀ": "ه",
            "ة": "ه",
            "أ": "ا",
            "إ": "ا",
        }
    )

    def normalize_document(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text).translate(self._translation)
        normalized = re.sub(r"[\u064b-\u065f\u0670\u0640]", "", normalized)
        normalized = normalized.replace("\u200c", " ")
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n[ \t]+", "\n", normalized)
        return re.sub(r"\n{3,}", "\n\n", normalized).strip()

    def normalize_query(self, text: str) -> str:
        return re.sub(r"\s+", " ", self.normalize_document(text)).strip().lower()

    def tokenize(self, text: str) -> list[str]:
        normalized = self.normalize_query(text)
        return re.findall(r"[a-z0-9_]+|[\u0600-\u06ff]{2,}", normalized)
