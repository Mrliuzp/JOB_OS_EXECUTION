"""职位 API。"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.dependencies import get_session, require_local_request
from jobos.core.errors import NotFoundError
from jobos.infrastructure.repositories import JobRepository
from jobos.services.job_service import JobService

router = APIRouter(
    prefix="/api/v1/jobs", tags=["jobs"], dependencies=[Depends(require_local_request)]
)


class ImportTextRequest(BaseModel):
    """手动 JD 导入请求。"""

    title: str
    company_name: str
    description: str
    source_id: str | None = None


class ImportURLRequest(BaseModel):
    """职位 URL 导入请求。"""

    url: str
    title: str = "待补全职位"
    company_name: str = "待补全公司"
    description: str = "通过 URL 导入，等待 Provider 补全。"


@router.get("")
def list_jobs(
    status: str | None = None, session: Session = Depends(get_session)
) -> list[dict[str, Any]]:
    """查询职位列表。"""
    return [_job_dict(item) for item in JobRepository(session).list(status)]


@router.get("/{job_id}")
def get_job(job_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    """获取职位详情。"""
    try:
        return _job_dict(JobRepository(session).get(job_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/import-text")
def import_text(
    payload: ImportTextRequest, session: Session = Depends(get_session)
) -> dict[str, Any]:
    """导入粘贴的职位描述。"""
    job, created = JobService(session).import_text(
        payload.title, payload.company_name, payload.description, payload.source_id
    )
    return {"created": created, "job": _job_dict(job)}


@router.post("/import-url")
def import_url(
    payload: ImportURLRequest, session: Session = Depends(get_session)
) -> dict[str, Any]:
    """安全导入 URL，不在 API 请求中自动抓取外站。"""
    job, created = JobService(session).import_text(
        payload.title, payload.company_name, payload.description, payload.url
    )
    job.provider = "generic_web"
    job.canonical_url = payload.url
    session.flush()
    return {"created": created, "job": _job_dict(job)}


@router.post("/{job_id}/archive")
def archive_job(job_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    """归档职位。"""
    job = JobRepository(session).get(job_id)
    job.status = "archived"
    session.flush()
    return _job_dict(job)


def _job_dict(job: Any) -> dict[str, Any]:
    return {column.name: getattr(job, column.name) for column in job.__table__.columns}
