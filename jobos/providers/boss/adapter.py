"""BOSS 直聘 Provider 适配器。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from urllib.parse import quote_plus

from jobos.browser.risk_detector import detect_browser_risk
from jobos.core.errors import (
    CapabilityNotSupported,
    ProviderCaptchaDetected,
    ProviderLoginRequired,
    ProviderTemporaryError,
)
from jobos.domain.schemas import (
    ContactRequest,
    ConversationPage,
    ExternalJobRef,
    JobSearchPage,
    JobSearchQuery,
    LoginStatus,
    MessagePage,
    ProviderActionResult,
    RawJobDetail,
    SendMessageRequest,
    SubmitApplicationRequest,
)
from jobos.infrastructure.db.models import PlatformAccountORM
from jobos.providers.base import ProviderCapabilities
from jobos.providers.boss.parser import (
    parse_conversations,
    parse_job_detail,
    parse_messages,
    parse_search_page,
)

HTMLLoader = Callable[[str], Awaitable[str]]
ActionRunner = Callable[[str, dict[str, str]], Awaitable[str]]


class BossProvider:
    """以用户本人持久化浏览器会话操作 BOSS 直聘。"""

    name = "boss"
    capabilities = ProviderCapabilities(
        discovery=True,
        job_detail=True,
        initiate_chat=True,
        send_message=True,
        upload_resume=True,
        direct_apply=False,
        receive_messages=True,
        application_status=False,
    )

    def __init__(
        self, html_loader: HTMLLoader | None = None, action_runner: ActionRunner | None = None
    ) -> None:
        self.html_loader = html_loader
        self.action_runner = action_runner
        self._completed_keys: set[str] = set()

    async def check_login(self, account: PlatformAccountORM) -> LoginStatus:
        """检查当前 Profile 是否已经登录。"""
        html = await self._load("https://www.zhipin.com/web/user/?ka=header-personal")
        risk = detect_browser_risk(html)
        if risk.detected:
            return LoginStatus(logged_in=False, requires_manual_action=True)
        logged_in = any(
            marker in html
            for marker in ('data-user-logged-in="true"', "退出登录", "个人中心")
        )
        if not logged_in:
            raise ProviderLoginRequired("BOSS 账号需要在独立 Chrome Profile 中手动登录")
        return LoginStatus(logged_in=True, account_name=account.display_name)

    async def discover_jobs(
        self, account: PlatformAccountORM, query: JobSearchQuery, cursor: str | None = None
    ) -> JobSearchPage:
        """搜索并解析职位列表，不执行沟通动作。"""
        del account
        keyword = quote_plus(" ".join(query.keywords))
        page = cursor or "1"
        url = f"https://www.zhipin.com/web/geek/job?query={keyword}&page={page}"
        html = await self._load(url)
        risk = detect_browser_risk(html)
        if risk.detected:
            raise ProviderCaptchaDetected(f"BOSS 搜索触发风控：{risk.marker}")
        return parse_search_page(html)

    async def fetch_job_detail(
        self, account: PlatformAccountORM, job_ref: ExternalJobRef
    ) -> RawJobDetail:
        """获取并标准化职位详情。"""
        del account
        html = await self._load(job_ref.canonical_url)
        risk = detect_browser_risk(html)
        if risk.detected:
            raise ProviderCaptchaDetected(f"BOSS 详情页触发风控：{risk.marker}")
        return parse_job_detail(html, job_ref.canonical_url)

    async def initiate_contact(
        self, account: PlatformAccountORM, request: ContactRequest
    ) -> ProviderActionResult:
        """发起沟通；Dry Run 永远停在最终发送前。"""
        del account
        return await self._side_effect(
            "initiate_contact",
            request.idempotency_key,
            request.dry_run,
            {
                "url": request.job.canonical_url,
                "message": request.message,
                "resume_path": request.resume_path or "",
            },
        )

    async def submit_application(
        self, account: PlatformAccountORM, request: SubmitApplicationRequest
    ) -> ProviderActionResult:
        del account, request
        raise CapabilityNotSupported("BOSS Provider 不支持通用 direct_apply；请使用发起沟通流程")

    async def list_conversations(
        self, account: PlatformAccountORM, cursor: str | None = None
    ) -> ConversationPage:
        """解析登录后的会话列表。"""
        del account
        page = cursor or "1"
        html = await self._load(f"https://www.zhipin.com/web/geek/chat?page={page}")
        risk = detect_browser_risk(html)
        if risk.detected:
            raise ProviderCaptchaDetected(f"BOSS 会话页触发风控：{risk.marker}")
        return parse_conversations(html)

    async def list_messages(
        self, account: PlatformAccountORM, conversation_id: str, cursor: str | None = None
    ) -> MessagePage:
        """解析指定会话的消息。"""
        del account
        page = cursor or "1"
        html = await self._load(
            f"https://www.zhipin.com/web/geek/chat?id={conversation_id}&page={page}"
        )
        risk = detect_browser_risk(html)
        if risk.detected:
            raise ProviderCaptchaDetected(f"BOSS 消息页触发风控：{risk.marker}")
        return parse_messages(html)

    async def send_message(
        self, account: PlatformAccountORM, request: SendMessageRequest
    ) -> ProviderActionResult:
        """发送站内消息，并执行幂等检查。"""
        del account
        return await self._side_effect(
            "send_message",
            request.idempotency_key,
            request.dry_run,
            {"conversation_id": request.conversation_id, "message": request.message},
        )

    async def _load(self, url: str) -> str:
        if self.html_loader is None:
            raise ProviderTemporaryError("未配置登录浏览器的 HTML 加载器")
        return await self.html_loader(url)

    async def _side_effect(
        self, action: str, idempotency_key: str, dry_run: bool, payload: dict[str, str]
    ) -> ProviderActionResult:
        if dry_run:
            return ProviderActionResult(
                success=True, dry_run=True, detail=f"Dry Run：已验证 {action}，未点击最终发送按钮"
            )
        if idempotency_key in self._completed_keys:
            return ProviderActionResult(
                success=True, dry_run=False, detail="幂等命中，未重复执行平台动作"
            )
        if self.action_runner is None:
            raise ProviderTemporaryError("未配置受控浏览器动作运行器")
        result = await self.action_runner(action, payload)
        risk = detect_browser_risk(result)
        if risk.detected:
            raise ProviderCaptchaDetected(f"BOSS 动作触发风控：{risk.marker}")
        self._completed_keys.add(idempotency_key)
        return ProviderActionResult(
            success=True,
            dry_run=False,
            external_id=result,
            detail="平台动作完成",
        )
