"""数据库和迁移基础测试。"""

from pathlib import Path

from sqlalchemy import create_engine, inspect

from jobos.core.config.settings import JobOSSettings
from jobos.infrastructure.db.session import create_database_engine, init_database, normalize_database_url


def test_database_initializes_all_core_tables(tmp_path: Path) -> None:
    settings = JobOSSettings.model_validate(
        {"database": {"url": f"sqlite:///{tmp_path / 'jobos.db'}", "wal": True}}
    )
    engine = create_database_engine(settings)
    init_database(engine)
    tables = set(inspect(engine).get_table_names())
    assert {"candidate_profiles", "candidate_facts", "jobs", "workflow_tasks", "audit_events"} <= tables
    engine.dispose()


def test_database_url_supports_postgresql_without_rewrite() -> None:
    url = "postgresql+psycopg://user:pass@localhost/jobos"
    assert normalize_database_url(url) == url


def test_alembic_upgrade_and_downgrade(tmp_path: Path) -> None:
    """迁移脚本能够在空数据库上升级并回退。"""
    from alembic import command
    from alembic.config import Config

    database_path = tmp_path / "migration.db"
    configuration = Config("alembic.ini")
    configuration.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(configuration, "head")
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    assert "jobs" in inspect(engine).get_table_names()
    engine.dispose()
    command.downgrade(configuration, "base")
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()


def test_postgresql_schema_roundtrip_when_ci_database_available() -> None:
    """CI 提供 PostgreSQL 时验证核心模型能够建表和删表。"""
    import os

    import pytest

    database_url = os.environ.get("JOBOS_TEST_POSTGRES_URL")
    if not database_url:
        pytest.skip("本地未配置 PostgreSQL 集成测试数据库")
    settings = JobOSSettings.model_validate({"database": {"url": database_url, "wal": False}})
    engine = create_database_engine(settings)
    from jobos.infrastructure.db.models import Base

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    assert "jobs" in inspect(engine).get_table_names()
    Base.metadata.drop_all(engine)
    engine.dispose()
