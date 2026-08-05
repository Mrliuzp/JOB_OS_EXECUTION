"""职位评分与简历 API。"""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.dependencies import get_session, get_settings, require_local_request
from jobos.artifacts.renderer import ResumeRenderer
from jobos.core.config import JobOSSettings
from jobos.infrastructure.db.models import (
    CandidateProfileORM,
    JobORM,
    ResumeVersionORM,
)
from jobos.memory.local_store import LocalMemoryStore
from jobos.memory.retrieval import build_evidence_pack
from jobos.rules.engine import RuleEngine
from jobos.services.resume_service import ResumeService
from jobos.services.scoring_service import ScoringService

router = APIRouter(prefix="/api/v1", tags=["resumes"], dependencies=[Depends(require_local_request)])


@router.post("/jobs/{job_id}/score")
async def score_job(
    job_id: str,
    session: Session = Depends(get_session),
    settings: JobOSSettings = Depends(get_settings),
) -> dict[str, Any]:
    """使用硬规则和事实证据评分。"""
    job = session.get(JobORM, job_id)
    profile = session.scalar(select(CandidateProfileORM).limit(1))
    if job is None or profile is None:
        raise HTTPException(status_code=404, detail="职位或候选人资料不存在")
    evidence = build_evidence_pack(
        LocalMemoryStore(session),
        profile.id,
        job.id,
        job.description_normalized,
        [str(item) for item in job.requirements_json],
    )
    score = await ScoringService(
        session, RuleEngine(settings.policies.model_dump())
    ).score(job, profile.id, evidence)
    return _orm_dict(score)


@router.post("/jobs/{job_id}/generate-resume")
def generate_resume(
    job_id: str, session: Session = Depends(get_session)
) -> dict[str, Any]:
    """生成并校验职位定制简历。"""
    job = session.get(JobORM, job_id)
    profile = session.scalar(select(CandidateProfileORM).limit(1))
    if job is None or profile is None:
        raise HTTPException(status_code=404, detail="职位或候选人资料不存在")
    evidence = build_evidence_pack(
        LocalMemoryStore(session),
        profile.id,
        job.id,
        job.description_normalized,
        [str(item) for item in job.requirements_json],
    )
    version = ResumeService(session).generate(profile, job, evidence)
    return _orm_dict(version)


@router.get("/resumes")
def list_resumes(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    """列出简历版本。"""
    return [
        _orm_dict(item)
        for item in session.scalars(
            select(ResumeVersionORM).order_by(ResumeVersionORM.created_at.desc())
        ).all()
    ]


@router.post("/resumes/{resume_id}/render")
async def render_resume(
    resume_id: str,
    session: Session = Depends(get_session),
    settings: JobOSSettings = Depends(get_settings),
) -> dict[str, str]:
    """渲染 HTML 和 PDF。"""
    version = session.get(ResumeVersionORM, resume_id)
    if version is None:
        raise HTTPException(status_code=404, detail="简历不存在")
    profile = session.get(CandidateProfileORM, version.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="候选人资料不存在")
    output = settings.resolved_data_dir() / "artifacts" / "resumes" / version.id
    renderer = ResumeRenderer(
        Path(__file__).parents[3] / "jobos/artifacts/resume_templates", output
    )
    html = renderer.render_html(
        version.content_json,
        {
            "name": profile.name,
            "email": profile.email,
            "phone": profile.phone,
            "city": profile.city,
        },
    )
    pdf = await renderer.render_pdf(html)
    version.rendered_text_path = str(html)
    version.rendered_pdf_path = str(pdf)
    session.flush()
    return {"html": str(html), "pdf": str(pdf)}


def _orm_dict(item: Any) -> dict[str, Any]:
    return {column.name: getattr(item, column.name) for column in item.__table__.columns}
