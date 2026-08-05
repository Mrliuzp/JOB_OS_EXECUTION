"""候选人资料与事实服务。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from jobos.core.errors import NotFoundError
from jobos.domain.schemas import CandidateFactInput, CandidateProfileInput
from jobos.infrastructure.db.models import CandidateFactORM, CandidateProfileORM
from jobos.infrastructure.repositories import FactRepository, ProfileRepository


class ProfileService:
    """管理候选人资料、事实和基础简历导入。"""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.profiles = ProfileRepository(session)
        self.facts = FactRepository(session)

    def upsert_profile(
        self, payload: CandidateProfileInput, profile_id: str | None = None
    ) -> CandidateProfileORM:
        """创建或更新单个候选人资料。"""
        profile = self.session.get(CandidateProfileORM, profile_id) if profile_id else self.profiles.first()
        if profile is None:
            profile = CandidateProfileORM()
        for key, value in payload.model_dump().items():
            setattr(profile, key, value)
        self.profiles.save(profile)
        return profile

    def get_profile(self, profile_id: str | None = None) -> CandidateProfileORM:
        """获取指定或默认资料。"""
        if profile_id:
            return self.profiles.get(profile_id)
        profile = self.profiles.first()
        if profile is None:
            raise NotFoundError("尚未初始化候选人资料")
        return profile

    def add_fact(self, profile_id: str, payload: CandidateFactInput) -> CandidateFactORM:
        """新增可追溯事实。"""
        self.profiles.get(profile_id)
        data = payload.model_dump(exclude={"metadata"})
        fact = CandidateFactORM(profile_id=profile_id, **data, metadata_json=payload.metadata)
        return self.facts.save(fact)

    def update_fact(self, fact_id: str, payload: CandidateFactInput) -> CandidateFactORM:
        """更新事实内容和权限。"""
        fact = self.facts.get(fact_id)
        data = payload.model_dump(exclude={"metadata"})
        for key, value in data.items():
            setattr(fact, key, value)
        fact.metadata_json = payload.metadata
        self.session.flush()
        return fact

    def delete_fact(self, fact_id: str) -> None:
        """删除事实。"""
        fact = self.facts.get(fact_id)
        self.session.delete(fact)
        self.session.flush()

    def import_resume(self, profile_id: str, path: Path) -> list[CandidateFactORM]:
        """把纯文本基础简历按非空段落导入为待审核事实。"""
        text = path.read_text(encoding="utf-8")
        facts: list[CandidateFactORM] = []
        for paragraph in [item.strip() for item in text.split("\n\n") if item.strip()]:
            fact_type = _guess_fact_type(paragraph)
            fact = CandidateFactORM(
                profile_id=profile_id,
                fact_type=fact_type,
                statement=paragraph,
                source_type="resume_import",
                source_reference=str(path),
                confidence=0.9,
                sensitivity="normal",
                metadata_json={"review_required": True},
            )
            self.session.add(fact)
            facts.append(fact)
        self.session.flush()
        return facts


def _guess_fact_type(text: str) -> str:
    lower = text.lower()
    if any(token in lower for token in ("大学", "学院", "本科", "硕士", "education")):
        return "education"
    if any(token in lower for token in ("项目", "project", "系统")):
        return "project"
    if any(token in lower for token in ("年", "公司", "任职", "工作")):
        return "employment"
    if any(token in lower for token in ("python", "vue", "c#", ".net", "skill")):
        return "skill"
    return "other"


def profile_to_dict(profile: CandidateProfileORM) -> dict[str, Any]:
    """把 ORM 转为 API 可序列化字典。"""
    return {
        "id": profile.id,
        "name": profile.name,
        "preferred_name": profile.preferred_name,
        "email": profile.email,
        "phone": profile.phone,
        "city": profile.city,
        "timezone": profile.timezone,
        "summary": profile.summary,
        "automation_level": profile.automation_level,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }
