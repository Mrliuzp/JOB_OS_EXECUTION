"""独立浏览器 Profile 管理。"""

from __future__ import annotations

from pathlib import Path

from jobos.core.errors import ConflictError


class BrowserProfileManager:
    """创建独立 Profile 并阻止并发写入。"""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def profile_path(self, provider: str, account_name: str) -> Path:
        """返回平台账号专属 Profile。"""
        safe = f"{provider}-{account_name}".replace("/", "-").replace("\\", "-")
        path = self.root / safe
        path.mkdir(parents=True, exist_ok=True)
        return path

    def acquire_lock(self, path: Path, owner: str) -> Path:
        """创建 Profile 排他锁。"""
        lock = path / ".jobos.lock"
        if lock.exists():
            raise ConflictError(f"浏览器 Profile 正在使用：{path}")
        lock.write_text(owner, encoding="utf-8")
        return lock

    def release_lock(self, path: Path) -> None:
        """释放 Profile 锁。"""
        lock = path / ".jobos.lock"
        lock.unlink(missing_ok=True)

    def cleanup_singletons(self, path: Path) -> None:
        """清理 Chrome 异常退出残留文件。"""
        for name in ("SingletonCookie", "SingletonLock", "SingletonSocket"):
            (path / name).unlink(missing_ok=True)
