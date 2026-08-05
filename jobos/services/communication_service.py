"""会话同步、消息分类、回复生成和发送服务。"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobos.core.enums import MessageType, RiskLevel
from jobos.core.errors import ApprovalRequiredError, NotFoundError
from jobos.core.idempotency import build_idempotency_key
from jobos.domain.schemas import (
    MessageClassification,
    ReplyDraft,
    SendMessageRequest,
)
from jobos.infrastructure.db.models import (
    ApprovalRequestORM,
    ConversationORM,
    JobORM,
    MessageORM,
    PlatformAccountORM,
)
from jobos.memory.base import MemoryProvider
from jobos.providers.base import ProviderAdapter
from jobos.rules.engine import RuleEngine
from jobos.rules.schemas import RuleContext


class CommunicationService:
    """站内消息的确定性安全处理流程。"""

    def __init__(self, session: Session, rules: RuleEngine) -> None:
        self.session = session
        self.rules = rules

    async def sync(self, provider: ProviderAdapter, account: PlatformAccountORM) -> tuple[int, int]:
        """同步会话和消息，按外部 ID 去重。"""
        conversations = await provider.list_conversations(account)
        conversation_count = 0
        message_count = 0
        for external in conversations.items:
            conversation = self.session.scalar(
                select(ConversationORM).where(
                    ConversationORM.provider == provider.name,
                    ConversationORM.external_conversation_id == external.external_conversation_id,
                )
            )
            if conversation is None:
                job_id = None
                if external.external_job_id:
                    job_id = self.session.scalar(
                        select(JobORM.id).where(
                            JobORM.provider == provider.name,
                            JobORM.external_job_id == external.external_job_id,
                        )
                    )
                conversation = ConversationORM(
                    provider=provider.name,
                    external_conversation_id=external.external_conversation_id,
                    job_id=job_id,
                )
                self.session.add(conversation)
                self.session.flush()
                conversation_count += 1
            conversation.recruiter_name = external.recruiter_name
            conversation.recruiter_company = external.recruiter_company
            conversation.unread_count = external.unread_count
            conversation.last_message_at = external.last_message_at
            page = await provider.list_messages(account, external.external_conversation_id)
            for external_message in page.items:
                existing = self.session.scalar(
                    select(MessageORM.id).where(
                        MessageORM.conversation_id == conversation.id,
                        MessageORM.external_message_id == external_message.external_message_id,
                    )
                )
                if existing is not None:
                    continue
                message = MessageORM(
                    conversation_id=conversation.id,
                    external_message_id=external_message.external_message_id,
                    direction=external_message.direction,
                    sender_type=external_message.sender_type,
                    content=external_message.content,
                    sent_at=external_message.sent_at
                    if external_message.direction == "outbound"
                    else None,
                    received_at=external_message.sent_at
                    if external_message.direction == "inbound"
                    else None,
                    metadata_json=external_message.metadata,
                )
                self.session.add(message)
                message_count += 1
        self.session.flush()
        return conversation_count, message_count

    def classify(self, message: MessageORM) -> MessageClassification:
        """按照关键词和风险规则分类 HR 消息。"""
        text = message.content.lower()
        mapping: list[tuple[tuple[str, ...], MessageType, RiskLevel, list[str]]] = [
            (("offer", "录用", "入职通知"), MessageType.OFFER, RiskLevel.CRITICAL, []),
            (("合同", "签约"), MessageType.CONTRACT, RiskLevel.CRITICAL, []),
            (
                ("薪资", "薪酬", "报价", "时薪"),
                MessageType.SALARY,
                RiskLevel.HIGH,
                ["compensation"],
            ),
            (
                ("面试", "几点", "时间方便"),
                MessageType.INTERVIEW_SCHEDULE,
                RiskLevel.HIGH,
                ["availability"],
            ),
            (
                ("身份证", "银行卡", "住址"),
                MessageType.PERSONAL_INFORMATION,
                RiskLevel.CRITICAL,
                [],
            ),
            (
                ("每周", "投入时间", "什么时候开始", "可以远程"),
                MessageType.AVAILABILITY,
                RiskLevel.LOW,
                ["availability"],
            ),
            (("简历", "附件"), MessageType.RESUME_REQUEST, RiskLevel.LOW, []),
            (
                ("经验", "做过", "熟悉"),
                MessageType.EXPERIENCE_QUESTION,
                RiskLevel.LOW,
                ["employment", "project", "skill"],
            ),
            (("你好", "您好"), MessageType.GREETING, RiskLevel.LOW, []),
        ]
        selected: tuple[MessageType, RiskLevel, list[str]] = (
            MessageType.UNKNOWN,
            RiskLevel.MEDIUM,
            [],
        )
        for markers, message_type, risk, fact_types in mapping:
            if any(marker in text for marker in markers):
                selected = (message_type, risk, fact_types)
                break
        decision = self.rules.evaluate_message(
            RuleContext(
                title="",
                company_name="",
                description=message.content,
                message_type=selected[0].value,
                risk_level=selected[1].value,
            )
        )
        message.message_type = selected[0].value
        message.risk_level = selected[1].value
        message.reply_status = "classified"
        self.session.flush()
        return MessageClassification(
            message_type=selected[0].value,
            risk_level=selected[1].value,
            intent=f"识别为 {selected[0].value}",
            required_fact_types=selected[2],
            requires_human=decision.action in {"review", "manual_required"},
            confidence=0.95 if selected[0] != MessageType.UNKNOWN else 0.55,
        )

    def generate_reply(
        self, message: MessageORM, profile_id: str, memory: MemoryProvider
    ) -> tuple[ReplyDraft, ApprovalRequestORM | None]:
        """仅使用允许聊天的事实生成回复。"""
        classification = self.classify(message)
        facts = memory.search(profile_id, message.content, for_chat=True, limit=8)
        if classification.message_type == MessageType.RESUME_REQUEST.value:
            reply = "可以，我会通过平台发送与该职位匹配的简历，请查收。"
            evidence_ids: list[str] = []
        elif facts:
            reply = "；".join(item.statement for item in facts[:3])
            evidence_ids = [item.evidence_id for item in facts[:3]]
        else:
            reply = "这个问题需要我确认后再回复您。"
            evidence_ids = []
            classification.requires_human = True
        draft = ReplyDraft(
            reply=reply,
            evidence_ids=evidence_ids,
            requires_human=classification.requires_human,
            risk_flags=[] if not classification.requires_human else [classification.risk_level],
        )
        message.generated_reply = draft.reply
        message.reply_status = "awaiting_approval" if draft.requires_human else "auto_approved"
        approval = None
        if draft.requires_human:
            approval = ApprovalRequestORM(
                entity_type="message",
                entity_id=message.id,
                approval_type="message_reply",
                reason=f"消息类型 {classification.message_type} 需要人工确认",
                payload_json=draft.model_dump(),
            )
            self.session.add(approval)
        self.session.flush()
        return draft, approval

    def approve_reply(self, message_id: str, edited_reply: str | None = None) -> MessageORM:
        """批准回复，并以人工编辑后的最终文本为准。"""
        message = self._get_message(message_id)
        if edited_reply is not None:
            message.generated_reply = edited_reply.strip()
        message.reply_status = "approved"
        approvals = self.session.scalars(
            select(ApprovalRequestORM).where(
                ApprovalRequestORM.entity_type == "message",
                ApprovalRequestORM.entity_id == message.id,
                ApprovalRequestORM.status == "pending",
            )
        ).all()
        for approval in approvals:
            approval.status = "approved"
            approval.resolved_at = datetime.now(timezone.utc)
            approval.resolved_by = "local-user"
        self.session.flush()
        return message

    async def send_reply(
        self,
        message_id: str,
        provider: ProviderAdapter,
        account: PlatformAccountORM,
        *,
        dry_run: bool = True,
    ) -> str:
        """发送最终版本回复，同一消息不会重复发送。"""
        message = self._get_message(message_id)
        if message.reply_status not in {"approved", "auto_approved", "sent"}:
            raise ApprovalRequiredError("回复尚未获得发送许可")
        if message.reply_status == "sent":
            return "幂等命中，未重复发送"
        if not message.generated_reply:
            raise NotFoundError("回复内容不存在")
        conversation = self.session.get(ConversationORM, message.conversation_id)
        if conversation is None:
            raise NotFoundError("会话不存在")
        key = build_idempotency_key("reply", {"message_id": message.id})
        result = await provider.send_message(
            account,
            SendMessageRequest(
                conversation_id=conversation.external_conversation_id,
                message=message.generated_reply,
                idempotency_key=key,
                dry_run=dry_run,
            ),
        )
        if result.success and not result.dry_run:
            message.reply_status = "sent"
            message.sent_at = datetime.now(timezone.utc)
        self.session.flush()
        return result.detail

    def _get_message(self, message_id: str) -> MessageORM:
        message = self.session.get(MessageORM, message_id)
        if message is None:
            raise NotFoundError(f"消息不存在：{message_id}")
        return message
