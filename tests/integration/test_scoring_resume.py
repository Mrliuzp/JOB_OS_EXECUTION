"""职位评分与简历生成测试。"""

from sqlalchemy.orm import Session

from jobos.core.errors import EvidenceValidationError, LLMConfigurationError
from jobos.domain.schemas import (
    CandidateFactInput,
    CandidateProfileInput,
    EvidencePack,
)
from jobos.memory.local_store import LocalMemoryStore
from jobos.memory.retrieval import build_evidence_pack
from jobos.rules.engine import RuleEngine
from jobos.services.job_service import JobService
from jobos.services.profile_service import ProfileService
from jobos.services.resume_service import (
    ResumeBullet,
    ResumeDocument,
    ResumeExperience,
    ResumeService,
    ResumeValidator,
)
from jobos.services.scoring_service import ScoringService

POLICIES = {
    "job_policy": {
        "accepted_employment_types": ["part_time", "contract", "freelance"],
        "accepted_work_modes": ["remote", "hybrid"],
        "rejected_keywords": ["刷单"],
        "score_thresholds": {"reject_below": 55, "review_below": 72, "auto_contact_above": 82},
    },
    "automation": {},
}


async def test_scoring_uses_evidence_ids_and_requires_model_when_requested(
    session: Session,
) -> None:
    profile_service = ProfileService(session)
    profile = profile_service.upsert_profile(
        CandidateProfileInput(name="李先生", summary="软件开发工程师")
    )
    fact = profile_service.add_fact(
        profile.id,
        CandidateFactInput(
            fact_type="skill",
            statement="熟悉 Python、FastAPI 和 SQL",
            metadata={"skills": ["Python", "FastAPI", "SQL"]},
        ),
    )
    profile_service.add_fact(
        profile.id,
        CandidateFactInput(fact_type="availability", statement="每周可投入 15 小时，支持远程兼职"),
    )
    job, _ = JobService(session).import_text(
        "Python 远程兼职开发", "示例科技", "远程兼职，要求 Python、FastAPI 和 SQL"
    )
    evidence = build_evidence_pack(
        LocalMemoryStore(session),
        profile.id,
        job.id,
        job.description_normalized,
        list(job.requirements_json),
    )
    score = await ScoringService(session, RuleEngine(POLICIES)).score(job, profile.id, evidence)
    assert fact.id in score.evidence_ids_json
    try:
        await ScoringService(session, RuleEngine(POLICIES)).score(
            job, profile.id, evidence, require_llm=True, provider_names=["openai"]
        )
    except LLMConfigurationError:
        pass
    else:
        raise AssertionError("缺少模型时必须明确失败")


def test_resume_validates_fabrication_and_allows_valid_document(session: Session) -> None:
    profile_service = ProfileService(session)
    profile = profile_service.upsert_profile(
        CandidateProfileInput(name="李先生", summary="真实摘要")
    )
    fact = profile_service.add_fact(
        profile.id,
        CandidateFactInput(
            fact_type="project",
            statement="在示例科技使用 Python 建设 API，性能提升 20%",
            metadata={
                "company": "示例科技",
                "role": "后端工程师",
                "period": "2024-2025",
                "skills": ["Python"],
            },
        ),
    )
    job, _ = JobService(session).import_text("Python 兼职", "客户公司", "远程兼职，要求 Python")
    evidence = EvidencePack(
        job_id=job.id,
        facts=LocalMemoryStore(session).search(profile.id, "Python", for_chat=False),
    )
    version = ResumeService(session).generate(profile, job, evidence)
    assert version.validation_status == "valid"
    fabricated = ResumeDocument(
        target_title="Python 兼职",
        summary="摘要",
        skills=["Python"],
        experiences=[
            ResumeExperience(
                company="虚构公司",
                role="后端工程师",
                period="2024-2025",
                bullets=[ResumeBullet(text="性能提升 99%", source_fact_ids=[fact.id])],
            )
        ],
    )
    try:
        ResumeValidator().validate(fabricated, evidence)
    except EvidenceValidationError as exc:
        assert "公司" in str(exc) or "量化指标" in str(exc)
    else:
        raise AssertionError("虚构简历必须失败")
