"""测试公共夹具。"""

from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from jobos.infrastructure.db.models import Base


@pytest.fixture()
def engine(tmp_path: Path) -> Generator[Engine, None, None]:
    database = tmp_path / "test.db"
    value = create_engine(
        f"sqlite:///{database.as_posix()}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(value)
    yield value
    value.dispose()


@pytest.fixture()
def factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture()
def session(factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    with factory() as value:
        yield value
        value.rollback()
