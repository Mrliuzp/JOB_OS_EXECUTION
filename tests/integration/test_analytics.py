"""分析指标测试。"""

from sqlalchemy.orm import Session

from jobos.infrastructure.db.models import ApplicationORM, CandidateProfileORM
from jobos.services.analytics_service import AnalyticsService
from jobos.services.job_service import JobService


def test_analytics_computes_rates_without_claiming_causality(session: Session) -> None:
    profile = CandidateProfileORM(name="测试用户")
    session.add(profile)
    session.flush()
    job, _ = JobService(session).import_text("Python 兼职", "示例", "远程兼职 Python")
    job.status = "scored"
    session.add_all(
        [
            ApplicationORM(
                job_id=job.id,
                profile_id=profile.id,
                status="interviewing",
                idempotency_key="a1",
            )
        ]
    )
    session.flush()
    summary = AnalyticsService(session).summary()
    assert summary.jobs == 1
    assert summary.interview_rate == 1.0
    assert "相关性" in summary.note
