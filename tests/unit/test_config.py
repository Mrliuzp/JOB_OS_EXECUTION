"""配置系统测试。"""

from pathlib import Path

import pytest

from jobos.core.config import load_settings
from jobos.core.errors import ConfigurationError


def _write_config(directory: Path, app: str) -> None:
    directory.mkdir()
    (directory / "app.yaml").write_text(app, encoding="utf-8")
    (directory / "providers.example.yaml").write_text("providers: {}", encoding="utf-8")
    (directory / "policies.example.yaml").write_text("version: 1", encoding="utf-8")
    (directory / "prompts.example.yaml").write_text("prompts: {}", encoding="utf-8")
    (directory / "llm.example.yaml").write_text("llm: {}", encoding="utf-8")


def test_load_settings_and_redact_secret(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "config"
    _write_config(
        config,
        "app:\n  name: JobOS-CN\n  data_dir: 'C:\\JobOS\\data'\nllm:\n  providers:\n    openai:\n      api_key: ${OPENAI_API_KEY}\n",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "secret-value")
    settings = load_settings(config)
    assert str(settings.app.data_dir) == r"C:\JobOS\data"
    assert settings.llm.providers["openai"].api_key is not None
    assert "secret-value" not in str(settings.safe_dump())


def test_invalid_settings_reports_field(tmp_path: Path) -> None:
    config = tmp_path / "config"
    _write_config(config, "worker:\n  concurrency: 0\n")
    with pytest.raises(ConfigurationError, match="concurrency"):
        load_settings(config)
