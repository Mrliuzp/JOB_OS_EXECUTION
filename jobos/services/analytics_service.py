"""求职效果分析服务。"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from jobos.infrastructure.db.models import ApplicationORM, ConversationORM, JobORM, MessageORM, ResumeVersionORM


@dataclass(frozen=True)
class AnalyticsSummary:
    """只描述观测数据，不宣称因果关系。"""

    jobs: int
    eligible_jobs: int
    applications: int
    submitted: int
    interviews: int
    offers: int
    inbound_messages: int
    reply_rate: float
    interview_rate: float
    offer_rate: float
    note: str = "指标仅反映相关性，不代表某个策略直接导致结果。"

    def to_dict(self) -> dict[str, object]:
        """转换为 API 字典。"""
        return asdict(self)


class AnalyticsService:
    """从业务数据计算漏斗指标。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def summary(self) -> AnalyticsSummary:
        """计算总览指标。"""
        jobs = self._count(JobORM)
        eligible = int(
            self.session.scalar(
                select(func.count(JobORM.id)).where(JobORM.status.in_(["eligible", "scored"]))
            )
            or 0
        )
        applications = self._count(ApplicationORM)
        submitted = int(
            self.session.scalar(
                select(func.count(ApplicationORM.id)).where(
                    ApplicationORM.status.in_(["submitted", "viewed", "interviewing", "offer", "accepted"])
                )
            )
            or 0
        )
        interviews = int(
            self.session.scalar(
                select(func.count(ApplicationORM.id)).where(
                    ApplicationORM.status.in_(["interviewing", "offer", "accepted"])
                )
            )
            or 0
        )
        offers = int(
            self.session.scalar(
                select(func.count(ApplicationORM.id)).where(
                    ApplicationORM.status.in_(["offer", "accepted"])
                )
            )
            or 0
        )
        inbound = int(
            self.session.scalar(
                select(func.count(MessageORM.id)).where(MessageORM.direction == "inbound")
            )
            or 0
        )
        conversations = self._count(ConversationORM)
        return AnalyticsSummary(
            jobs=jobs,
            eligible_jobs=eligible,
            applications=applications,
            submitted=submitted,
            interviews=interviews,
            offers=offers,
            inbound_messages=inbound,
            reply_rate=_rate(conversations, submitted),
            interview_rate=_rate(interviews, submitted),
            offer_rate=_rate(offers, submitted),
        )

    def resume_performance(self) -> list[dict[str, object]]:
        """按简历版本统计申请数和面试数。"""
        rows = self.session.execute(
            select(
                ResumeVersionORM.id,
                ResumeVersionORM.title,
                func.count(ApplicationORM.id),
                func.sum(
                    case(
                        (ApplicationORM.status.in_(["interviewing", "offer", "accepted"]), 1),
                        else_=0,
                    )
                ),
            )
            .outerjoin(ApplicationORM, ApplicationORM.resume_version_id == ResumeVersionORM.id)
            .group_by(ResumeVersionORM.id, ResumeVersionORM.title)
        ).all()
        return [
            {"resume_id": row[0], "title": row[1], "applications": int(row[2] or 0), "interviews": int(row[3] or 0)}
            for row in rows
        ]

    def _count(self, model: type[object]) -> int:
        return int(self.session.scalar(select(func.count()).select_from(model)) or 0)


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0
