"""Worker 心跳状态测试。"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import jobos.workflow.worker_status as worker_status_module
from jobos.workflow.worker_status import (
    read_worker_status,
    worker_heartbeat_path,
    write_worker_heartbeat,
)


def test_worker_heartbeat_reports_online(tmp_path: Path) -> None:
    """新鲜心跳应报告 Worker 在线。"""
    now = datetime(2026, 8, 6, 2, 0, tzinfo=UTC)
    path = worker_heartbeat_path(tmp_path)

    write_worker_heartbeat(path, "worker-test", "waiting", now=now)
    status = read_worker_status(path, 90, now=now + timedelta(seconds=30))

    assert status.online is True
    assert status.worker_id == "worker-test"
    assert status.status == "waiting"
    assert status.health_payload()["worker"] == "online"


def test_worker_heartbeat_reports_offline_when_stale(tmp_path: Path) -> None:
    """过期心跳应报告 Worker 离线。"""
    now = datetime(2026, 8, 6, 2, 0, tzinfo=UTC)
    path = worker_heartbeat_path(tmp_path)

    write_worker_heartbeat(path, "worker-test", "working", now=now)
    status = read_worker_status(path, 90, now=now + timedelta(seconds=91))

    assert status.online is False
    assert status.worker_id == "worker-test"
    assert status.status == "offline"


def test_missing_worker_heartbeat_reports_offline(tmp_path: Path) -> None:
    """不存在心跳文件时应报告离线。"""
    status = read_worker_status(worker_heartbeat_path(tmp_path), 90)

    assert status.online is False
    assert status.worker_id == "unknown"
    assert status.status == "offline"


def test_worker_heartbeat_retries_when_target_is_temporarily_locked(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Windows 短暂锁定目标文件时应重试并完成写入。"""
    path = worker_heartbeat_path(tmp_path)
    original_replace = worker_status_module.os.replace
    replace_calls = 0

    def replace_with_temporary_lock(source: Path, target: Path) -> None:
        nonlocal replace_calls
        replace_calls += 1
        if replace_calls < 3:
            raise PermissionError(32, "文件正在被占用")
        original_replace(source, target)

    monkeypatch.setattr(worker_status_module.os, "replace", replace_with_temporary_lock)
    monkeypatch.setattr(worker_status_module.time, "sleep", lambda _seconds: None)

    write_worker_heartbeat(path, "worker-retry", "waiting")
    status = read_worker_status(path, 90)

    assert replace_calls == 3
    assert status.worker_id == "worker-retry"
    assert status.online is True
    assert list(tmp_path.glob("*.tmp")) == []
