"""申请审批和 Dry Run 测试。"""

import pytest
from sqlalchemy.orm import Session

from jobos.core.enums import AutomationLevel
from jobos.core.errors import ApprovalRequiredError
from jobos.infrastructure.db.models import (
    CandidateProfileORM,
    PlatformAccountORM,
    ResumeVersionORM,
)
from jobos.providers.mock import MockProvider
from jobos.services.application_service import ApplicationService
from jobos.services.job_service import JobService


@pytest.mark.asyncio
async def test_l1_requires_approval_and_dry_run_does_not_submit(session: Session) -> None:
    profile = CandidateProfileORM(name="测试用户")
    account = PlatformAccountORM(provider="mock", display_name="primary", status="logged_in")
    session.add_all([profile, account])
    session.flush()
    job, _ = JobService(session).import_text("Python 兼职", "示例", "远程兼职 Python")
    resume = ResumeVersionORM(profile_id=profile.id, job_id=job.id, title="简历")
    session.add(resume)
    session.flush()
    service = ApplicationService(session)
    application = service.create(job.id, profile.id, account.id, AutomationLevel.L1)
    approval = service.prepare_materials(application.id, resume.id, "您好，我有相关经验。")
    assert approval is not None
    with pytest.raises(ApprovalRequiredError):
        await service.submit(application.id, MockProvider(), account, job, dry_run=True)
    service.resolve_approval(approval.id, True)
    result = await service.submit(application.id, MockProvider(), account, job, dry_run=True)
    assert result.dry_run is True
    assert application.status == "approved"


def test_l3_high_risk_still_requires_approval(session: Session) -> None:
    profile = CandidateProfileORM(name="测试用户")
    session.add(profile)
    session.flush()
    job, _ = JobService(session).import_text("Python 兼职", "示例", "远程兼职 Python")
    resume = ResumeVersionORM(profile_id=profile.id, job_id=job.id, title="简历")
    session.add(resume)
    session.flush()
    service = ApplicationService(session)
    application = service.create(job.id, profile.id, None, AutomationLevel.L3)
    approval = service.prepare_materials(application.id, resume.id, "您好", high_risk=True)
    assert approval is not None
    assert application.status == "awaiting_approval"
