"""手动 JD 到申请审批的端到端测试。"""

from sqlalchemy.orm import Session

from jobos.core.enums import AutomationLevel
from jobos.domain.schemas import CandidateFactInput, CandidateProfileInput
from jobos.memory.local_store import LocalMemoryStore
from jobos.memory.retrieval import build_evidence_pack
from jobos.rules.engine import RuleEngine
from jobos.services.application_service import ApplicationService
from jobos.services.job_service import JobService
from jobos.services.profile_service import ProfileService
from jobos.services.resume_service import ResumeService
from jobos.services.scoring_service import ScoringService


async def test_manual_jd_to_approval_flow(session: Session) -> None:
    profiles = ProfileService(session)
    profile = profiles.upsert_profile(
        CandidateProfileInput(name="测试用户", summary="Python 与 Vue 开发工程师")
    )
    profiles.add_fact(
        profile.id,
        CandidateFactInput(
            fact_type="skill",
            statement="熟悉 Python、FastAPI、Vue 3 和 TypeScript",
            metadata={"skills": ["Python", "FastAPI", "Vue 3", "TypeScript"]},
        ),
    )
    profiles.add_fact(
        profile.id,
        CandidateFactInput(
            fact_type="project",
            statement="使用 Python 和 FastAPI 交付远程项目",
            metadata={"company": "个人项目", "role": "开发者", "period": "2025"},
        ),
    )
    job, _ = JobService(session).import_text(
        "Python/Vue 远程兼职",
        "示例科技",
        "远程兼职，要求 Python、FastAPI、Vue 3 和 TypeScript",
    )
    evidence = build_evidence_pack(
        LocalMemoryStore(session), profile.id, job.id, job.description_normalized, list(job.requirements_json)
    )
    rules = RuleEngine(
        {
            "job_policy": {
                "accepted_employment_types": ["part_time"],
                "accepted_work_modes": ["remote"],
                "score_thresholds": {"reject_below": 55, "review_below": 72, "auto_contact_above": 82},
            },
            "automation": {},
        }
    )
    score = await ScoringService(session, rules).score(job, profile.id, evidence)
    resume = ResumeService(session).generate(profile, job, evidence)
    application = ApplicationService(session).create(
        job.id, profile.id, None, AutomationLevel.L1
    )
    approval = ApplicationService(session).prepare_materials(
        application.id, resume.id, f"您好，我与职位的匹配分为 {score.total_score}。"
    )
    assert score.evidence_ids_json
    assert resume.validation_status == "valid"
    assert approval is not None
    assert application.status == "awaiting_approval"
