"""拉勾 Provider 骨架。"""

from jobos.providers.skeleton import SkeletonProvider


class LagouProvider(SkeletonProvider):
    """拉勾接口骨架。"""

    def __init__(self) -> None:
        super().__init__("lagou")
