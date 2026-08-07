"""LLM 用量统计。"""

from dataclasses import dataclass

from jobos.llm.schemas import LLMResponse


@dataclass(frozen=True)
class UsageSummary:
    """模型调用用量摘要。"""

    requests: int
    prompt_tokens: int
    completion_tokens: int


def summarize_usage(responses: list[LLMResponse]) -> UsageSummary:
    """汇总模型调用次数和 Token。"""
    return UsageSummary(
        requests=len(responses),
        prompt_tokens=sum(item.prompt_tokens for item in responses),
        completion_tokens=sum(item.completion_tokens for item in responses),
    )
