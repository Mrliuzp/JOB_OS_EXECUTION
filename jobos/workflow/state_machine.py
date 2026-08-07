"""职位、申请和消息状态机。"""

from jobos.core.enums import ApplicationStatus, JobStatus
from jobos.core.errors import InvalidStateTransitionError

_JOB_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.DISCOVERED: {JobStatus.ENRICHED, JobStatus.ARCHIVED, JobStatus.EXPIRED},
    JobStatus.ENRICHED: {JobStatus.FILTERED, JobStatus.ARCHIVED, JobStatus.EXPIRED},
    JobStatus.FILTERED: {JobStatus.ELIGIBLE, JobStatus.ARCHIVED},
    JobStatus.ELIGIBLE: {JobStatus.SCORED, JobStatus.ARCHIVED},
    JobStatus.SCORED: {JobStatus.ARCHIVED, JobStatus.EXPIRED},
    JobStatus.ARCHIVED: set(),
    JobStatus.EXPIRED: set(),
}

_APPLICATION_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.PLANNED: {
        ApplicationStatus.MATERIALS_READY,
        ApplicationStatus.FAILED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.MANUAL_REQUIRED,
    },
    ApplicationStatus.MATERIALS_READY: {
        ApplicationStatus.AWAITING_APPROVAL,
        ApplicationStatus.APPROVED,
        ApplicationStatus.FAILED,
        ApplicationStatus.MANUAL_REQUIRED,
    },
    ApplicationStatus.AWAITING_APPROVAL: {
        ApplicationStatus.APPROVED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.MANUAL_REQUIRED,
    },
    ApplicationStatus.APPROVED: {
        ApplicationStatus.COMMUNICATING,
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.FAILED,
        ApplicationStatus.MANUAL_REQUIRED,
    },
    ApplicationStatus.COMMUNICATING: {
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.FAILED,
        ApplicationStatus.MANUAL_REQUIRED,
    },
    ApplicationStatus.SUBMITTED: {
        ApplicationStatus.VIEWED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.INTERVIEWING,
        ApplicationStatus.EXPIRED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.VIEWED: {
        ApplicationStatus.REJECTED,
        ApplicationStatus.INTERVIEWING,
        ApplicationStatus.EXPIRED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.INTERVIEWING: {
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.OFFER: {
        ApplicationStatus.ACCEPTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.FAILED: {ApplicationStatus.PLANNED, ApplicationStatus.MANUAL_REQUIRED},
    ApplicationStatus.REJECTED: set(),
    ApplicationStatus.ACCEPTED: set(),
    ApplicationStatus.WITHDRAWN: set(),
    ApplicationStatus.EXPIRED: set(),
    ApplicationStatus.MANUAL_REQUIRED: {ApplicationStatus.PLANNED, ApplicationStatus.APPROVED},
}


def transition_job(current: str, target: str) -> JobStatus:
    """验证并返回职位目标状态。"""
    current_status = JobStatus(current)
    target_status = JobStatus(target)
    if target_status not in _JOB_TRANSITIONS[current_status]:
        raise InvalidStateTransitionError(f"职位状态不能从 {current} 迁移到 {target}")
    return target_status


def transition_application(current: str, target: str) -> ApplicationStatus:
    """验证并返回申请目标状态。"""
    current_status = ApplicationStatus(current)
    target_status = ApplicationStatus(target)
    if target_status not in _APPLICATION_TRANSITIONS[current_status]:
        raise InvalidStateTransitionError(f"申请状态不能从 {current} 迁移到 {target}")
    return target_status
