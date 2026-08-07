"""LLM 网关测试。"""

import pytest

from jobos.core.errors import LLMError, LLMResponseValidationError
from jobos.llm.gateway import LLMGateway
from jobos.llm.schemas import LLMRequest, LLMResponse, ProviderHealth


class FakeProvider:
    """可配置输出的测试 Provider。"""

    def __init__(self, name: str, content: str, fail: bool = False) -> None:
        self.name = name
        self.content = content
        self.fail = fail

    async def generate(self, request: LLMRequest, model: str) -> LLMResponse:
        del request
        if self.fail:
            raise LLMError("模拟失败")
        return LLMResponse(content=self.content, model=model, provider=self.name)

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(available=not self.fail)


@pytest.mark.asyncio
async def test_gateway_validates_schema_and_falls_back() -> None:
    gateway = LLMGateway(
        {
            "bad": FakeProvider("bad", "", fail=True),
            "good": FakeProvider("good", '{"score": 88}'),
        }
    )
    request = LLMRequest(
        task_type="test",
        trace_id="t1",
        messages=[],
        response_schema={
            "type": "object",
            "required": ["score"],
            "properties": {"score": {"type": "number"}},
        },
    )
    response = await gateway.generate(request, ["bad", "good"], "model", retries=0)
    assert response.provider == "good"
    assert response.parsed == {"score": 88}


def test_invalid_json_is_detected() -> None:
    with pytest.raises(LLMResponseValidationError):
        LLMGateway._parse_and_validate("不是 JSON", {"type": "object"})
