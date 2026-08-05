"""招聘平台 Provider 协议。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

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


@dataclass(frozen=True)
class ProviderCapabilities:
    """Provider 能力声明。"""

    discovery: bool
    job_detail: bool
    initiate_chat: bool
    send_message: bool
    upload_resume: bool
    direct_apply: bool
    receive_messages: bool
    application_status: bool


class ProviderAdapter(Protocol):
    """招聘平台统一接口。"""

    name: str
    capabilities: ProviderCapabilities

    async def check_login(self, account: PlatformAccountORM) -> LoginStatus: ...

    async def discover_jobs(
        self, account: PlatformAccountORM, query: JobSearchQuery, cursor: str | None = None
    ) -> JobSearchPage: ...

    async def fetch_job_detail(
        self, account: PlatformAccountORM, job_ref: ExternalJobRef
    ) -> RawJobDetail: ...

    async def initiate_contact(
        self, account: PlatformAccountORM, request: ContactRequest
    ) -> ProviderActionResult: ...

    async def submit_application(
        self, account: PlatformAccountORM, request: SubmitApplicationRequest
    ) -> ProviderActionResult: ...

    async def list_conversations(
        self, account: PlatformAccountORM, cursor: str | None = None
    ) -> ConversationPage: ...

    async def list_messages(
        self, account: PlatformAccountORM, conversation_id: str, cursor: str | None = None
    ) -> MessagePage: ...

    async def send_message(
        self, account: PlatformAccountORM, request: SendMessageRequest
    ) -> ProviderActionResult: ...
