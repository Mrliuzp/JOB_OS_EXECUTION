"""任务、审计和系统状态 API。"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.dependencies import (
    get_session,
    get_session_factory,
    get_settings,
    require_local_request,
)
from jobos.core.errors import NotFoundError
from jobos.infrastructure.db.models import (
    ApprovalRequestORM,
    AuditEventORM,
    MessageORM,
    WorkflowTaskORM,
)
from jobos.services.application_service import ApplicationService
from jobos.workflow.task_queue import TaskQueue
from jobos.workflow.worker_status import read_worker_status, worker_heartbeat_path

router = APIRouter(
    prefix="/api/v1", tags=["workflow"], dependencies=[Depends(require_local_request)]
)


@router.get("/tasks")
def list_tasks(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    """列出任务。"""
    items = session.scalars(
        select(WorkflowTaskORM).order_by(WorkflowTaskORM.created_at.desc())
    ).all()
    return [_orm_dict(item) for item in items]


@router.post("/tasks/{task_id}/retry")
def retry_task(task_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    """人工重试失败任务。"""
    task = session.get(WorkflowTaskORM, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.status = "pending"
    task.last_error = None
    task.lease_owner = None
    task.lease_expires_at = None
    session.flush()
    return _orm_dict(task)


@router.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: str) -> dict[str, bool]:
    """取消任务。"""
    try:
        TaskQueue(get_session_factory()).cancel(task_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"cancelled": True}


@router.get("/audit-events")
def list_audit_events(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    """列出审计事件。"""
    items = session.scalars(select(AuditEventORM).order_by(AuditEventORM.created_at.desc())).all()
    return [_orm_dict(item) for item in items]


@router.get("/approvals")
def list_approvals(
    status: str = "pending", session: Session = Depends(get_session)
) -> list[dict[str, Any]]:
    """列出审批请求。"""
    items = session.scalars(
        select(ApprovalRequestORM).where(ApprovalRequestORM.status == status)
    ).all()
    return [_orm_dict(item) for item in items]


@router.post("/approvals/{approval_id}/approve")
def approve(approval_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    """批准申请或消息审批。"""
    approval = session.get(ApprovalRequestORM, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="审批不存在")
    if approval.entity_type == "application":
        ApplicationService(session).resolve_approval(approval_id, True)
    elif approval.entity_type == "message":
        message = session.get(MessageORM, approval.entity_id)
        if message is None:
            raise HTTPException(status_code=404, detail="审批关联消息不存在")
        message.reply_status = "approved"
        approval.status = "approved"
    else:
        approval.status = "approved"
    session.flush()
    return _orm_dict(approval)


@router.post("/approvals/{approval_id}/reject")
def reject(approval_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    """拒绝审批。"""
    approval = session.get(ApprovalRequestORM, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="审批不存在")
    if approval.entity_type == "application":
        ApplicationService(session).resolve_approval(approval_id, False)
    else:
        approval.status = "rejected"
        if approval.entity_type == "message":
            message = session.get(MessageORM, approval.entity_id)
            if message is not None:
                message.reply_status = "manual_required"
    session.flush()
    return _orm_dict(approval)


@router.get("/system/health")
def system_health(session: Session = Depends(get_session)) -> dict[str, str]:
    """检查 API、数据库和 Worker 心跳状态。"""
    session.execute(select(1))
    settings = get_settings()
    status = read_worker_status(
        worker_heartbeat_path(settings.resolved_data_dir()),
        float(settings.worker.heartbeat_seconds * 3),
    )
    return {"status": "ok", "database": "ok", **status.health_payload()}


def _orm_dict(item: Any) -> dict[str, Any]:
    return {column.name: getattr(item, column.name) for column in item.__table__.columns}
