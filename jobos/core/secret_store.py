"""本地密钥存储抽象。"""

from __future__ import annotations

import os
from typing import Protocol


class SecretStore(Protocol):
    """密钥存储协议。"""

    def get(self, name: str) -> str | None: ...
    def set(self, name: str, value: str) -> None: ...
    def delete(self, name: str) -> None: ...


class EnvironmentSecretStore:
    """开发环境使用的只读环境变量存储。"""

    def get(self, name: str) -> str | None:
        return os.getenv(name)

    def set(self, name: str, value: str) -> None:
        raise PermissionError("环境变量密钥存储不支持运行时写入")

    def delete(self, name: str) -> None:
        raise PermissionError("环境变量密钥存储不支持运行时删除")


class KeyringSecretStore:
    """使用系统凭据管理器保存密钥。"""

    def __init__(self, service_name: str = "JobOS-CN") -> None:
        self.service_name = service_name

    def get(self, name: str) -> str | None:
        import keyring

        return keyring.get_password(self.service_name, name)

    def set(self, name: str, value: str) -> None:
        import keyring

        keyring.set_password(self.service_name, name, value)

    def delete(self, name: str) -> None:
        import keyring

        try:
            keyring.delete_password(self.service_name, name)
        except keyring.errors.PasswordDeleteError:
            return
