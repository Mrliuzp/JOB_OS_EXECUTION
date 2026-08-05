"""LLM 请求和响应模型。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """对话消息。"""

    role: str
    content: str


class LLMRequest(BaseModel):
    """统一模型请求。"""

    task_type: str
    messages: list[ChatMessage]
    response_schema: dict[str, Any] | None = None
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=1)
    timeout_seconds: int = Field(default=60, ge=1)
    trace_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """统一模型响应。"""

    content: str
    parsed: dict[str, Any] | list[Any] | None = None
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    request_id: str | None = None


class ProviderHealth(BaseModel):
    """模型 Provider 健康状态。"""

    available: bool
    detail: str = ""
