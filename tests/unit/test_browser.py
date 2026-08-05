"""浏览器风险和 Profile 测试。"""

from pathlib import Path

import pytest

from jobos.browser.profile_manager import BrowserProfileManager
from jobos.browser.risk_detector import detect_browser_risk
from jobos.core.errors import ConflictError


def test_captcha_fixture_is_detected() -> None:
    assert detect_browser_risk("请完成滑块安全验证").detected is True
    assert detect_browser_risk("正常职位页面").detected is False


def test_profile_lock_prevents_concurrent_use(tmp_path: Path) -> None:
    manager = BrowserProfileManager(tmp_path)
    profile = manager.profile_path("boss", "primary")
    manager.acquire_lock(profile, "one")
    with pytest.raises(ConflictError):
        manager.acquire_lock(profile, "two")
    manager.release_lock(profile)
    assert manager.acquire_lock(profile, "two").exists()
