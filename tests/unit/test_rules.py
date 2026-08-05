"""规则引擎测试。"""

from jobos.rules.engine import RuleEngine
from jobos.rules.schemas import RuleContext


POLICIES = {
    "job_policy": {
        "accepted_employment_types": ["part_time"],
        "accepted_work_modes": ["remote"],
        "rejected_keywords": ["刷单"],
        "blocked_company_patterns": ["培训"],
        "score_thresholds": {"reject_below": 55, "review_below": 72, "auto_contact_above": 82},
    },
    "automation": {"daily_contact_limit": 15, "daily_application_limit": 8},
    "message_policy": {
        "auto_reply_types": ["availability"],
        "manual_review_types": ["salary"],
        "always_manual_types": ["offer", "contract"],
    },
}


def test_hard_reject_cannot_be_overridden_by_score() -> None:
    result = RuleEngine(POLICIES).evaluate_job(
        RuleContext(
            title="高薪刷单",
            company_name="示例",
            description="远程兼职",
            employment_type="part_time",
            work_mode="remote",
            ai_score=99,
        )
    )
    assert result.hard_reject is True
    assert result.action == "reject"
    assert result.matched_rule_ids


def test_offer_message_is_always_manual() -> None:
    result = RuleEngine(POLICIES).evaluate_message(
        RuleContext(title="", company_name="", description="", message_type="offer", risk_level="critical")
    )
    assert result.action == "manual_required"
