"""Chrome 进程和 CDP 端口管理。"""

from __future__ import annotations

import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from jobos.browser.models import BrowserSession
from jobos.browser.profile_manager import BrowserProfileManager
from jobos.core.errors import NotFoundError, ProviderTemporaryError


class BrowserSessionManager:
    """启动独立 Chrome，并持久化招聘平台登录状态。"""

    def __init__(
        self, executable_path: Path, profile_manager: BrowserProfileManager, headless: bool = False
    ) -> None:
        self.executable_path = executable_path
        self.profile_manager = profile_manager
        self.headless = headless
        self._processes: dict[str, subprocess.Popen[bytes]] = {}
        self._sessions: dict[str, BrowserSession] = {}

    def acquire(self, account_id: str, provider: str, account_name: str, purpose: str) -> BrowserSession:
        """启动一个独立浏览器会话。"""
        if not self.executable_path.exists():
            raise ProviderTemporaryError(f"Chrome 不存在：{self.executable_path}")
        profile = self.profile_manager.profile_path(provider, account_name)
        self.profile_manager.cleanup_singletons(profile)
        session_id = uuid4().hex
        self.profile_manager.acquire_lock(profile, session_id)
        port = _free_port()
        args = [
            str(self.executable_path),
            f"--user-data-dir={profile}",
            f"--remote-debugging-port={port}",
            "--no-first-run",
            "--no-default-browser-check",
        ]
        if self.headless:
            args.append("--headless=new")
        try:
            process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as exc:
            self.profile_manager.release_lock(profile)
            raise ProviderTemporaryError(f"Chrome 启动失败：{exc}") from exc
        now = datetime.now(timezone.utc)
        session = BrowserSession(
            session_id=session_id,
            account_id=account_id,
            browser_profile_path=profile,
            cdp_port=port,
            process_id=process.pid,
            started_at=now,
            last_heartbeat_at=now,
            purpose=purpose,
        )
        self._processes[session_id] = process
        self._sessions[session_id] = session
        return session

    def heartbeat(self, session_id: str) -> None:
        """更新会话心跳。"""
        session = self._sessions.get(session_id)
        if session is None:
            raise NotFoundError(f"浏览器会话不存在：{session_id}")
        session.last_heartbeat_at = datetime.now(timezone.utc)

    def release(self, session_id: str) -> None:
        """关闭浏览器并释放 Profile。"""
        session = self._sessions.pop(session_id, None)
        process = self._processes.pop(session_id, None)
        if session is None:
            return
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        self.profile_manager.release_lock(session.browser_profile_path)
        self.profile_manager.cleanup_singletons(session.browser_profile_path)

    def cleanup_dead(self) -> int:
        """清理已经退出的 Chrome 进程和锁。"""
        dead = [key for key, process in self._processes.items() if process.poll() is not None]
        for session_id in dead:
            session = self._sessions.pop(session_id, None)
            self._processes.pop(session_id, None)
            if session is not None:
                self.profile_manager.release_lock(session.browser_profile_path)
                self.profile_manager.cleanup_singletons(session.browser_profile_path)
        return len(dead)


def _free_port() -> int:
    """向操作系统申请空闲本地端口。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
