"""智联招聘 Provider 骨架。"""

from jobos.providers.skeleton import SkeletonProvider


class ZhaopinProvider(SkeletonProvider):
    """智联招聘接口骨架。"""

    def __init__(self) -> None:
        super().__init__("zhaopin")
