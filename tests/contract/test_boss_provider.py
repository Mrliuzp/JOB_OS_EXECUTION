"""BOSS Provider 离线合同测试。"""

from pathlib import Path

import pytest

from jobos.core.errors import ProviderCaptchaDetected, ProviderLoginRequired
from jobos.domain.schemas import ContactRequest, ExternalJobRef, JobSearchQuery
from jobos.infrastructure.db.models import PlatformAccountORM
from jobos.providers.boss import BossProvider

FIXTURES = Path(__file__).parents[1] / "browser_fixtures"


@pytest.mark.asyncio
async def test_boss_login_search_and_detail() -> None:
    async def loader(url: str) -> str:
        if "user" in url:
            return (FIXTURES / "boss-login.html").read_text(encoding="utf-8")
        if "job_detail" in url:
            return (FIXTURES / "boss-detail.html").read_text(encoding="utf-8")
        return (FIXTURES / "boss-search.html").read_text(encoding="utf-8")

    provider = BossProvider(html_loader=loader)
    account = PlatformAccountORM(provider="boss", display_name="primary")
    assert (await provider.check_login(account)).logged_in
    page = await provider.discover_jobs(account, JobSearchQuery(keywords=["Vue"]))
    assert len(page.items) == 2
    detail = await provider.fetch_job_detail(
        account,
        ExternalJobRef(external_job_id="boss-001", canonical_url=page.items[0].canonical_url),
    )
    assert detail.work_mode == "remote"
    assert detail.employment_type == "part_time"


@pytest.mark.asyncio
async def test_boss_dry_run_never_calls_action_runner() -> None:
    called = False

    async def runner(action: str, payload: dict[str, str]) -> str:
        nonlocal called
        del action, payload
        called = True
        return "external-id"

    provider = BossProvider(action_runner=runner)
    account = PlatformAccountORM(provider="boss", display_name="primary")
    result = await provider.initiate_contact(
        account,
        ContactRequest(
            job=ExternalJobRef(external_job_id="1", canonical_url="https://example.test/1"),
            message="您好",
            idempotency_key="k1",
            dry_run=True,
        ),
    )
    assert result.dry_run is True
    assert called is False


@pytest.mark.asyncio
async def test_boss_login_required_and_captcha() -> None:
    async def login_loader(url: str) -> str:
        del url
        return "<html><body>请登录</body></html>"

    provider = BossProvider(html_loader=login_loader)
    account = PlatformAccountORM(provider="boss", display_name="primary")
    with pytest.raises(ProviderLoginRequired):
        await provider.check_login(account)

    async def captcha_loader(url: str) -> str:
        del url
        return (FIXTURES / "captcha.html").read_text(encoding="utf-8")

    provider = BossProvider(html_loader=captcha_loader)
    with pytest.raises(ProviderCaptchaDetected):
        await provider.discover_jobs(account, JobSearchQuery(keywords=["Vue"]))
