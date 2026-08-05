"""OpenAI、Gemini 与本地模型 Provider。"""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

import httpx

from jobos.core.errors import LLMConfigurationError, LLMError
from jobos.llm.schemas import LLMRequest, LLMResponse, ProviderHealth


class OpenAICompatibleProvider:
    """兼容 OpenAI Chat Completions 的 Provider。"""

    def __init__(self, name: str, base_url: str | None, api_key: str | None) -> None:
        self.name = name
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key

    async def health_check(self) -> ProviderHealth:
        """只检查配置，不主动消耗模型额度。"""
        return ProviderHealth(available=bool(self.base_url and self.api_key), detail=self.base_url)

    async def generate(self, request: LLMRequest, model: str) -> LLMResponse:
        """调用 OpenAI 兼容接口。"""
        if not self.api_key:
            raise LLMConfigurationError(f"{self.name} 未配置 API Key")
        payload: dict[str, Any] = {
            "model": model,
            "messages": [message.model_dump() for message in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.response_schema is not None:
            payload["response_format"] = {"type": "json_object"}
        started = time.perf_counter()
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"{self.name} 请求失败：{exc}") from exc
        data = response.json()
        content = str(data["choices"][0]["message"]["content"])
        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            model=model,
            provider=self.name,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            latency_ms=int((time.perf_counter() - started) * 1000),
            request_id=response.headers.get("x-request-id") or uuid4().hex,
        )


class GeminiProvider:
    """Gemini 原生 REST Provider。"""

    name = "gemini"

    def __init__(self, api_key: str | None, base_url: str | None = None) -> None:
        self.api_key = api_key
        self.base_url = (base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(available=bool(self.api_key), detail=self.base_url)

    async def generate(self, request: LLMRequest, model: str) -> LLMResponse:
        if not self.api_key:
            raise LLMConfigurationError("Gemini 未配置 API Key")
        payload = {
            "contents": [
                {"role": item.role if item.role != "assistant" else "model", "parts": [{"text": item.content}]}
                for item in request.messages
            ],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/models/{model}:generateContent",
                    params={"key": self.api_key},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"Gemini 请求失败：{exc}") from exc
        data = response.json()
        content = str(data["candidates"][0]["content"]["parts"][0]["text"])
        usage = data.get("usageMetadata", {})
        return LLMResponse(
            content=content,
            model=model,
            provider=self.name,
            prompt_tokens=int(usage.get("promptTokenCount", 0)),
            completion_tokens=int(usage.get("candidatesTokenCount", 0)),
            latency_ms=int((time.perf_counter() - started) * 1000),
            request_id=uuid4().hex,
        )
