"""职位发现和补全服务测试。"""

import pytest
from sqlalchemy.orm import Session

from jobos.domain.schemas import JobSearchQuery
from jobos.infrastructure.db.models import PlatformAccountORM
from jobos.infrastructure.repositories import JobRepository
from jobos.providers.mock import MockProvider
from jobos.services.discovery_service import DiscoveryService
from jobos.services.enrichment_service import EnrichmentService


@pytest.mark.asyncio
async def test_discovery_and_enrichment(session: Session) -> None:
    account = PlatformAccountORM(provider="mock", display_name="primary", status="logged_in")
    session.add(account)
    session.flush()
    discovered, created = await DiscoveryService(session).discover(
        MockProvider(), account, JobSearchQuery(keywords=["Python"])
    )
    assert (discovered, created) == (1, 1)
    job = JobRepository(session).list()[0]
    enriched = await EnrichmentService(session).enrich(MockProvider(), account, job)
    assert enriched.description_normalized
