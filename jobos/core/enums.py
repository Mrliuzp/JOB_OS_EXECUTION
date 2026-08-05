"""跨领域使用的枚举。"""

from enum import StrEnum


class AutomationLevel(StrEnum):
    """自动化等级。"""

    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class Sensitivity(StrEnum):
    """候选人事实敏感等级。"""

    PUBLIC = "public"
    NORMAL = "normal"
    PRIVATE = "private"
    RESTRICTED = "restricted"


class JobStatus(StrEnum):
    """职位状态。"""

    DISCOVERED = "discovered"
    ENRICHED = "enriched"
    FILTERED = "filtered"
    ELIGIBLE = "eligible"
    SCORED = "scored"
    ARCHIVED = "archived"
    EXPIRED = "expired"


class ApplicationStatus(StrEnum):
    """申请状态。"""

    PLANNED = "planned"
    MATERIALS_READY = "materials_ready"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    COMMUNICATING = "communicating"
    SUBMITTED = "submitted"
    VIEWED = "viewed"
    REJECTED = "rejected"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    ACCEPTED = "accepted"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    FAILED = "failed"
    MANUAL_REQUIRED = "manual_required"


class TaskStatus(StrEnum):
    """工作流任务状态。"""

    PENDING = "pending"
    LEASED = "leased"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    RETRY_WAIT = "retry_wait"
    FAILED = "failed"
    CANCELLED = "cancelled"
    MANUAL_REQUIRED = "manual_required"


class MessageType(StrEnum):
    """HR 消息类型。"""

    GREETING = "greeting"
    RESUME_REQUEST = "resume_request"
    AVAILABILITY = "availability"
    EXPERIENCE_QUESTION = "experience_question"
    TECHNICAL_QUESTION = "technical_question"
    SALARY = "salary"
    INTERVIEW_SCHEDULE = "interview_schedule"
    OFFER = "offer"
    CONTRACT = "contract"
    PERSONAL_INFORMATION = "personal_information"
    REJECTION = "rejection"
    FOLLOW_UP = "follow_up"
    UNKNOWN = "unknown"


class RiskLevel(StrEnum):
    """消息风险等级。"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
