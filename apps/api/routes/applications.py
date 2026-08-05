"""申请和审批 API。"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.dependencies import (
    get_provider_registry,
    get_session,
    require_local_request,
)
from jobos.core.enums import AutomationLevel
from jobos.core.errors import JobOSError, NotFoundError
from jobos.infrastructure.db.models import (
    ApplicationORM,
    ApprovalRequestORM,
    JobORM,
    PlatformAccountORM,
)
from jobos.providers.registry import ProviderRegistry
from jobos.services.application_service import ApplicationService, application_to_dict

router = APIRouter(
    prefix="/api/v1/applications",
    tags=["applications"],
    dependencies=[Depends(require_local_request)],
)


class CreateApplicationRequest(BaseModel):
    """创建申请请求。"""

    job_id: str
    profile_id: str
    platform_account_id: str | None = None
    automation_level: AutomationLevel = AutomationLevel.L1


class PrepareRequest(BaseModel):
    """准备申请材料请求。"""

    resume_version_id: str
    intro_message: str
    high_risk: bool = False


class ApprovalResolveRequest(BaseModel):
    """审批处理请求。"""

    approved: bool
    note: str = ""


class SubmitRequest(BaseModel):
    """平台提交请求。"""

    dry_run: bool = True


@router.get("")
def list_applications(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    """列出申请。"""
    items = session.scalars(select(ApplicationORM).order_by(ApplicationORM.created_at.desc())).all()
    return [application_to_dict(item) for item in items]


@router.post("")
def create_application(
    payload: CreateApplicationRequest, session: Session = Depends(get_session)
) -> dict[str, Any]:
    """创建申请。"""
    application = ApplicationService(session).create(
        payload.job_id, payload.profile_id, payload.platform_account_id, payload.automation_level
    )
    return application_to_dict(application)


@router.get("/{application_id}")
def get_application(application_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    """获取申请。"""
    application = session.get(ApplicationORM, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="申请不存在")
    return application_to_dict(application)


@router.post("/{application_id}/generate-materials")
def prepare_application(
    application_id: str, payload: PrepareRequest, session: Session = Depends(get_session)
) -> dict[str, Any]:
    """关联简历和开场语。"""
    approval = ApplicationService(session).prepare_materials(
        application_id, payload.resume_version_id, payload.intro_message, payload.high_risk
    )
    return {"approval_id": approval.id if approval else None}


@router.post("/{application_id}/approve")
def approve_application(
    application_id: str, payload: ApprovalResolveRequest, session: Session = Depends(get_session)
) -> dict[str, Any]:
    """处理申请对应的待审批请求。"""
    approval_id = session.scalar(
        select(ApprovalRequestORM.id).where(
            ApprovalRequestORM.entity_type == "application",
            ApprovalRequestORM.entity_id == application_id,
            ApprovalRequestORM.status == "pending",
        )
    )
    if approval_id is None:
        raise HTTPException(status_code=404, detail="没有待处理审批")
    approval = ApplicationService(session).resolve_approval(
        approval_id, payload.approved, note=payload.note
    )
    return {"approval_id": approval.id, "status": approval.status}


@router.post("/{application_id}/submit")
async def submit_application(
    application_id: str,
    payload: SubmitRequest,
    session: Session = Depends(get_session),
    registry: ProviderRegistry = Depends(get_provider_registry),
) -> dict[str, Any]:
    """执行平台沟通；默认 Dry Run。"""
    application = session.get(ApplicationORM, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="申请不存在")
    job = session.get(JobORM, application.job_id)
    account = (
        session.get(PlatformAccountORM, application.platform_account_id)
        if application.platform_account_id
        else None
    )
    if job is None or account is None:
        raise HTTPException(status_code=409, detail="申请缺少职位或平台账号")
    try:
        result = await ApplicationService(session).submit(
            application_id, registry.get(account.provider), account, job, dry_run=payload.dry_run
        )
    except (JobOSError, NotFoundError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result.model_dump()


@router.post("/{application_id}/withdraw")
def withdraw_application(
    application_id: str, session: Session = Depends(get_session)
) -> dict[str, Any]:
    """撤回申请。"""
    return application_to_dict(ApplicationService(session).withdraw(application_id))
