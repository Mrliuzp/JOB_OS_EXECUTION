"""浏览器动作执行器。"""

from __future__ import annotations

from typing import Any, Protocol

from jobos.browser.models import BrowserAction, SelectorSpec
from jobos.browser.risk_detector import detect_browser_risk
from jobos.core.errors import ProviderActionRejected, ProviderCaptchaDetected


class LocatorLike(Protocol):
    """Playwright Locator 最小协议。"""

    async def click(self, timeout: float | None = None) -> None: ...
    async def fill(self, value: str, timeout: float | None = None) -> None: ...
    async def select_option(self, value: str) -> Any: ...
    async def set_input_files(self, files: str) -> None: ...
    async def inner_text(self) -> str: ...


class PageLike(Protocol):
    """Playwright Page 最小协议。"""

    url: str

    async def goto(self, url: str, timeout: float | None = None) -> Any: ...
    async def wait_for_timeout(self, timeout: float) -> None: ...
    async def content(self) -> str: ...
    def locator(self, selector: str) -> LocatorLike: ...
    def get_by_text(self, text: str, exact: bool = False) -> LocatorLike: ...
    def get_by_label(self, text: str) -> LocatorLike: ...
    def get_by_role(self, role: str, name: str | None = None) -> LocatorLike: ...


class BrowserActionExecutor:
    """在统一风险检查和期望状态验证下执行动作。"""

    async def execute(self, page: PageLike, action: BrowserAction) -> str | None:
        """执行一个受控动作。"""
        if action.action_type == "goto":
            if not action.value:
                raise ProviderActionRejected("goto 动作缺少 URL")
            await page.goto(action.value, timeout=float(action.timeout_ms))
        elif action.action_type == "wait":
            await page.wait_for_timeout(float(action.timeout_ms))
        elif action.action_type == "snapshot":
            return await page.content()
        else:
            locator = self._locator(page, action.selector)
            if action.action_type == "click":
                await locator.click(timeout=float(action.timeout_ms))
            elif action.action_type == "fill":
                await locator.fill(action.value or "", timeout=float(action.timeout_ms))
            elif action.action_type == "select":
                await locator.select_option(action.value or "")
            elif action.action_type == "upload":
                if not action.value:
                    raise ProviderActionRejected("upload 动作缺少文件路径")
                await locator.set_input_files(action.value)
            elif action.action_type == "extract":
                return await locator.inner_text()
            else:
                raise ProviderActionRejected(f"不支持的浏览器动作：{action.action_type}")
        content = await page.content()
        risk = detect_browser_risk(content)
        if risk.detected:
            raise ProviderCaptchaDetected(f"检测到平台风控：{risk.marker}")
        expected = action.expected_state
        if expected and expected.text_present and expected.text_present not in content:
            raise ProviderActionRejected(f"动作后未出现预期文本：{expected.text_present}")
        if expected and expected.url_contains and expected.url_contains not in page.url:
            raise ProviderActionRejected(f"动作后 URL 不符合预期：{expected.url_contains}")
        return None

    @staticmethod
    def _locator(page: PageLike, selector: SelectorSpec | None) -> LocatorLike:
        if selector is None:
            raise ProviderActionRejected("当前动作缺少元素定位信息")
        if selector.kind == "css":
            return page.locator(selector.value)
        if selector.kind == "text":
            return page.get_by_text(selector.value, exact=False)
        if selector.kind == "label":
            return page.get_by_label(selector.value)
        return page.get_by_role(selector.value, name=selector.role_name)
