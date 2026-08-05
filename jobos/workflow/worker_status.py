"""Worker 本地心跳状态读写。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WorkerStatus:
    """Worker 最近一次可观测状态。"""

    worker_id: str
    status: str
    last_seen_at: datetime | None
    online: bool

    def websocket_payload(self) -> dict[str, str | bool]:
        """返回 WebSocket 状态载荷。"""
        return {
            "worker": self.worker_id,
            "status": self.status,
            "online": self.online,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else "",
        }

    def health_payload(self) -> dict[str, str]:
        """返回系统健康检查字段。"""
        return {
            "worker": "online" if self.online else "offline",
            "worker_id": self.worker_id,
            "worker_status": self.status,
            "worker_last_seen": self.last_seen_at.isoformat() if self.last_seen_at else "",
        }


def worker_heartbeat_path(data_dir: Path) -> Path:
    """返回 Worker 心跳文件路径。"""
    return data_dir / "worker-heartbeat.json"


def write_worker_heartbeat(
    path: Path,
    worker_id: str,
    status: str,
    *,
    now: datetime | None = None,
) -> None:
    """原子写入 Worker 心跳。"""
    observed_at = now or datetime.now(UTC)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=UTC)
    payload = {
        "worker_id": worker_id,
        "status": status,
        "last_seen_at": observed_at.astimezone(UTC).isoformat(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    temporary_path.replace(path)


def read_worker_status(
    path: Path,
    stale_after_seconds: float,
    *,
    now: datetime | None = None,
) -> WorkerStatus:
    """读取心跳并根据时间判断 Worker 是否在线。"""
    if not path.is_file():
        return WorkerStatus("unknown", "offline", None, False)

    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("心跳内容必须是对象")
        worker_id = raw.get("worker_id")
        status = raw.get("status")
        last_seen_text = raw.get("last_seen_at")
        if not isinstance(worker_id, str) or not worker_id:
            raise ValueError("缺少 worker_id")
        if not isinstance(status, str) or not status:
            raise ValueError("缺少 status")
        if not isinstance(last_seen_text, str) or not last_seen_text:
            raise ValueError("缺少 last_seen_at")
        last_seen_at = datetime.fromisoformat(last_seen_text)
        if last_seen_at.tzinfo is None:
            last_seen_at = last_seen_at.replace(tzinfo=UTC)
    except (OSError, ValueError, json.JSONDecodeError):
        return WorkerStatus("unknown", "unknown", None, False)

    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)
    age_seconds = (current_time.astimezone(UTC) - last_seen_at.astimezone(UTC)).total_seconds()
    online = age_seconds <= stale_after_seconds
    return WorkerStatus(
        worker_id=worker_id,
        status=status if online else "offline",
        last_seen_at=last_seen_at,
        online=online,
    )
