"""会话和消息 API。"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.dependencies import get_provider_registry, get_session, require_local_request
from jobos.core.config import load_settings
from jobos.core.errors import JobOSError
from jobos.infrastructure.db.models import (
    CandidateProfileORM,
    ConversationORM,
    MessageORM,
    PlatformAccountORM,
)
from jobos.memory.local_store import LocalMemoryStore
from jobos.providers.registry import ProviderRegistry
from jobos.rules.engine import RuleEngine
from jobos.services.communication_service import CommunicationService

router = APIRouter(
    prefix="/api/v1", tags=["conversations"], dependencies=[Depends(require_local_request)]
)


class SyncConversationRequest(BaseModel):
    """会话同步请求。"""

    account_id: str


class ApproveReplyRequest(BaseModel):
    """回复审批请求。"""

    edited_reply: str | None = None


class SendReplyRequest(BaseModel):
    """回复发送请求。"""

    account_id: str
    dry_run: bool = True


def _service(session: Session) -> CommunicationService:
    settings = load_settings()
    return CommunicationService(session, RuleEngine(settings.policies.model_dump()))


@router.get("/conversations")
def list_conversations(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    """列出会话。"""
    items = session.scalars(
        select(ConversationORM).order_by(ConversationORM.updated_at.desc())
    ).all()
    return [_orm_dict(item) for item in items]


@router.post("/conversations/sync")
async def sync_conversations(
    payload: SyncConversationRequest,
    session: Session = Depends(get_session),
    registry: ProviderRegistry = Depends(get_provider_registry),
) -> dict[str, int]:
    """同步指定平台账号的会话和消息。"""
    account = session.get(PlatformAccountORM, payload.account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="平台账号不存在")
    try:
        conversations_count, messages_count = await _service(session).sync(
            registry.get(account.provider), account
        )
    except JobOSError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"conversations": conversations_count, "messages": messages_count}


@router.get("/conversations/{conversation_id}/messages")
def list_messages(
    conversation_id: str, session: Session = Depends(get_session)
) -> list[dict[str, Any]]:
    """列出会话消息。"""
    items = session.scalars(
        select(MessageORM).where(MessageORM.conversation_id == conversation_id)
    ).all()
    return [_orm_dict(item) for item in items]


@router.post("/messages/{message_id}/generate-reply")
def generate_reply(message_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    """生成事实型回复。"""
    message = session.get(MessageORM, message_id)
    profile = session.scalar(select(CandidateProfileORM).limit(1))
    if message is None or profile is None:
        raise HTTPException(status_code=404, detail="消息或候选人资料不存在")
    draft, approval = _service(session).generate_reply(
        message, profile.id, LocalMemoryStore(session)
    )
    return {"draft": draft.model_dump(), "approval_id": approval.id if approval else None}


@router.post("/messages/{message_id}/approve-reply")
def approve_reply(
    message_id: str, payload: ApproveReplyRequest, session: Session = Depends(get_session)
) -> dict[str, Any]:
    """批准或编辑回复。"""
    return _orm_dict(_service(session).approve_reply(message_id, payload.edited_reply))


@router.post("/messages/{message_id}/send")
async def send_reply(
    message_id: str,
    payload: SendReplyRequest,
    session: Session = Depends(get_session),
    registry: ProviderRegistry = Depends(get_provider_registry),
) -> dict[str, str]:
    """发送最终回复。"""
    account = session.get(PlatformAccountORM, payload.account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="平台账号不存在")
    try:
        detail = await _service(session).send_reply(
            message_id, registry.get(account.provider), account, dry_run=payload.dry_run
        )
    except JobOSError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"detail": detail}


def _orm_dict(item: Any) -> dict[str, Any]:
    return {column.name: getattr(item, column.name) for column in item.__table__.columns}
