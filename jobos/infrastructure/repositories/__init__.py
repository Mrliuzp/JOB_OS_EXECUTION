"""Repository 公共接口。"""

from jobos.infrastructure.repositories.repositories import (
    ApprovalRepository,
    AuditRepository,
    FactRepository,
    JobRepository,
    ProfileRepository,
)

__all__ = [
    "ApprovalRepository",
    "AuditRepository",
    "FactRepository",
    "JobRepository",
    "ProfileRepository",
]
