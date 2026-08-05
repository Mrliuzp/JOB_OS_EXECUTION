"""基于关系数据库的本地事实存储。"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobos.domain.schemas import EvidenceFact
from jobos.infrastructure.db.models import CandidateFactORM

_TOKEN = re.compile(r"[A-Za-z0-9+#.]+|[\u4e00-\u9fff]{2,}")


def _tokens(text: str) -> set[str]:
    """同时生成英文词和中文二元词，提升问句与事实的匹配率。"""
    result: set[str] = set()
    for token in _TOKEN.findall(text):
        lowered = token.lower()
        result.add(lowered)
        if any("\u4e00" <= char <= "\u9fff" for char in token):
            result.update(token[index : index + 2] for index in range(max(len(token) - 1, 0)))
    return result


class LocalMemoryStore:
    """支持敏感性过滤和简单相关性排序的本地事实库。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def search(
        self, profile_id: str, query: str, *, for_chat: bool, limit: int = 20
    ) -> list[EvidenceFact]:
        """检索可用于简历或聊天的有效事实。"""
        now = datetime.now(timezone.utc)
        stmt = select(CandidateFactORM).where(
            CandidateFactORM.profile_id == profile_id,
            CandidateFactORM.sensitivity != "restricted",
        )
        if for_chat:
            stmt = stmt.where(CandidateFactORM.allowed_for_chat.is_(True))
        else:
            stmt = stmt.where(CandidateFactORM.allowed_for_resume.is_(True))
        facts = list(self.session.scalars(stmt).all())
        query_tokens = _tokens(query)
        scored: list[tuple[float, CandidateFactORM]] = []
        for fact in facts:
            if fact.valid_from and _aware(fact.valid_from) > now:
                continue
            if fact.valid_until and _aware(fact.valid_until) < now:
                continue
            fact_tokens = _tokens(fact.statement + " " + str(fact.metadata_json))
            overlap = len(query_tokens & fact_tokens)
            score = overlap * 2 + fact.confidence
            if not query_tokens or overlap > 0:
                scored.append((score, fact))
        scored.sort(key=lambda item: (item[0], item[1].confidence), reverse=True)
        return [
            EvidenceFact(
                evidence_id=fact.id,
                statement=fact.statement,
                fact_type=fact.fact_type,
                confidence=fact.confidence,
                metadata=fact.metadata_json,
            )
            for _, fact in scored[:limit]
        ]


def _aware(value: datetime) -> datetime:
    """兼容 SQLite 返回的无时区时间。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
