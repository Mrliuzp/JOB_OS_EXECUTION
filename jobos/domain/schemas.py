"""跨服务使用的 Pydantic 领域模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CandidateProfileInput(BaseModel):
    """候选人资料输入。"""

    name: str
    preferred_name: str | None = None
    email: str | None = None
    phone: str | None = None
    city: str | None = None
    timezone: str = "Asia/Shanghai"
    summary: str = ""
    automation_level: str = "L1"


class CandidateFactInput(BaseModel):
    """候选人事实输入。"""

    fact_type: str
    statement: str
    source_type: str = "manual"
    source_reference: str | None = None
    confidence: float = Field(default=1.0, ge=0, le=1)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    allowed_for_resume: bool = True
    allowed_for_chat: bool = True
    sensitivity: str = "normal"
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceFact(BaseModel):
    """可传给生成模型的事实证据。"""

    evidence_id: str
    statement: str
    fact_type: str
    confidence: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidencePack(BaseModel):
    """职位相关事实证据包。"""

    job_id: str
    facts: list[EvidenceFact] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)


class JobSearchQuery(BaseModel):
    """职位搜索条件。"""

    keywords: list[str] = Field(default_factory=list)
    employment_types: list[str] = Field(default_factory=list)
    work_modes: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    salary_min: float | None = None
    page_limit: int = Field(default=5, ge=1, le=20)


class ExternalJobRef(BaseModel):
    """平台职位引用。"""

    external_job_id: str
    canonical_url: str


class JobSearchItem(BaseModel):
    """职位列表项。"""

    external_job_id: str
    canonical_url: str
    title: str
    company_name: str
    location: str | None = None
    salary_text: str | None = None
    job_card_text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class JobSearchPage(BaseModel):
    """职位搜索分页。"""

    items: list[JobSearchItem]
    next_cursor: str | None = None


class RawJobDetail(BaseModel):
    """Provider 返回的原始职位详情。"""

    external_job_id: str
    canonical_url: str
    title: str
    company_name: str
    location: str | None = None
    description: str
    requirements: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    work_mode: str = "unknown"
    employment_type: str = "unknown"
    salary_min: float | None = None
    salary_max: float | None = None
    salary_period: str | None = None
    expired: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class LoginStatus(BaseModel):
    """平台登录状态。"""

    logged_in: bool
    account_name: str | None = None
    requires_manual_action: bool = False


class ContactRequest(BaseModel):
    """发起沟通请求。"""

    job: ExternalJobRef
    message: str
    resume_path: str | None = None
    idempotency_key: str
    dry_run: bool = True


class SubmitApplicationRequest(BaseModel):
    """提交申请请求。"""

    job: ExternalJobRef
    resume_path: str
    cover_message: str | None = None
    idempotency_key: str
    dry_run: bool = True


class SendMessageRequest(BaseModel):
    """发送站内消息请求。"""

    conversation_id: str
    message: str
    idempotency_key: str
    dry_run: bool = True


class ProviderActionResult(BaseModel):
    """Provider 动作结果。"""

    success: bool
    dry_run: bool
    external_id: str | None = None
    detail: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExternalConversation(BaseModel):
    """平台会话。"""

    external_conversation_id: str
    external_job_id: str | None = None
    recruiter_name: str | None = None
    recruiter_company: str | None = None
    unread_count: int = 0
    last_message_at: datetime | None = None


class ConversationPage(BaseModel):
    """会话分页。"""

    items: list[ExternalConversation]
    next_cursor: str | None = None


class ExternalMessage(BaseModel):
    """平台消息。"""

    external_message_id: str
    direction: Literal["inbound", "outbound"]
    sender_type: str
    content: str
    sent_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessagePage(BaseModel):
    """消息分页。"""

    items: list[ExternalMessage]
    next_cursor: str | None = None


class MessageClassification(BaseModel):
    """消息分类结果。"""

    message_type: str
    risk_level: str
    intent: str
    required_fact_types: list[str] = Field(default_factory=list)
    requires_human: bool
    confidence: float = Field(ge=0, le=1)


class ReplyDraft(BaseModel):
    """基于事实的回复草稿。"""

    reply: str
    evidence_ids: list[str]
    requires_human: bool
    risk_flags: list[str] = Field(default_factory=list)
