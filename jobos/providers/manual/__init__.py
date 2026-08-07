"""手动导入 Provider 骨架。"""

from jobos.providers.skeleton import SkeletonProvider


class ManualProvider(SkeletonProvider):
    """手动导入接口骨架。"""

    def __init__(self) -> None:
        super().__init__("manual")
