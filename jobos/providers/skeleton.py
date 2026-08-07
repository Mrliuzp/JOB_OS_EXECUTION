"""尚未接入真实页面的平台 Provider 骨架。"""

from __future__ import annotations

from jobos.core.errors import CapabilityNotSupported, ProviderLoginRequired
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


class SkeletonProvider:
    """保留完整接口并明确返回未支持能力。"""

    capabilities = ProviderCapabilities(False, False, False, False, False, False, False, False)

    def __init__(self, name: str) -> None:
        self.name = name

    async def check_login(self, account: PlatformAccountORM) -> LoginStatus:
        if account.status != "logged_in":
            raise ProviderLoginRequired(f"{self.name} 需要用户手动登录")
        return LoginStatus(logged_in=True, account_name=account.display_name)

    async def discover_jobs(
        self, account: PlatformAccountORM, query: JobSearchQuery, cursor: str | None = None
    ) -> JobSearchPage:
        del account, query, cursor
        raise CapabilityNotSupported(f"{self.name} 尚未实现职位发现")

    async def fetch_job_detail(
        self, account: PlatformAccountORM, job_ref: ExternalJobRef
    ) -> RawJobDetail:
        del account, job_ref
        raise CapabilityNotSupported(f"{self.name} 尚未实现职位详情")

    async def initiate_contact(
        self, account: PlatformAccountORM, request: ContactRequest
    ) -> ProviderActionResult:
        del account, request
        raise CapabilityNotSupported(f"{self.name} 尚未实现沟通")

    async def submit_application(
        self, account: PlatformAccountORM, request: SubmitApplicationRequest
    ) -> ProviderActionResult:
        del account, request
        raise CapabilityNotSupported(f"{self.name} 尚未实现投递")

    async def list_conversations(
        self, account: PlatformAccountORM, cursor: str | None = None
    ) -> ConversationPage:
        del account, cursor
        raise CapabilityNotSupported(f"{self.name} 尚未实现会话同步")

    async def list_messages(
        self, account: PlatformAccountORM, conversation_id: str, cursor: str | None = None
    ) -> MessagePage:
        del account, conversation_id, cursor
        raise CapabilityNotSupported(f"{self.name} 尚未实现消息同步")

    async def send_message(
        self, account: PlatformAccountORM, request: SendMessageRequest
    ) -> ProviderActionResult:
        del account, request
        raise CapabilityNotSupported(f"{self.name} 尚未实现消息发送")
