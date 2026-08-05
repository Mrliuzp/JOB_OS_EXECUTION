"""职位申请、审批和提交服务。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobos.core.enums import ApplicationStatus, AutomationLevel
from jobos.core.errors import ApprovalRequiredError, ConflictError, NotFoundError
from jobos.core.idempotency import build_idempotency_key
from jobos.domain.schemas import ContactRequest, ExternalJobRef, ProviderActionResult
from jobos.infrastructure.db.models import (
    ApplicationORM,
    ApprovalRequestORM,
    JobORM,
    PlatformAccountORM,
)
from jobos.providers.base import ProviderAdapter
from jobos.workflow.state_machine import transition_application


class ApplicationService:
    """执行材料准备、人工审批和受控平台动作。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        job_id: str,
        profile_id: str,
        platform_account_id: str | None,
        automation_level: AutomationLevel,
    ) -> ApplicationORM:
        """按候选人和职位幂等创建申请。"""
        existing = self.session.scalar(
            select(ApplicationORM).where(
                ApplicationORM.job_id == job_id, ApplicationORM.profile_id == profile_id
            )
        )
        if existing is not None:
            return existing
        key = build_idempotency_key(
            "application", {"job_id": job_id, "profile_id": profile_id}
        )
        application = ApplicationORM(
            job_id=job_id,
            profile_id=profile_id,
            platform_account_id=platform_account_id,
            autonomy_level=automation_level.value,
            idempotency_key=key,
        )
        self.session.add(application)
        self.session.flush()
        return application

    def prepare_materials(
        self, application_id: str, resume_version_id: str, intro_message: str, high_risk: bool = False
    ) -> ApprovalRequestORM | None:
        """关联材料，并按自动化等级创建审批。"""
        application = self._get(application_id)
        application.resume_version_id = resume_version_id
        application.intro_message = intro_message
        application.status = transition_application(
            application.status, ApplicationStatus.MATERIALS_READY.value
        ).value
        level = AutomationLevel(application.autonomy_level)
        requires_approval = level in {AutomationLevel.L0, AutomationLevel.L1, AutomationLevel.L2} or high_risk
        if not requires_approval:
            application.status = transition_application(
                application.status, ApplicationStatus.APPROVED.value
            ).value
            self.session.flush()
            return None
        application.status = transition_application(
            application.status, ApplicationStatus.AWAITING_APPROVAL.value
        ).value
        approval = ApprovalRequestORM(
            entity_type="application",
            entity_id=application.id,
            approval_type="application_submit",
            reason="投递前人工审批" if not high_risk else "命中高风险规则，必须人工审批",
            payload_json={
                "resume_version_id": resume_version_id,
                "intro_message": intro_message,
                "high_risk": high_risk,
            },
        )
        self.session.add(approval)
        self.session.flush()
        return approval

    def resolve_approval(
        self, approval_id: str, approved: bool, resolved_by: str = "local-user", note: str = ""
    ) -> ApprovalRequestORM:
        """批准或拒绝申请。"""
        approval = self.session.get(ApprovalRequestORM, approval_id)
        if approval is None:
            raise NotFoundError(f"审批不存在：{approval_id}")
        if approval.status != "pending":
            raise ConflictError("审批已经处理")
        approval.status = "approved" if approved else "rejected"
        approval.resolved_at = datetime.now(timezone.utc)
        approval.resolved_by = resolved_by
        approval.resolution_note = note
        if approval.entity_type == "application":
            application = self._get(approval.entity_id)
            if approved:
                application.status = transition_application(
                    application.status, ApplicationStatus.APPROVED.value
                ).value
            else:
                application.status = ApplicationStatus.WITHDRAWN.value
        self.session.flush()
        return approval

    async def submit(
        self,
        application_id: str,
        provider: ProviderAdapter,
        account: PlatformAccountORM,
        job: JobORM,
        *,
        dry_run: bool = True,
    ) -> ProviderActionResult:
        """在审批和幂等检查后发起沟通。"""
        application = self._get(application_id)
        if application.status != ApplicationStatus.APPROVED.value:
            raise ApprovalRequiredError("申请未获批准，禁止执行平台动作")
        if not application.intro_message:
            raise ConflictError("申请缺少开场语")
        action_key = build_idempotency_key(
            "contact", {"application_id": application.id, "job_id": job.id}
        )
        result = await provider.initiate_contact(
            account,
            ContactRequest(
                job=ExternalJobRef(
                    external_job_id=job.external_job_id, canonical_url=job.canonical_url
                ),
                message=application.intro_message,
                idempotency_key=action_key,
                dry_run=dry_run,
            ),
        )
        if result.success and not result.dry_run:
            application.status = transition_application(
                application.status, ApplicationStatus.COMMUNICATING.value
            ).value
            application.last_action_at = datetime.now(timezone.utc)
        self.session.flush()
        return result

    def mark_submitted(self, application_id: str, external_id: str | None = None) -> ApplicationORM:
        """手动确认平台已完成申请。"""
        application = self._get(application_id)
        application.status = transition_application(
            application.status, ApplicationStatus.SUBMITTED.value
        ).value
        application.external_application_id = external_id
        application.submitted_at = datetime.now(timezone.utc)
        self.session.flush()
        return application

    def withdraw(self, application_id: str) -> ApplicationORM:
        """撤回申请。"""
        application = self._get(application_id)
        if application.status in {
            ApplicationStatus.REJECTED.value,
            ApplicationStatus.ACCEPTED.value,
            ApplicationStatus.EXPIRED.value,
        }:
            raise ConflictError("终止状态的申请不能撤回")
        application.status = ApplicationStatus.WITHDRAWN.value
        self.session.flush()
        return application

    def _get(self, application_id: str) -> ApplicationORM:
        application = self.session.get(ApplicationORM, application_id)
        if application is None:
            raise NotFoundError(f"申请不存在：{application_id}")
        return application


def application_to_dict(application: ApplicationORM) -> dict[str, Any]:
    """序列化申请。"""
    return {column.name: getattr(application, column.name) for column in application.__table__.columns}
