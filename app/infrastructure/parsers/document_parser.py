"""Extract searchable text from supported document formats."""

from __future__ import annotations

import re
import zipfile
from html import unescape
from io import BytesIO
from xml.etree import ElementTree

from app.core.errors import ApplicationError


class DocumentParser:
    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".log", ".html", ".htm"}

    def extract_text(self, filename: str, media_type: str, raw: bytes) -> str:
        extension = self._extension(filename)
        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ApplicationError("قالب فایل پشتیبانی نمی‌شود. PDF، DOCX، TXT، Markdown، CSV و HTML مجاز هستند.")
        try:
            if extension == ".pdf":
                text = self._extract_pdf(raw)
            elif extension == ".docx":
                text = self._extract_docx(raw)
            else:
                text = raw.decode("utf-8-sig", errors="replace")
                if extension in {".html", ".htm"}:
                    text = self._extract_html(text)
        except ImportError as error:
            raise ApplicationError("وابستگی خواندن PDF نصب نشده است؛ در backend دستور pip install -r requirements.txt را اجرا کنید.", 503) from error
        except (ValueError, zipfile.BadZipFile, ElementTree.ParseError) as error:
            raise ApplicationError("خواندن فایل ممکن نشد؛ مطمئن شوید فایل خراب نیست.") from error
        text = text.replace("\x00", "")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if len(text) < 25:
            raise ApplicationError("متن قابل‌استفاده‌ای از فایل استخراج نشد.")
        return text

    @staticmethod
    def _extension(filename: str) -> str:
        return "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    @staticmethod
    def _extract_pdf(raw: bytes) -> str:
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(raw))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            raise
        except Exception as error:
            raise ApplicationError("خواندن PDF ممکن نشد؛ فایل را بررسی کنید یا از OCR برای فایل اسکن‌شده استفاده کنید.") from error

    @staticmethod
    def _extract_docx(raw: bytes) -> str:
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            document_xml = archive.read("word/document.xml")
        root = ElementTree.fromstring(document_xml)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        for paragraph in root.findall(".//w:p", namespace):
            text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace))
            if text.strip():
                paragraphs.append(text)
        return "\n".join(paragraphs)

    @staticmethod
    def _extract_html(text: str) -> str:
        text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        return unescape(text)
