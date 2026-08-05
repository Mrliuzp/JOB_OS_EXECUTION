"""测试和本地演示使用的 Mock Provider。"""

from __future__ import annotations

from jobos.domain.schemas import (
    ContactRequest,
    ConversationPage,
    ExternalConversation,
    ExternalJobRef,
    ExternalMessage,
    JobSearchItem,
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


class MockProvider:
    """覆盖全部 Provider 合同的确定性实现。"""

    name = "mock"
    capabilities = ProviderCapabilities(True, True, True, True, True, True, True, True)

    def __init__(self) -> None:
        self.sent_keys: set[str] = set()

    async def check_login(self, account: PlatformAccountORM) -> LoginStatus:
        return LoginStatus(logged_in=account.status == "logged_in", account_name=account.display_name)

    async def discover_jobs(
        self, account: PlatformAccountORM, query: JobSearchQuery, cursor: str | None = None
    ) -> JobSearchPage:
        del account, cursor
        keyword = query.keywords[0] if query.keywords else "Python"
        return JobSearchPage(
            items=[
                JobSearchItem(
                    external_job_id="mock-job-1",
                    canonical_url="https://example.test/jobs/mock-job-1",
                    title=f"{keyword} 远程兼职开发",
                    company_name="示例科技",
                    location="远程",
                    salary_text="200-300元/小时",
                )
            ]
        )

    async def fetch_job_detail(
        self, account: PlatformAccountORM, job_ref: ExternalJobRef
    ) -> RawJobDetail:
        del account
        return RawJobDetail(
            external_job_id=job_ref.external_job_id,
            canonical_url=job_ref.canonical_url,
            title="Python 远程兼职开发",
            company_name="示例科技",
            location="远程",
            description="使用 Python 和 FastAPI 开发系统",
            requirements=["Python", "FastAPI"],
            work_mode="remote",
            employment_type="part_time",
        )

    async def initiate_contact(
        self, account: PlatformAccountORM, request: ContactRequest
    ) -> ProviderActionResult:
        del account
        return self._action(request.idempotency_key, request.dry_run, "已模拟发起沟通")

    async def submit_application(
        self, account: PlatformAccountORM, request: SubmitApplicationRequest
    ) -> ProviderActionResult:
        del account
        return self._action(request.idempotency_key, request.dry_run, "已模拟提交申请")

    async def list_conversations(
        self, account: PlatformAccountORM, cursor: str | None = None
    ) -> ConversationPage:
        del account, cursor
        return ConversationPage(
            items=[
                ExternalConversation(
                    external_conversation_id="mock-conversation-1",
                    external_job_id="mock-job-1",
                    recruiter_name="张 HR",
                    recruiter_company="示例科技",
                    unread_count=1,
                )
            ]
        )

    async def list_messages(
        self, account: PlatformAccountORM, conversation_id: str, cursor: str | None = None
    ) -> MessagePage:
        del account, conversation_id, cursor
        return MessagePage(
            items=[
                ExternalMessage(
                    external_message_id="mock-message-1",
                    direction="inbound",
                    sender_type="recruiter",
                    content="每周可以投入多少时间？",
                )
            ]
        )

    async def send_message(
        self, account: PlatformAccountORM, request: SendMessageRequest
    ) -> ProviderActionResult:
        del account
        return self._action(request.idempotency_key, request.dry_run, "已模拟发送消息")

    def _action(self, key: str, dry_run: bool, detail: str) -> ProviderActionResult:
        if dry_run:
            return ProviderActionResult(success=True, dry_run=True, detail=f"Dry Run：{detail}")
        if key in self.sent_keys:
            return ProviderActionResult(success=True, dry_run=False, detail="幂等命中，未重复执行")
        self.sent_keys.add(key)
        return ProviderActionResult(
            success=True, dry_run=False, external_id=f"mock-{len(self.sent_keys)}", detail=detail
        )
