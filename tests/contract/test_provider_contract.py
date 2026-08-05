"""Provider 合同测试。"""

import pytest

from jobos.domain.schemas import (
    ContactRequest,
    ExternalJobRef,
    JobSearchQuery,
    SendMessageRequest,
)
from jobos.infrastructure.db.models import PlatformAccountORM
from jobos.providers.mock import MockProvider


@pytest.mark.contract
@pytest.mark.asyncio
async def test_mock_provider_fulfills_contract() -> None:
    provider = MockProvider()
    account = PlatformAccountORM(provider="mock", display_name="primary", status="logged_in")
    assert (await provider.check_login(account)).logged_in
    page = await provider.discover_jobs(account, JobSearchQuery(keywords=["Python"]))
    detail = await provider.fetch_job_detail(
        account, ExternalJobRef(external_job_id=page.items[0].external_job_id, canonical_url=page.items[0].canonical_url)
    )
    assert detail.title
    contact = await provider.initiate_contact(
        account,
        ContactRequest(
            job=ExternalJobRef(external_job_id=detail.external_job_id, canonical_url=detail.canonical_url),
            message="您好",
            idempotency_key="contact-1",
            dry_run=True,
        ),
    )
    assert contact.dry_run
    conversations = await provider.list_conversations(account)
    messages = await provider.list_messages(account, conversations.items[0].external_conversation_id)
    assert messages.items
    sent = await provider.send_message(
        account,
        SendMessageRequest(
            conversation_id=conversations.items[0].external_conversation_id,
            message="回复",
            idempotency_key="reply-1",
            dry_run=False,
        ),
    )
    assert sent.success
