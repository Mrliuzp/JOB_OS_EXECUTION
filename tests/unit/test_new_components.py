"""新增组件测试。"""

from pathlib import Path

import pytest

from jobos.browser.detection import detect_chrome_path
from jobos.core.errors import CapabilityNotSupported, ProviderLoginRequired
from jobos.core.secret_store import EnvironmentSecretStore
from jobos.domain.schemas import JobSearchQuery
from jobos.infrastructure.db.models import PlatformAccountORM
from jobos.prompts.registry import PromptRegistry
from jobos.providers.skeleton import SkeletonProvider


def test_chrome_detection_and_environment_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chrome = tmp_path / "chrome.exe"
    chrome.write_text("", encoding="utf-8")
    assert detect_chrome_path(chrome) == chrome
    monkeypatch.setenv("TEST_SECRET", "value")
    store = EnvironmentSecretStore()
    assert store.get("TEST_SECRET") == "value"
    with pytest.raises(PermissionError):
        store.set("TEST_SECRET", "new")
    with pytest.raises(PermissionError):
        store.delete("TEST_SECRET")


def test_prompt_registry(tmp_path: Path) -> None:
    path = tmp_path / "task"
    path.mkdir()
    (path / "v1.md").write_text("中文 Prompt", encoding="utf-8")
    registry = PromptRegistry(tmp_path)
    assert registry.get("task") == "中文 Prompt"
    with pytest.raises(FileNotFoundError):
        registry.get("missing")


@pytest.mark.asyncio
async def test_skeleton_provider_explicitly_reports_unsupported() -> None:
    provider = SkeletonProvider("zhaopin")
    account = PlatformAccountORM(provider="zhaopin", display_name="primary", status="unknown")
    with pytest.raises(ProviderLoginRequired):
        await provider.check_login(account)
    account.status = "logged_in"
    assert (await provider.check_login(account)).logged_in
    with pytest.raises(CapabilityNotSupported):
        await provider.discover_jobs(account, JobSearchQuery())
