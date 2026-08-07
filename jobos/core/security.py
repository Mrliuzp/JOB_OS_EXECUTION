"""隐私数据脱敏工具。"""

import re
from typing import Any

_REDACTED = "***已脱敏***"
_SECRET_KEYS = ("key", "secret", "token", "password", "cookie", "authorization")
_PHONE = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_ID_CARD = re.compile(r"(?<!\d)\d{17}[0-9Xx](?!\d)")


def redact_text(value: str) -> str:
    """脱敏手机号、邮箱和身份证号。"""
    value = _PHONE.sub("1**********", value)
    value = _EMAIL.sub(_REDACTED, value)
    return _ID_CARD.sub(_REDACTED, value)


def redact_mapping(value: Any) -> Any:
    """递归脱敏配置或日志字典。"""
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            if any(marker in key.lower() for marker in _SECRET_KEYS):
                result[key] = _REDACTED
            else:
                result[key] = redact_mapping(raw_value)
        return result
    if isinstance(value, list):
        return [redact_mapping(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_mapping(item) for item in value)
    if isinstance(value, str):
        return redact_text(value)
    return value
