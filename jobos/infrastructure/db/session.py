"""数据库引擎、会话与初始化。"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from jobos.core.config import JobOSSettings
from jobos.infrastructure.db.models import Base


def normalize_database_url(url: str) -> str:
    """展开 SQLite URL 中的用户目录。"""
    prefix = "sqlite:///"
    if url.startswith(prefix):
        raw_path = url[len(prefix) :]
        if raw_path != ":memory:":
            path = Path(raw_path).expanduser().resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            return f"{prefix}{path.as_posix()}"
    return url


def create_database_engine(settings: JobOSSettings) -> Engine:
    """创建数据库引擎，并为 SQLite 打开外键和 WAL。"""
    url = normalize_database_url(settings.database.url)
    connect_args: dict[str, object] = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(url, echo=settings.database.echo, future=True, connect_args=connect_args)
    if url.startswith("sqlite"):
        wal_enabled = settings.database.wal

        @event.listens_for(engine, "connect")
        def configure_sqlite(dbapi_connection: object, _connection_record: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            if wal_enabled and url != "sqlite:///:memory:":
                cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


def session_factory(engine: Engine) -> sessionmaker[Session]:
    """创建显式事务会话工厂。"""
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False, future=True)


def init_database(engine: Engine) -> None:
    """初始化所有核心表。"""
    Base.metadata.create_all(engine)


def drop_database(engine: Engine) -> None:
    """仅供测试和本地重置使用。"""
    Base.metadata.drop_all(engine)
