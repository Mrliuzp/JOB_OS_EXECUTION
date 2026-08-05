"""职位评分服务。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobos.core.errors import LLMConfigurationError
from jobos.domain.schemas import EvidencePack
from jobos.infrastructure.db.models import JobORM, JobScoreORM
from jobos.llm.gateway import LLMGateway
from jobos.llm.schemas import ChatMessage, LLMRequest
from jobos.rules.engine import RuleEngine
from jobos.rules.schemas import RuleContext


@dataclass(frozen=True)
class ScoreResult:
    """职位评分计算结果。"""

    total_score: float
    decision: str
    dimension_scores: dict[str, float]
    matched_requirements: list[str]
    missing_requirements: list[str]
    matched_evidence_ids: list[str]
    hard_reject_reasons: list[str]
    summary: str


class ScoringService:
    """先执行硬规则，再进行证据驱动评分。"""

    def __init__(
        self,
        session: Session,
        rule_engine: RuleEngine,
        llm: LLMGateway | None = None,
    ) -> None:
        self.session = session
        self.rule_engine = rule_engine
        self.llm = llm

    async def score(
        self,
        job: JobORM,
        profile_id: str,
        evidence: EvidencePack,
        *,
        require_llm: bool = False,
        provider_names: list[str] | None = None,
        model: str = "configured-model",
    ) -> JobScoreORM:
        """计算并保存职位评分。"""
        rule = self.rule_engine.evaluate_job(
            RuleContext(
                title=job.title,
                company_name=job.company_name,
                description=job.description_normalized,
                employment_type=job.employment_type,
                work_mode=job.work_mode,
            )
        )
        if rule.hard_reject:
            result = ScoreResult(
                total_score=0,
                decision="reject",
                dimension_scores=_zero_dimensions(),
                matched_requirements=[],
                missing_requirements=list(job.requirements_json),
                matched_evidence_ids=[],
                hard_reject_reasons=rule.reasons,
                summary="职位命中硬拒绝规则",
            )
        else:
            result = self._deterministic_score(job, evidence)
            if require_llm:
                if self.llm is None:
                    raise LLMConfigurationError("职位评分要求 LLM，但尚未配置模型网关")
                result = await self._llm_score(
                    job, evidence, provider_names or [], model, result
                )
        existing = self.session.scalar(
            select(JobScoreORM).where(
                JobScoreORM.job_id == job.id, JobScoreORM.profile_id == profile_id
            )
        )
        score = existing or JobScoreORM(job_id=job.id, profile_id=profile_id)
        score.total_score = result.total_score
        score.technical_score = result.dimension_scores["technical"]
        score.experience_score = result.dimension_scores["experience"]
        score.availability_score = result.dimension_scores["availability"]
        score.compensation_score = result.dimension_scores["compensation"]
        score.remote_score = result.dimension_scores["work_mode"]
        score.risk_score = result.dimension_scores["risk"]
        score.matched_skills_json = result.matched_requirements
        score.missing_skills_json = result.missing_requirements
        score.reasons_json = [result.summary, *result.hard_reject_reasons]
        score.evidence_ids_json = result.matched_evidence_ids
        score.decision = result.decision
        score.prompt_version = "scoring-v1"
        score.model_name = model if require_llm else "deterministic-v1"
        self.session.add(score)
        job.status = "scored"
        self.session.flush()
        return score

    def _deterministic_score(self, job: JobORM, evidence: EvidencePack) -> ScoreResult:
        requirements = [str(item) for item in job.requirements_json]
        corpus = " ".join(item.statement.lower() for item in evidence.facts)
        matched = [item for item in requirements if item.lower() in corpus]
        missing = [item for item in requirements if item not in matched]
        ratio = len(matched) / max(len(requirements), 1)
        technical = round(30 * ratio, 2)
        experience = min(20.0, round(len(evidence.facts) * 2.5, 2))
        employment = 15.0 if job.employment_type in {"part_time", "contract", "freelance", "temporary"} else 5.0
        work_mode = 10.0 if job.work_mode in {"remote", "hybrid"} else 3.0
        availability = 10.0 if any(item.fact_type == "availability" for item in evidence.facts) else 5.0
        compensation = 5.0 if job.salary_min is not None or job.salary_max is not None else 3.0
        credibility = 5.0 if len(job.description_normalized) >= 50 else 2.0
        risk = 5.0
        total = technical + experience + employment + work_mode + availability + compensation + credibility + risk
        if total < 55:
            decision = "reject"
        elif total < 72:
            decision = "review"
        elif total < 82:
            decision = "eligible"
        else:
            decision = "priority"
        return ScoreResult(
            total_score=round(total, 2),
            decision=decision,
            dimension_scores={
                "technical": technical,
                "experience": experience,
                "employment_type": employment,
                "work_mode": work_mode,
                "availability": availability,
                "compensation": compensation,
                "credibility": credibility,
                "risk": risk,
            },
            matched_requirements=matched,
            missing_requirements=missing,
            matched_evidence_ids=[item.evidence_id for item in evidence.facts],
            hard_reject_reasons=[],
            summary=f"匹配 {len(matched)}/{len(requirements)} 项职位要求",
        )

    async def _llm_score(
        self,
        job: JobORM,
        evidence: EvidencePack,
        provider_names: list[str],
        model: str,
        baseline: ScoreResult,
    ) -> ScoreResult:
        schema: dict[str, Any] = {
            "type": "object",
            "required": [
                "total_score",
                "decision",
                "dimension_scores",
                "matched_requirements",
                "missing_requirements",
                "matched_evidence_ids",
                "hard_reject_reasons",
                "summary",
            ],
            "properties": {
                "total_score": {"type": "number", "minimum": 0, "maximum": 100},
                "decision": {"enum": ["reject", "review", "eligible", "priority"]},
                "dimension_scores": {"type": "object"},
                "matched_requirements": {"type": "array", "items": {"type": "string"}},
                "missing_requirements": {"type": "array", "items": {"type": "string"}},
                "matched_evidence_ids": {"type": "array", "items": {"type": "string"}},
                "hard_reject_reasons": {"type": "array", "items": {"type": "string"}},
                "summary": {"type": "string"},
            },
        }
        request = LLMRequest(
            task_type="score_job",
            trace_id=f"score-{job.id}",
            response_schema=schema,
            messages=[
                ChatMessage(
                    role="system",
                    content="你是职位匹配评分器。只能引用给定 evidence_id，不得创造候选人经历。",
                ),
                ChatMessage(
                    role="user",
                    content=f"职位：{job.description_normalized}\n证据：{evidence.model_dump_json()}\n基线：{baseline}",
                ),
            ],
        )
        assert self.llm is not None
        response = await self.llm.generate(request, provider_names, model)
        parsed = response.parsed
        if not isinstance(parsed, dict):
            raise ValueError("职位评分模型未返回对象")
        raw_dimensions = parsed.get("dimension_scores", {})
        if not isinstance(raw_dimensions, dict):
            raw_dimensions = {}
        dimensions = dict(baseline.dimension_scores)
        for key in dimensions:
            value = raw_dimensions.get(key)
            if isinstance(value, (int, float)):
                dimensions[key] = float(value)
        allowed_evidence = {item.evidence_id for item in evidence.facts}
        ids = [str(item) for item in parsed.get("matched_evidence_ids", [])]
        ids = [item for item in ids if item in allowed_evidence]
        return ScoreResult(
            total_score=float(parsed["total_score"]),
            decision=str(parsed["decision"]),
            dimension_scores=dimensions,
            matched_requirements=[str(item) for item in parsed.get("matched_requirements", [])],
            missing_requirements=[str(item) for item in parsed.get("missing_requirements", [])],
            matched_evidence_ids=ids,
            hard_reject_reasons=[str(item) for item in parsed.get("hard_reject_reasons", [])],
            summary=str(parsed.get("summary", "")),
        )


def _zero_dimensions() -> dict[str, float]:
    return {
        "technical": 0,
        "experience": 0,
        "employment_type": 0,
        "work_mode": 0,
        "availability": 0,
        "compensation": 0,
        "credibility": 0,
        "risk": 0,
    }
