"""LLM 网关公共接口。"""

from jobos.llm.gateway import LLMGateway
from jobos.llm.schemas import LLMRequest, LLMResponse

__all__ = ["LLMGateway", "LLMRequest", "LLMResponse"]
