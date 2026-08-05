"""Provider 注册表。"""

from jobos.core.errors import NotFoundError
from jobos.providers.base import ProviderAdapter


class ProviderRegistry:
    """按名称管理 Provider。"""

    def __init__(self) -> None:
        self._providers: dict[str, ProviderAdapter] = {}

    def register(self, provider: ProviderAdapter) -> None:
        """注册或替换 Provider。"""
        self._providers[provider.name] = provider

    def get(self, name: str) -> ProviderAdapter:
        """获取 Provider。"""
        provider = self._providers.get(name)
        if provider is None:
            raise NotFoundError(f"Provider 未注册：{name}")
        return provider

    def list(self) -> list[ProviderAdapter]:
        """按名称返回 Provider。"""
        return [self._providers[name] for name in sorted(self._providers)]
