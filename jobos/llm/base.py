"""LLM Provider 协议。"""

from typing import Protocol

from jobos.llm.schemas import LLMRequest, LLMResponse, ProviderHealth


class LLMProvider(Protocol):
    """模型 Provider 必须实现的接口。"""

    name: str

    async def generate(self, request: LLMRequest, model: str) -> LLMResponse: ...

    async def health_check(self) -> ProviderHealth: ...
