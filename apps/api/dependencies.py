"""FastAPI 依赖和本地运行时容器。"""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from fastapi import Depends, HTTPException, Request
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from jobos.browser.detection import detect_chrome_path
from jobos.browser.profile_manager import BrowserProfileManager
from jobos.browser.session_manager import BrowserSessionManager
from jobos.core.config import JobOSSettings, load_settings
from jobos.core.errors import ConfigurationError
from jobos.infrastructure.db import create_database_engine, init_database, session_factory
from jobos.providers.boss import BossProvider
from jobos.providers.generic_web import GenericWebProvider
from jobos.providers.lagou import LagouProvider
from jobos.providers.liepin import LiepinProvider
from jobos.providers.manual import ManualProvider
from jobos.providers.mock import MockProvider
from jobos.providers.registry import ProviderRegistry
from jobos.providers.zhaopin import ZhaopinProvider


@lru_cache(maxsize=1)
def get_settings() -> JobOSSettings:
    """获取缓存配置。"""
    return load_settings()


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """获取并初始化数据库引擎。"""
    engine = create_database_engine(get_settings())
    init_database(engine)
    return engine


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """获取数据库会话工厂。"""
    return session_factory(get_engine())


def get_session() -> Generator[Session, None, None]:
    """按请求提供事务会话。"""
    with get_session_factory()() as session:
        try:
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise


@lru_cache(maxsize=1)
def get_provider_registry() -> ProviderRegistry:
    """注册内置 Provider。"""
    registry = ProviderRegistry()
    registry.register(MockProvider())
    registry.register(BossProvider())
    registry.register(ZhaopinProvider())
    registry.register(LiepinProvider())
    registry.register(LagouProvider())
    registry.register(GenericWebProvider())
    registry.register(ManualProvider())
    return registry


@lru_cache(maxsize=1)
def get_browser_session_manager() -> BrowserSessionManager:
    """创建浏览器会话管理器。"""
    settings = get_settings()
    executable = detect_chrome_path(settings.browser.executable_path)
    if executable is None:
        raise ConfigurationError("未找到 Chrome，请安装 Chrome 或设置 CHROME_PATH")
    profile_root = settings.browser.profile_root or (
        settings.resolved_data_dir() / "browser-profiles"
    )
    return BrowserSessionManager(
        executable, BrowserProfileManager(profile_root), headless=settings.browser.headless
    )


def require_local_request(
    request: Request, settings: JobOSSettings = Depends(get_settings)
) -> None:
    """默认拒绝非本机访问。"""
    if not settings.security.local_only:
        return
    host = request.client.host if request.client else ""
    if host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(status_code=403, detail="JobOS 默认仅允许本机访问")
