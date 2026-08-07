"""JobOS 分域配置模型与加载器。"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator

from jobos.core.enums import AutomationLevel
from jobos.core.errors import ConfigurationError
from jobos.core.security import redact_mapping

_ENV_PATTERN = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")


class AppSettings(BaseModel):
    """应用基础设置。"""

    name: str = "JobOS-CN"
    environment: str = "development"
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".jobos")
    timezone: str = "Asia/Shanghai"
    language: str = "zh-CN"
    automation_level: AutomationLevel = AutomationLevel.L1

    @field_validator("data_dir", mode="before")
    @classmethod
    def normalize_data_dir(cls, value: object) -> Path:
        """展开用户目录，同时保留 Windows 盘符文本。"""
        if isinstance(value, Path):
            return value.expanduser()
        if not isinstance(value, str):
            raise ValueError("data_dir 必须是路径字符串")
        expanded = os.path.expandvars(os.path.expanduser(value))
        return Path(expanded)


class DatabaseSettings(BaseModel):
    """数据库设置。"""

    url: str = "sqlite:///~/.jobos/jobos.db"
    echo: bool = False
    wal: bool = True


class WorkerSettings(BaseModel):
    """任务 Worker 设置。"""

    concurrency: int = Field(default=2, ge=1, le=32)
    lease_seconds: int = Field(default=300, ge=30)
    heartbeat_seconds: int = Field(default=30, ge=5)


class BrowserSettings(BaseModel):
    """浏览器运行时设置。"""

    executable_path: Path | None = None
    headless: bool = False
    action_timeout_ms: int = Field(default=15000, ge=1000)
    page_timeout_ms: int = Field(default=45000, ge=1000)
    screenshot_on_error: bool = True
    profile_root: Path | None = None


class SecuritySettings(BaseModel):
    """安全和隐私设置。"""

    redact_logs: bool = True
    encrypt_secrets: bool = True
    local_only: bool = True


class LLMProviderSettings(BaseModel):
    """单个模型 Provider 设置。"""

    base_url: str | None = None
    api_key: SecretStr | None = None
    model: str | None = None
    timeout_seconds: int = Field(default=60, ge=1)


class LLMTaskSettings(BaseModel):
    """语义任务所使用的模型。"""

    provider: str
    model: str
    fallback_providers: list[str] = Field(default_factory=list)


class LLMSettings(BaseModel):
    """LLM 网关设置。"""

    default_provider: str = "openai"
    providers: dict[str, LLMProviderSettings] = Field(default_factory=dict)
    tasks: dict[str, LLMTaskSettings] = Field(default_factory=dict)


class ProviderAccountSettings(BaseModel):
    """招聘平台账号运行设置。"""

    enabled: bool = False
    account: str = "primary"
    max_concurrency: int = Field(default=1, ge=1, le=4)
    daily_action_limit: int = Field(default=30, ge=0)
    minimum_action_interval_seconds: int = Field(default=20, ge=0)


class PolicySettings(BaseModel):
    """规则配置原始载荷。"""

    model_config = ConfigDict(extra="allow")

    version: int = 1
    job_policy: dict[str, Any] = Field(default_factory=dict)
    automation: dict[str, Any] = Field(default_factory=lambda: {"level": "L1"})
    message_policy: dict[str, Any] = Field(default_factory=dict)


class JobOSSettings(BaseModel):
    """应用完整配置。"""

    model_config = ConfigDict(extra="forbid")

    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    worker: WorkerSettings = Field(default_factory=WorkerSettings)
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    providers: dict[str, ProviderAccountSettings] = Field(default_factory=dict)
    policies: PolicySettings = Field(default_factory=PolicySettings)
    prompts: dict[str, Any] = Field(default_factory=dict)

    def resolved_data_dir(self) -> Path:
        """返回已创建的用户数据目录。"""
        path = self.app.data_dir.expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def safe_dump(self) -> dict[str, Any]:
        """返回可安全写入日志的配置快照。"""
        raw = self.model_dump(mode="json")
        redacted = redact_mapping(raw)
        if not isinstance(redacted, dict):
            raise TypeError("配置快照必须是字典")
        return redacted


def _read_yaml(path: Path) -> dict[str, Any]:
    """读取 YAML；空文件按空字典处理。"""
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ConfigurationError(f"配置文件顶层必须是对象：{path}")
    return {str(key): value for key, value in loaded.items()}


def _resolve_env(value: Any) -> Any:
    """递归解析 `${ENV_NAME}` 占位符。"""
    if isinstance(value, dict):
        return {str(key): _resolve_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_env(item) for item in value]
    if isinstance(value, str):
        match = _ENV_PATTERN.match(value)
        if match:
            return os.environ.get(match.group(1))
    return value


def _deep_merge(target: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    """递归合并配置，后加载文件覆盖前者。"""
    result = dict(target)
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            existing = result[key]
            if isinstance(existing, dict):
                result[key] = _deep_merge(existing, value)
        else:
            result[key] = value
    return result


def _environment_overrides() -> dict[str, Any]:
    """读取常用环境变量覆盖项。"""
    result: dict[str, Any] = {}
    if data_dir := os.getenv("JOBOS_DATA_DIR"):
        result.setdefault("app", {})["data_dir"] = data_dir
    if database_url := os.getenv("JOBOS_DATABASE_URL"):
        result.setdefault("database", {})["url"] = database_url
    if level := os.getenv("JOBOS_AUTOMATION_LEVEL"):
        result.setdefault("app", {})["automation_level"] = level
    providers: dict[str, Any] = {}
    if key := os.getenv("OPENAI_API_KEY"):
        providers["openai"] = {"api_key": key, "base_url": os.getenv("OPENAI_BASE_URL")}
    if key := os.getenv("GEMINI_API_KEY"):
        providers["gemini"] = {"api_key": key}
    if url := os.getenv("LLM_URL"):
        providers["local"] = {"base_url": url, "api_key": os.getenv("LLM_API_KEY")}
    if providers:
        result.setdefault("llm", {})["providers"] = providers
    return result


def load_settings(config_dir: Path | None = None) -> JobOSSettings:
    """从分域 YAML 与环境变量加载配置。"""
    directory = config_dir or Path(os.getenv("JOBOS_CONFIG_DIR", "config"))
    merged: dict[str, Any] = {}
    file_map = (
        ("app", "app.yaml", "app.example.yaml", None),
        ("providers", "providers.yaml", "providers.example.yaml", "providers"),
        ("policies", "policies.yaml", "policies.example.yaml", None),
        ("prompts", "prompts.yaml", "prompts.example.yaml", "prompts"),
        ("llm", "llm.yaml", "llm.example.yaml", "llm"),
    )
    for section, primary, fallback, nested_key in file_map:
        path = directory / primary
        if not path.exists():
            path = directory / fallback
        data = _read_yaml(path)
        if nested_key and nested_key in data:
            section_data = data[nested_key]
            if not isinstance(section_data, dict):
                raise ConfigurationError(f"{path} 中的 {nested_key} 必须是对象")
            merged[section] = section_data
        elif section == "app":
            merged = _deep_merge(merged, data)
        else:
            merged[section] = data
    merged = _deep_merge(merged, _environment_overrides())
    try:
        return JobOSSettings.model_validate(_resolve_env(merged))
    except ValidationError as exc:
        raise ConfigurationError(str(exc)) from exc
