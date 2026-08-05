"""分析 API。"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.dependencies import get_session, require_local_request
from jobos.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"], dependencies=[Depends(require_local_request)])


@router.get("/summary")
def summary(session: Session = Depends(get_session)) -> dict[str, Any]:
    """返回求职漏斗摘要。"""
    return AnalyticsService(session).summary().to_dict()


@router.get("/resumes")
def resume_performance(session: Session = Depends(get_session)) -> list[dict[str, object]]:
    """按简历版本返回观测数据。"""
    return AnalyticsService(session).resume_performance()
