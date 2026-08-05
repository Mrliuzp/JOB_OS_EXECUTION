"""事实约束的简历生成与验证。"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from jobos.core.errors import EvidenceValidationError
from jobos.domain.schemas import EvidencePack
from jobos.infrastructure.db.models import CandidateProfileORM, JobORM, ResumeVersionORM

_LEAK_PATTERNS = ("作为 AI", "I cannot", "language model", "根据提示词", "以下是生成")
_METRIC = re.compile(r"(?<!\w)(\d+(?:\.\d+)?%?|\d+倍)(?!\w)")


class ResumeBullet(BaseModel):
    """简历要点及来源事实。"""

    text: str
    source_fact_ids: list[str] = Field(min_length=1)


class ResumeExperience(BaseModel):
    """工作或项目经历。"""

    company: str | None = None
    role: str | None = None
    period: str | None = None
    bullets: list[ResumeBullet]


class ResumeDocument(BaseModel):
    """结构化简历。"""

    target_title: str
    summary: str
    skills: list[str]
    experiences: list[ResumeExperience]
    education: list[ResumeExperience] = Field(default_factory=list)
    excluded_requirements: list[str] = Field(default_factory=list)
    validation_notes: list[str] = Field(default_factory=list)


class ResumeValidator:
    """对生成简历执行事实、技能、指标和模型泄漏校验。"""

    def validate(self, document: ResumeDocument, evidence: EvidencePack) -> dict[str, Any]:
        """校验简历；失败时抛出明确错误。"""
        allowed = {item.evidence_id: item for item in evidence.facts}
        errors: list[str] = []
        claims: list[ResumeBullet] = []
        for experience in [*document.experiences, *document.education]:
            claims.extend(experience.bullets)
            metadata_sources = [allowed.get(item) for bullet in experience.bullets for item in bullet.source_fact_ids]
            allowed_companies = {str(item.metadata.get("company")) for item in metadata_sources if item and item.metadata.get("company")}
            allowed_roles = {str(item.metadata.get("role")) for item in metadata_sources if item and item.metadata.get("role")}
            allowed_periods = {str(item.metadata.get("period")) for item in metadata_sources if item and item.metadata.get("period")}
            if experience.company and allowed_companies and experience.company not in allowed_companies:
                errors.append(f"公司名称缺少事实依据：{experience.company}")
            if experience.role and allowed_roles and experience.role not in allowed_roles:
                errors.append(f"职位名称缺少事实依据：{experience.role}")
            if experience.period and allowed_periods and experience.period not in allowed_periods:
                errors.append(f"时间段缺少事实依据：{experience.period}")
        for bullet in claims:
            if any(source not in allowed for source in bullet.source_fact_ids):
                errors.append(f"要点引用不存在的 evidence_id：{bullet.source_fact_ids}")
                continue
            source_text = " ".join(allowed[source].statement for source in bullet.source_fact_ids)
            generated_metrics = set(_METRIC.findall(bullet.text))
            source_metrics = set(_METRIC.findall(source_text))
            if generated_metrics - source_metrics:
                errors.append(f"要点改写或新增了量化指标：{bullet.text}")
            if any(pattern.lower() in bullet.text.lower() for pattern in _LEAK_PATTERNS):
                errors.append(f"要点包含模型自言自语：{bullet.text}")
        allowed_skills = {
            token.lower()
            for item in evidence.facts
            if item.fact_type in {"skill", "project", "employment"}
            for token in _skill_tokens(item.statement, item.metadata)
        }
        for skill in document.skills:
            if skill.lower() not in allowed_skills:
                errors.append(f"技能缺少事实依据：{skill}")
        if any(pattern.lower() in document.summary.lower() for pattern in _LEAK_PATTERNS):
            errors.append("个人简介包含模型自言自语")
        if errors:
            raise EvidenceValidationError("；".join(errors))
        return {"valid": True, "evidence_count": len(allowed), "claim_count": len(claims)}


class ResumeService:
    """用 EvidencePack 生成不虚构的定制简历。"""

    def __init__(self, session: Session, validator: ResumeValidator | None = None) -> None:
        self.session = session
        self.validator = validator or ResumeValidator()

    def generate(
        self, profile: CandidateProfileORM, job: JobORM, evidence: EvidencePack
    ) -> ResumeVersionORM:
        """确定性生成第一版简历，后续可接 LLM 只做措辞优化。"""
        skills: list[str] = []
        experiences: list[ResumeExperience] = []
        education: list[ResumeExperience] = []
        for fact in evidence.facts:
            if fact.fact_type == "skill":
                skills.extend(_skill_tokens(fact.statement, fact.metadata))
                continue
            bullet = ResumeBullet(text=fact.statement, source_fact_ids=[fact.evidence_id])
            item = ResumeExperience(
                company=_optional_text(fact.metadata.get("company")),
                role=_optional_text(fact.metadata.get("role")),
                period=_optional_text(fact.metadata.get("period")),
                bullets=[bullet],
            )
            if fact.fact_type == "education":
                education.append(item)
            elif fact.fact_type in {"employment", "project", "achievement", "metric"}:
                experiences.append(item)
        unique_skills = list(dict.fromkeys(skills))
        if not unique_skills:
            for fact in evidence.facts:
                if fact.fact_type in {"project", "employment"}:
                    unique_skills.extend(_skill_tokens(fact.statement, fact.metadata))
            unique_skills = list(dict.fromkeys(unique_skills))
        document = ResumeDocument(
            target_title=job.title,
            summary=profile.summary or f"面向 {job.title} 的真实经历摘要。",
            skills=unique_skills,
            experiences=experiences,
            education=education,
            excluded_requirements=evidence.missing_requirements,
            validation_notes=["所有内容均引用 CandidateFact evidence_id"],
        )
        report = self.validator.validate(document, evidence)
        version = ResumeVersionORM(
            profile_id=profile.id,
            job_id=job.id,
            version_type="tailored",
            language="zh-CN",
            title=f"{profile.name}-{job.title}",
            content_json=document.model_dump(),
            validation_status="valid",
            validation_report_json=report,
            prompt_version="resume-v1",
            model_name="deterministic-v1",
        )
        self.session.add(version)
        self.session.flush()
        return version


def _skill_tokens(statement: str, metadata: dict[str, Any]) -> list[str]:
    known = ["Vue", "Vue 3", "C#", ".NET", "Python", "FastAPI", "SQL", "Docker", "TypeScript", "Redis"]
    metadata_skills = metadata.get("skills", [])
    result = [str(item) for item in metadata_skills] if isinstance(metadata_skills, list) else []
    lower = statement.lower()
    result.extend(item for item in known if item.lower() in lower)
    return list(dict.fromkeys(result))


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
