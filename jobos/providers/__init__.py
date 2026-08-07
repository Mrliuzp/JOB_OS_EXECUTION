"""招聘平台 Provider 公共接口。"""

from jobos.providers.base import ProviderAdapter, ProviderCapabilities
from jobos.providers.registry import ProviderRegistry

__all__ = ["ProviderAdapter", "ProviderCapabilities", "ProviderRegistry"]
