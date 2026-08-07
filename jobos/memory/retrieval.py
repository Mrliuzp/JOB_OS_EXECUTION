"""职位事实证据包构建。"""

from jobos.domain.schemas import EvidencePack
from jobos.memory.base import MemoryProvider


def build_evidence_pack(
    memory: MemoryProvider, profile_id: str, job_id: str, job_text: str, requirements: list[str]
) -> EvidencePack:
    """检索与职位最相关的真实事实。"""
    query = " ".join([job_text, *requirements])
    facts = memory.search(profile_id, query, for_chat=False, limit=30)
    fact_text = " ".join(item.statement.lower() for item in facts)
    missing = [item for item in requirements if item.lower() not in fact_text]
    return EvidencePack(job_id=job_id, facts=facts, missing_requirements=missing)
