"""Worker 入口测试。"""

import json

import pytest

from apps.worker.main import main


def test_worker_entry_point_runs(capsys: pytest.CaptureFixture[str]) -> None:
    """单次模式应启动 Worker 并正常退出。"""
    main(["--once"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload["event"] == "worker.started"
    assert payload["worker_id"]
