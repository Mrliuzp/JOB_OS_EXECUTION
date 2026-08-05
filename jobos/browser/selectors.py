"""YAML 选择器注册表。"""

from pathlib import Path
from typing import Any

import yaml


def load_selector_registry(path: Path) -> dict[str, Any]:
    """读取选择器配置。"""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"选择器配置无效：{path}")
    return {str(key): value for key, value in data.items()}
