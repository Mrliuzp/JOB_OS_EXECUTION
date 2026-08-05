import pytest

from apps.worker.main import main


def test_worker_entry_point_runs(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    captured = capsys.readouterr()

    assert "worker.bootstrap" in captured.out
    assert '"status": "ok"' in captured.out
