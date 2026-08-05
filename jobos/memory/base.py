"""记忆 Provider 协议。"""

from __future__ import annotations

from typing import Protocol

from jobos.domain.schemas import EvidenceFact


class MemoryProvider(Protocol):
    """候选人事实存储协议。"""

    def search(
        self, profile_id: str, query: str, *, for_chat: bool, limit: int = 20
    ) -> list[EvidenceFact]: ...
