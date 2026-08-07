"""职位发现服务。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from jobos.domain.schemas import ExternalJobRef, JobSearchQuery
from jobos.infrastructure.db.models import PlatformAccountORM
from jobos.providers.base import ProviderAdapter
from jobos.services.job_service import JobService


class DiscoveryService:
    """协调 Provider 搜索、详情补全和数据库去重。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    async def discover(
        self, provider: ProviderAdapter, account: PlatformAccountORM, query: JobSearchQuery
    ) -> tuple[int, int]:
        """发现并补全职位；返回发现数和新建数。"""
        page = await provider.discover_jobs(account, query)
        created = 0
        service = JobService(self.session)
        for item in page.items:
            detail = await provider.fetch_job_detail(
                account,
                ExternalJobRef(
                    external_job_id=item.external_job_id, canonical_url=item.canonical_url
                ),
            )
            _, is_new = service.import_detail(provider.name, detail)
            created += int(is_new)
        self.session.flush()
        return len(page.items), created
