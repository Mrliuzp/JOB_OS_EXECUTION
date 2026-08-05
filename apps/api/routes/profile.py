"""候选人资料 API。"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.dependencies import get_session, require_local_request
from jobos.core.errors import NotFoundError
from jobos.domain.schemas import CandidateFactInput, CandidateProfileInput
from jobos.services.profile_service import ProfileService, profile_to_dict

router = APIRouter(prefix="/api/v1/profile", tags=["profile"], dependencies=[Depends(require_local_request)])


@router.get("")
def get_profile(session: Session = Depends(get_session)) -> dict[str, Any]:
    """获取默认候选人资料。"""
    try:
        return profile_to_dict(ProfileService(session).get_profile())
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("")
def put_profile(
    payload: CandidateProfileInput, session: Session = Depends(get_session)
) -> dict[str, Any]:
    """创建或更新默认资料。"""
    return profile_to_dict(ProfileService(session).upsert_profile(payload))


@router.get("/facts")
def list_facts(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    """列出默认资料的事实。"""
    service = ProfileService(session)
    profile = service.get_profile()
    return [_fact_dict(item) for item in service.facts.list_for_profile(profile.id)]


@router.post("/facts")
def add_fact(
    payload: CandidateFactInput, session: Session = Depends(get_session)
) -> dict[str, Any]:
    """新增候选人事实。"""
    service = ProfileService(session)
    profile = service.get_profile()
    return _fact_dict(service.add_fact(profile.id, payload))


@router.put("/facts/{fact_id}")
def update_fact(
    fact_id: str, payload: CandidateFactInput, session: Session = Depends(get_session)
) -> dict[str, Any]:
    """更新事实。"""
    return _fact_dict(ProfileService(session).update_fact(fact_id, payload))


@router.delete("/facts/{fact_id}")
def delete_fact(fact_id: str, session: Session = Depends(get_session)) -> dict[str, bool]:
    """删除事实。"""
    ProfileService(session).delete_fact(fact_id)
    return {"deleted": True}


def _fact_dict(fact: Any) -> dict[str, Any]:
    return {column.name: getattr(fact, column.name) for column in fact.__table__.columns}
