"""SQLAlchemy 领域持久化模型。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """生成 UTC 时间。"""
    return datetime.now(timezone.utc)


def new_id() -> str:
    """生成不带连字符的 UUID。"""
    return uuid4().hex


class Base(DeclarativeBase):
    """ORM 基类。"""


class TimestampMixin:
    """统一时间字段。"""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class CandidateProfileORM(TimestampMixin, Base):
    """候选人资料。"""

    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100))
    preferred_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai")
    summary: Mapped[str] = mapped_column(Text, default="")
    automation_level: Mapped[str] = mapped_column(String(8), default="L1")


class CandidateFactORM(TimestampMixin, Base):
    """可追溯的候选人事实。"""

    __tablename__ = "candidate_facts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    fact_type: Mapped[str] = mapped_column(String(40), index=True)
    statement: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(40), default="manual")
    source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    allowed_for_resume: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_for_chat: Mapped[bool] = mapped_column(Boolean, default=True)
    sensitivity: Mapped[str] = mapped_column(String(20), default="normal", index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ResumeVersionORM(Base):
    """简历版本。"""

    __tablename__ = "resume_versions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[str | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    version_type: Mapped[str] = mapped_column(String(20), default="tailored")
    language: Mapped[str] = mapped_column(String(16), default="zh-CN")
    title: Mapped[str] = mapped_column(String(255))
    content_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    rendered_text_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    rendered_pdf_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    validation_status: Mapped[str] = mapped_column(String(30), default="pending")
    validation_report_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PlatformAccountORM(TimestampMixin, Base):
    """招聘平台账号；不保存明文密码。"""

    __tablename__ = "platform_accounts"
    __table_args__ = (UniqueConstraint("provider", "display_name", name="uq_platform_account"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    browser_profile_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="unknown")
    last_login_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rate_limit_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    settings_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class JobORM(Base):
    """标准化职位。"""

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("provider", "external_job_id", name="uq_job_provider_external"),
        UniqueConstraint("provider", "canonical_url", name="uq_job_provider_url"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    external_job_id: Mapped[str] = mapped_column(String(255))
    canonical_url: Mapped[str] = mapped_column(String(2000))
    title: Mapped[str] = mapped_column(String(255), index=True)
    company_name: Mapped[str] = mapped_column(String(255), index=True)
    company_external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    work_mode: Mapped[str] = mapped_column(String(20), default="unknown")
    employment_type: Mapped[str] = mapped_column(String(30), default="unknown")
    salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_period: Mapped[str | None] = mapped_column(String(20), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    description_raw: Mapped[str] = mapped_column(Text, default="")
    description_normalized: Mapped[str] = mapped_column(Text, default="")
    requirements_json: Mapped[list[Any]] = mapped_column(JSON, default=list)
    benefits_json: Mapped[list[Any]] = mapped_column(JSON, default=list)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    status: Mapped[str] = mapped_column(String(30), default="discovered", index=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class JobScoreORM(Base):
    """职位评分结果。"""

    __tablename__ = "job_scores"
    __table_args__ = (UniqueConstraint("job_id", "profile_id", name="uq_job_score"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    total_score: Mapped[float] = mapped_column(Float)
    technical_score: Mapped[float] = mapped_column(Float, default=0)
    experience_score: Mapped[float] = mapped_column(Float, default=0)
    availability_score: Mapped[float] = mapped_column(Float, default=0)
    compensation_score: Mapped[float] = mapped_column(Float, default=0)
    remote_score: Mapped[float] = mapped_column(Float, default=0)
    risk_score: Mapped[float] = mapped_column(Float, default=0)
    matched_skills_json: Mapped[list[Any]] = mapped_column(JSON, default=list)
    missing_skills_json: Mapped[list[Any]] = mapped_column(JSON, default=list)
    reasons_json: Mapped[list[Any]] = mapped_column(JSON, default=list)
    evidence_ids_json: Mapped[list[Any]] = mapped_column(JSON, default=list)
    decision: Mapped[str] = mapped_column(String(20))
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ApplicationORM(TimestampMixin, Base):
    """职位申请。"""

    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("profile_id", "job_id", name="uq_application_profile_job"),
        UniqueConstraint("idempotency_key", name="uq_application_idempotency"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    platform_account_id: Mapped[str | None] = mapped_column(
        ForeignKey("platform_accounts.id", ondelete="SET NULL"), nullable=True
    )
    resume_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), default="planned", index=True)
    autonomy_level: Mapped[str] = mapped_column(String(8), default="L1")
    intro_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    failure_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_application_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), index=True)


class ConversationORM(TimestampMixin, Base):
    """平台会话。"""

    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("provider", "external_conversation_id", name="uq_conversation_external"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    external_conversation_id: Mapped[str] = mapped_column(String(255))
    job_id: Mapped[str | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    application_id: Mapped[str | None] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"), nullable=True
    )
    recruiter_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recruiter_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unread_count: Mapped[int] = mapped_column(Integer, default=0)


class MessageORM(Base):
    """会话消息。"""

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "external_message_id", name="uq_message_external"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    external_message_id: Mapped[str] = mapped_column(String(255))
    direction: Mapped[str] = mapped_column(String(20))
    sender_type: Mapped[str] = mapped_column(String(30))
    content: Mapped[str] = mapped_column(Text)
    message_type: Mapped[str] = mapped_column(String(40), default="unknown")
    risk_level: Mapped[str] = mapped_column(String(20), default="medium")
    reply_status: Mapped[str] = mapped_column(String(30), default="received")
    generated_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ApprovalRequestORM(Base):
    """人工审批请求。"""

    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[str] = mapped_column(String(32), index=True)
    approval_type: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class WorkflowTaskORM(TimestampMixin, Base):
    """可租约领取的工作流任务。"""

    __tablename__ = "workflow_tasks"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_task_idempotency"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    task_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    lease_owner: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), index=True)


class AuditEventORM(Base):
    """不可由普通业务更新的审计事件。"""

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    actor_type: Mapped[str] = mapped_column(String(40))
    actor_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[str] = mapped_column(String(32), index=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
