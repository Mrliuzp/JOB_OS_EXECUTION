"""猎聘 Provider 骨架。"""

from jobos.providers.skeleton import SkeletonProvider


class LiepinProvider(SkeletonProvider):
    """猎聘接口骨架。"""

    def __init__(self) -> None:
        super().__init__("liepin")
