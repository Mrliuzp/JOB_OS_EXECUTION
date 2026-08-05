"""确定性职位与消息规则引擎。"""

from __future__ import annotations

from typing import Any

from jobos.rules.schemas import RuleContext, RuleDecision


class RuleEngine:
    """硬规则优先于 AI 分数的规则引擎。"""

    def __init__(self, policies: dict[str, Any]) -> None:
        self.policies = policies

    def evaluate_job(self, context: RuleContext) -> RuleDecision:
        """评估职位是否允许进入评分或自动沟通。"""
        policy = self.policies.get("job_policy", {})
        automation = self.policies.get("automation", {})
        text = f"{context.title} {context.company_name} {context.description}".lower()
        matched: list[str] = []
        reasons: list[str] = []

        for keyword in policy.get("rejected_keywords", []):
            if str(keyword).lower() in text:
                matched.append(f"job.rejected_keyword.{keyword}")
                reasons.append(f"命中拒绝关键词：{keyword}")
        for company in policy.get("blocked_companies", []):
            if str(company).lower() == context.company_name.lower():
                matched.append(f"job.blocked_company.{company}")
                reasons.append(f"公司在屏蔽名单中：{company}")
        for pattern in policy.get("blocked_company_patterns", []):
            if str(pattern).lower() in context.company_name.lower():
                matched.append(f"job.blocked_company_pattern.{pattern}")
                reasons.append(f"公司名称命中屏蔽模式：{pattern}")
        accepted_types = [str(item) for item in policy.get("accepted_employment_types", [])]
        if accepted_types and context.employment_type not in accepted_types:
            matched.append("job.employment_type_not_accepted")
            reasons.append(f"职位类型不符合兼职策略：{context.employment_type}")
        accepted_modes = [str(item) for item in policy.get("accepted_work_modes", [])]
        if accepted_modes and context.work_mode not in [*accepted_modes, "unknown"]:
            matched.append("job.work_mode_not_accepted")
            reasons.append(f"工作方式不符合策略：{context.work_mode}")
        if matched:
            return RuleDecision(
                action="reject", matched_rule_ids=matched, reasons=reasons, hard_reject=True
            )

        contact_limit = int(automation.get("daily_contact_limit", 15))
        application_limit = int(automation.get("daily_application_limit", 8))
        if context.daily_contact_count >= contact_limit:
            return RuleDecision(
                action="review",
                matched_rule_ids=["platform.daily_contact_limit"],
                reasons=["已达到每日沟通上限"],
            )
        if context.daily_application_count >= application_limit:
            return RuleDecision(
                action="review",
                matched_rule_ids=["platform.daily_application_limit"],
                reasons=["已达到每日投递上限"],
            )

        thresholds = policy.get("score_thresholds", {})
        if context.ai_score is None:
            return RuleDecision(action="allow", reasons=["硬规则通过，等待 AI 评分"])
        reject_below = float(thresholds.get("reject_below", 55))
        review_below = float(thresholds.get("review_below", 72))
        auto_above = float(thresholds.get("auto_contact_above", 82))
        if context.ai_score < reject_below:
            return RuleDecision(
                action="reject",
                matched_rule_ids=["score.reject_below"],
                reasons=[f"匹配分低于 {reject_below}"],
            )
        if context.ai_score < review_below:
            return RuleDecision(
                action="review",
                matched_rule_ids=["score.review_below"],
                reasons=[f"匹配分低于人工复核阈值 {review_below}"],
            )
        if context.ai_score >= auto_above:
            return RuleDecision(
                action="auto_contact",
                matched_rule_ids=["score.auto_contact_above"],
                reasons=[f"匹配分达到自动沟通阈值 {auto_above}"],
            )
        return RuleDecision(action="allow", reasons=["规则和评分均通过"])

    def evaluate_message(self, context: RuleContext) -> RuleDecision:
        """判断消息是否必须人工审批。"""
        policy = self.policies.get("message_policy", {})
        message_type = context.message_type or "unknown"
        if message_type in set(policy.get("always_manual_types", [])):
            return RuleDecision(
                action="manual_required",
                matched_rule_ids=[f"message.always_manual.{message_type}"],
                reasons=["该消息类型必须人工处理"],
            )
        if message_type in set(policy.get("manual_review_types", [])):
            return RuleDecision(
                action="review",
                matched_rule_ids=[f"message.manual_review.{message_type}"],
                reasons=["该消息类型需要人工复核"],
            )
        if context.risk_level in {"high", "critical"}:
            return RuleDecision(
                action="manual_required",
                matched_rule_ids=["message.high_risk"],
                reasons=["消息风险等级过高"],
            )
        if message_type in set(policy.get("auto_reply_types", [])):
            return RuleDecision(
                action="allow",
                matched_rule_ids=[f"message.auto_reply.{message_type}"],
                reasons=["低风险消息允许自动回复"],
            )
        return RuleDecision(action="review", reasons=["未知消息默认人工复核"])
