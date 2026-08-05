"""职位详情补全服务。"""

from sqlalchemy.orm import Session

from jobos.domain.schemas import ExternalJobRef
from jobos.infrastructure.db.models import JobORM, PlatformAccountORM
from jobos.providers.base import ProviderAdapter
from jobos.services.job_service import JobService


class EnrichmentService:
    """对已有职位重新获取详情。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    async def enrich(
        self, provider: ProviderAdapter, account: PlatformAccountORM, job: JobORM
    ) -> JobORM:
        """补全单个职位。"""
        detail = await provider.fetch_job_detail(
            account,
            ExternalJobRef(
                external_job_id=job.external_job_id, canonical_url=job.canonical_url
            ),
        )
        updated, _ = JobService(self.session).import_detail(provider.name, detail)
        return updated
