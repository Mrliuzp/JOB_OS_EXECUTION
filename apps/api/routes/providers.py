"""Provider 和平台账号 API。"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.dependencies import (
    get_browser_session_manager,
    get_provider_registry,
    get_session,
    require_local_request,
)
from jobos.core.errors import ConfigurationError, JobOSError
from jobos.infrastructure.db.models import PlatformAccountORM
from jobos.providers.registry import ProviderRegistry

router = APIRouter(
    prefix="/api/v1/providers", tags=["providers"], dependencies=[Depends(require_local_request)]
)


class CreateAccountRequest(BaseModel):
    """平台账号创建请求。"""

    provider: str
    display_name: str
    browser_profile_id: str | None = None


@router.get("")
def list_providers(
    registry: ProviderRegistry = Depends(get_provider_registry),
) -> list[dict[str, Any]]:
    """列出 Provider 及能力。"""
    return [
        {"name": item.name, "capabilities": item.capabilities.__dict__} for item in registry.list()
    ]


@router.get("/accounts")
def list_accounts(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    """列出平台账号。"""
    return [_orm_dict(item) for item in session.scalars(select(PlatformAccountORM)).all()]


@router.post("/accounts")
def add_account(
    payload: CreateAccountRequest,
    session: Session = Depends(get_session),
    registry: ProviderRegistry = Depends(get_provider_registry),
) -> dict[str, Any]:
    """创建平台账号记录，不接收密码。"""
    registry.get(payload.provider)
    account = PlatformAccountORM(
        provider=payload.provider,
        display_name=payload.display_name,
        browser_profile_id=payload.browser_profile_id,
        status="unknown",
    )
    session.add(account)
    session.flush()
    return _orm_dict(account)


@router.post("/accounts/{account_id}/login-window")
def login_window(
    account_id: str,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """启动独立 Chrome 窗口，由用户手动登录。"""
    account = session.get(PlatformAccountORM, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="平台账号不存在")
    try:
        manager = get_browser_session_manager()
        browser_session = manager.acquire(
            account.id, account.provider, account.display_name, "manual_login"
        )
    except (ConfigurationError, JobOSError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    account.browser_profile_id = browser_session.browser_profile_path.name
    account.status = "login_window_open"
    session.flush()
    return {
        "session_id": browser_session.session_id,
        "cdp_port": browser_session.cdp_port,
        "profile_path": str(browser_session.browser_profile_path),
        "instruction": "请在打开的 Chrome 窗口中手动完成登录和验证码。",
    }


@router.post("/accounts/{account_id}/close-login-window")
def close_login_window(
    account_id: str,
    session_id: str,
    session: Session = Depends(get_session),
) -> dict[str, bool]:
    """关闭手动登录窗口并释放 Profile 锁。"""
    account = session.get(PlatformAccountORM, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="平台账号不存在")
    get_browser_session_manager().release(session_id)
    account.status = "unknown"
    session.flush()
    return {"closed": True}


@router.post("/accounts/{account_id}/check-login")
async def check_login(
    account_id: str,
    session: Session = Depends(get_session),
    registry: ProviderRegistry = Depends(get_provider_registry),
) -> dict[str, Any]:
    """检查登录状态；不会自动输入账号密码。"""
    account = session.get(PlatformAccountORM, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="平台账号不存在")
    try:
        result = await registry.get(account.provider).check_login(account)
    except JobOSError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    account.status = "logged_in" if result.logged_in else "login_required"
    session.flush()
    return result.model_dump()


def _orm_dict(item: Any) -> dict[str, Any]:
    return {column.name: getattr(item, column.name) for column in item.__table__.columns}
