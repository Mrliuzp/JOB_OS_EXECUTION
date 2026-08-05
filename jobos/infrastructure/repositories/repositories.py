"""领域 Repository 实现。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobos.core.errors import NotFoundError
from jobos.infrastructure.db.models import (
    ApprovalRequestORM,
    AuditEventORM,
    CandidateFactORM,
    CandidateProfileORM,
    JobORM,
)


class ProfileRepository:
    """候选人资料 Repository。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, profile_id: str) -> CandidateProfileORM:
        profile = self.session.get(CandidateProfileORM, profile_id)
        if profile is None:
            raise NotFoundError(f"候选人资料不存在：{profile_id}")
        return profile

    def first(self) -> CandidateProfileORM | None:
        return self.session.scalar(
            select(CandidateProfileORM).order_by(CandidateProfileORM.created_at)
        )

    def save(self, profile: CandidateProfileORM) -> CandidateProfileORM:
        self.session.add(profile)
        self.session.flush()
        return profile


class FactRepository:
    """候选人事实 Repository。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_profile(self, profile_id: str) -> Sequence[CandidateFactORM]:
        stmt = select(CandidateFactORM).where(CandidateFactORM.profile_id == profile_id)
        return tuple(self.session.scalars(stmt).all())

    def get(self, fact_id: str) -> CandidateFactORM:
        fact = self.session.get(CandidateFactORM, fact_id)
        if fact is None:
            raise NotFoundError(f"候选人事实不存在：{fact_id}")
        return fact

    def save(self, fact: CandidateFactORM) -> CandidateFactORM:
        self.session.add(fact)
        self.session.flush()
        return fact


class JobRepository:
    """职位 Repository。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, job_id: str) -> JobORM:
        job = self.session.get(JobORM, job_id)
        if job is None:
            raise NotFoundError(f"职位不存在：{job_id}")
        return job

    def find_external(self, provider: str, external_job_id: str) -> JobORM | None:
        stmt = select(JobORM).where(
            JobORM.provider == provider, JobORM.external_job_id == external_job_id
        )
        return self.session.scalar(stmt)

    def find_url(self, provider: str, canonical_url: str) -> JobORM | None:
        stmt = select(JobORM).where(
            JobORM.provider == provider, JobORM.canonical_url == canonical_url
        )
        return self.session.scalar(stmt)

    def list(self, status: str | None = None) -> Sequence[JobORM]:
        stmt = select(JobORM).order_by(JobORM.discovered_at.desc())
        if status:
            stmt = stmt.where(JobORM.status == status)
        return tuple(self.session.scalars(stmt).all())

    def save(self, job: JobORM) -> JobORM:
        self.session.add(job)
        self.session.flush()
        return job


class ApprovalRepository:
    """审批 Repository。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def pending(self) -> Sequence[ApprovalRequestORM]:
        stmt = select(ApprovalRequestORM).where(ApprovalRequestORM.status == "pending")
        return tuple(self.session.scalars(stmt).all())

    def get(self, approval_id: str) -> ApprovalRequestORM:
        approval = self.session.get(ApprovalRequestORM, approval_id)
        if approval is None:
            raise NotFoundError(f"审批不存在：{approval_id}")
        return approval


class AuditRepository:
    """只追加审计日志。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def append(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        trace_id: str,
        payload: dict[str, Any],
        actor_type: str = "system",
        actor_id: str | None = None,
    ) -> AuditEventORM:
        event = AuditEventORM(
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            trace_id=trace_id,
            payload_json=payload,
        )
        self.session.add(event)
        self.session.flush()
        return event
