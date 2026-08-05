"""资料和事实记忆测试。"""

from sqlalchemy.orm import Session

from jobos.domain.schemas import CandidateFactInput, CandidateProfileInput
from jobos.memory.local_store import LocalMemoryStore
from jobos.services.profile_service import ProfileService


def test_restricted_fact_is_not_returned(session: Session) -> None:
    service = ProfileService(session)
    profile = service.upsert_profile(CandidateProfileInput(name="测试用户"))
    public = service.add_fact(
        profile.id,
        CandidateFactInput(fact_type="skill", statement="熟悉 Python 和 FastAPI")
    )
    service.add_fact(
        profile.id,
        CandidateFactInput(
            fact_type="compensation",
            statement="银行卡信息",
            sensitivity="restricted",
        ),
    )
    session.commit()
    results = LocalMemoryStore(session).search(profile.id, "Python", for_chat=False)
    assert [item.evidence_id for item in results] == [public.id]
