"""领域异常定义。"""


class JobOSError(Exception):
    """JobOS 所有可预期异常的基类。"""


class ConfigurationError(JobOSError):
    """配置无效。"""


class InvalidStateTransitionError(JobOSError):
    """状态迁移不合法。"""


class NotFoundError(JobOSError):
    """资源不存在。"""


class ConflictError(JobOSError):
    """资源发生幂等或唯一性冲突。"""


class ApprovalRequiredError(JobOSError):
    """操作需要人工审批。"""


class EvidenceValidationError(JobOSError):
    """生成内容无法通过事实校验。"""


class LLMError(JobOSError):
    """大模型调用失败。"""


class LLMConfigurationError(LLMError):
    """大模型未配置。"""


class LLMResponseValidationError(LLMError):
    """大模型结构化输出无效。"""


class ProviderError(JobOSError):
    """招聘平台 Provider 异常。"""


class ProviderLoginRequired(ProviderError):
    """需要用户手动登录。"""


class ProviderSessionExpired(ProviderError):
    """平台会话已过期。"""


class ProviderRateLimited(ProviderError):
    """平台触发限流。"""


class ProviderPageChanged(ProviderError):
    """平台页面结构发生变化。"""


class ProviderJobExpired(ProviderError):
    """职位已过期。"""


class ProviderPermissionDenied(ProviderError):
    """平台拒绝当前操作。"""


class ProviderCaptchaDetected(ProviderError):
    """检测到验证码或风控页面。"""


class ProviderActionRejected(ProviderError):
    """平台未接受动作。"""


class ProviderTemporaryError(ProviderError):
    """可重试的平台临时错误。"""


class ProviderPermanentError(ProviderError):
    """不可重试的平台永久错误。"""


class CapabilityNotSupported(ProviderError):
    """Provider 不支持当前能力。"""
