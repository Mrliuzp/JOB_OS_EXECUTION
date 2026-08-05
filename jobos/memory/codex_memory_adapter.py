"""Codex Memory 同步适配器。"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy.orm import Session

from jobos.infrastructure.db.models import CandidateFactORM


class CodexMemoryAdapter:
    """把外部记忆记录同步为 CandidateFact。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def sync(self, profile_id: str, records: Iterable[dict[str, Any]]) -> int:
        """同步外部记录；不直接把结果发送给模型。"""
        count = 0
        for record in records:
            statement = str(record.get("statement", "")).strip()
            if not statement:
                continue
            fact = CandidateFactORM(
                profile_id=profile_id,
                fact_type=str(record.get("fact_type", "other")),
                statement=statement,
                source_type="codex_memory",
                source_reference=str(record.get("id", "")) or None,
                confidence=float(record.get("confidence", 1.0)),
                sensitivity=str(record.get("sensitivity", "normal")),
                metadata_json={"external_id": record.get("id")},
            )
            self.session.add(fact)
            count += 1
        self.session.flush()
        return count
