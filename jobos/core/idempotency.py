"""幂等键工具。"""

import hashlib
import json
from collections.abc import Mapping
from typing import Any


def build_idempotency_key(namespace: str, payload: Mapping[str, Any]) -> str:
    """基于稳定 JSON 生成不可逆幂等键。"""
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return f"{namespace}:{digest}"
