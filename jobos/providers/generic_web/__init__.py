"""企业招聘官网 Provider 骨架。"""

from jobos.providers.skeleton import SkeletonProvider


class GenericWebProvider(SkeletonProvider):
    """通用网页接口骨架。"""

    def __init__(self) -> None:
        super().__init__("generic_web")
