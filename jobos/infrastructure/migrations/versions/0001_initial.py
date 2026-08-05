"""初始化 JobOS 核心表。

修订号：0001
父修订号：无
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from jobos.infrastructure.db.models import Base

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建全部核心表。"""
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """删除全部核心表。"""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
