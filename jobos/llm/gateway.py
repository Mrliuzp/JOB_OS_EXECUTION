"""支持结构化输出、重试与备用 Provider 的 LLM 网关。"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Sequence
from typing import Any

from jsonschema import ValidationError as JSONSchemaValidationError
from jsonschema import validate as validate_json

from jobos.core.errors import LLMConfigurationError, LLMError, LLMResponseValidationError
from jobos.llm.base import LLMProvider
from jobos.llm.schemas import LLMRequest, LLMResponse

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


class LLMGateway:
    """按任务配置选择模型，并在失败时切换备用 Provider。"""

    def __init__(self, providers: dict[str, LLMProvider]) -> None:
        self.providers = providers
        self.usage: list[LLMResponse] = []

    async def generate(
        self,
        request: LLMRequest,
        provider_names: Sequence[str],
        model: str,
        retries: int = 1,
    ) -> LLMResponse:
        """执行模型请求并验证 JSON Schema。"""
        if not provider_names:
            raise LLMConfigurationError("没有为当前任务配置模型 Provider")
        errors: list[str] = []
        for provider_name in provider_names:
            provider = self.providers.get(provider_name)
            if provider is None:
                errors.append(f"未注册 Provider：{provider_name}")
                continue
            for attempt in range(retries + 1):
                try:
                    response = await provider.generate(request, model)
                    response.parsed = self._parse_and_validate(
                        response.content, request.response_schema
                    )
                    self.usage.append(response)
                    return response
                except (LLMError, LLMResponseValidationError) as exc:
                    errors.append(f"{provider_name} 第 {attempt + 1} 次失败：{exc}")
                    if attempt < retries:
                        await asyncio.sleep(0)
        raise LLMError("；".join(errors))

    @staticmethod
    def _parse_and_validate(
        content: str, schema: dict[str, Any] | None
    ) -> dict[str, Any] | list[Any] | None:
        if schema is None:
            return None
        candidate = content.strip()
        block = _JSON_BLOCK.search(candidate)
        if block:
            candidate = block.group(1).strip()
        else:
            start_positions = [pos for pos in (candidate.find("{"), candidate.find("[")) if pos >= 0]
            if start_positions:
                candidate = candidate[min(start_positions) :]
        try:
            parsed = json.loads(candidate)
            validate_json(instance=parsed, schema=schema)
        except (json.JSONDecodeError, JSONSchemaValidationError) as exc:
            raise LLMResponseValidationError(f"结构化输出无效：{exc}") from exc
        if not isinstance(parsed, (dict, list)):
            raise LLMResponseValidationError("结构化输出必须是对象或数组")
        return parsed
