"""OpenAI-compatible AvalAI adapter for embeddings and chat completions."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings
from app.core.errors import ProviderError


class AvalAIClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._http_client = httpx.AsyncClient(timeout=settings.timeout_seconds)

    @property
    def is_configured(self) -> bool:
        return self.settings.ai_enabled and self.settings.provider_configured

    async def embed_text(self, text: str) -> list[float]:
        response = await self._post(
            "embeddings",
            {"model": self.settings.embedding_model, "input": text},
        )
        try:
            return [float(value) for value in response["data"][0]["embedding"]]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ProviderError("پاسخ embedding از AvalAI ساختار معتبری نداشت.") from error

    async def complete(self, messages: list[dict[str, str]]) -> str:
        response = await self._post(
            "chat/completions",
            {
                "model": self.settings.chat_model,
                "messages": messages,
                "max_completion_tokens": self.settings.max_output_tokens,
            },
        )
        try:
            content: Any = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderError("پاسخ متنی معتبری از AvalAI دریافت نشد.") from error
        if isinstance(content, list):
            content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("پاسخ AvalAI خالی بود.")
        return content.strip()

    async def close(self) -> None:
        await self._http_client.aclose()

    async def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.provider_configured:
            raise ProviderError("کلید AvalAI در تنظیمات سرور تعریف نشده است.")
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            response = await self._http_client.post(
                f"{self.settings.base_url}/{endpoint}",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as error:
            raise ProviderError(f"سرویس AvalAI با وضعیت {error.response.status_code} پاسخ داد.") from error
        except (httpx.RequestError, ValueError) as error:
            raise ProviderError("ارتباط با سرویس AvalAI برقرار نشد یا زمان پاسخ تمام شد.") from error
        if not isinstance(data, dict):
            raise ProviderError("پاسخ AvalAI معتبر نیست.")
        return data
