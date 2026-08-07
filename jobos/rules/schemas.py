"""规则引擎模型。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class RuleContext(BaseModel):
    """规则计算上下文。"""

    title: str
    company_name: str
    description: str
    employment_type: str = "unknown"
    work_mode: str = "unknown"
    ai_score: float | None = None
    message_type: str | None = None
    risk_level: str | None = None
    daily_contact_count: int = 0
    daily_application_count: int = 0
    extra: dict[str, Any] = Field(default_factory=dict)


class RuleDecision(BaseModel):
    """可审计的规则决策。"""

    action: Literal["reject", "review", "allow", "auto_contact", "manual_required"]
    matched_rule_ids: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    hard_reject: bool = False
