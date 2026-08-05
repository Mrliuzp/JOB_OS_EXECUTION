"""消息同步、分类和发送测试。"""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from jobos.domain.schemas import CandidateFactInput, CandidateProfileInput
from jobos.infrastructure.db.models import MessageORM, PlatformAccountORM
from jobos.memory.local_store import LocalMemoryStore
from jobos.providers.mock import MockProvider
from jobos.rules.engine import RuleEngine
from jobos.services.communication_service import CommunicationService
from jobos.services.job_service import JobService
from jobos.services.profile_service import ProfileService

POLICIES = {
    "message_policy": {
        "auto_reply_types": ["greeting", "resume_request", "availability", "experience_question"],
        "manual_review_types": [
            "salary",
            "interview_schedule",
            "technical_question",
            "personal_information",
        ],
        "always_manual_types": ["offer", "contract"],
    }
}


@pytest.mark.asyncio
async def test_sync_deduplicates_and_availability_can_auto_reply(session: Session) -> None:
    profile_service = ProfileService(session)
    profile = profile_service.upsert_profile(CandidateProfileInput(name="测试用户"))
    fact = profile_service.add_fact(
        profile.id,
        CandidateFactInput(
            fact_type="availability", statement="每周可投入 15 至 20 小时，支持远程"
        ),
    )
    account = PlatformAccountORM(provider="mock", display_name="primary", status="logged_in")
    session.add(account)
    JobService(session).import_text(
        "Python 远程兼职开发", "示例科技", "Python FastAPI 远程兼职", "mock-job-1"
    )
    session.flush()
    service = CommunicationService(session, RuleEngine(POLICIES))
    first = await service.sync(MockProvider(), account)
    second = await service.sync(MockProvider(), account)
    assert first == (1, 1)
    assert second == (0, 0)
    message = session.scalar(select(MessageORM))
    assert message is not None
    draft, approval = service.generate_reply(message, profile.id, LocalMemoryStore(session))
    assert fact.id in draft.evidence_ids
    assert approval is None
    detail = await service.send_reply(message.id, MockProvider(), account, dry_run=False)
    assert "发送" in detail
    assert (
        await service.send_reply(message.id, MockProvider(), account, dry_run=False)
        == "幂等命中，未重复发送"
    )


def test_salary_offer_and_contract_require_human(session: Session) -> None:
    service = CommunicationService(session, RuleEngine(POLICIES))
    for index, text in enumerate(("你的期望薪资是多少？", "我们给你发 Offer", "请确认合同")):
        message = MessageORM(
            conversation_id="x" * 32,
            external_message_id=str(index),
            direction="inbound",
            sender_type="recruiter",
            content=text,
        )
        result = service.classify(message)
        assert result.requires_human is True
