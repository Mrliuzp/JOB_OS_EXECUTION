"""BOSS 页面离线解析器。"""

from __future__ import annotations

from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin

from jobos.core.errors import ProviderJobExpired, ProviderPageChanged
from jobos.domain.schemas import (
    ConversationPage,
    ExternalConversation,
    ExternalMessage,
    JobSearchItem,
    JobSearchPage,
    MessagePage,
    RawJobDetail,
)


class _NodeParser(HTMLParser):
    """保留标签、属性和文本的轻量 HTML 解析器。"""

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[dict[str, object]] = []
        self.nodes: list[dict[str, object]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node: dict[str, object] = {"tag": tag, "attrs": dict(attrs), "text": [], "children": []}
        if self.stack:
            children = self.stack[-1]["children"]
            if isinstance(children, list):
                children.append(node)
        else:
            self.nodes.append(node)
        self.stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if self.stack and data.strip():
            text = self.stack[-1]["text"]
            if isinstance(text, list):
                text.append(data.strip())


def _all_nodes(nodes: list[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for node in nodes:
        result.append(node)
        children = node.get("children", [])
        if isinstance(children, list):
            result.extend(_all_nodes(children))
    return result


def _text(node: dict[str, object]) -> str:
    parts: list[str] = []
    raw = node.get("text", [])
    if isinstance(raw, list):
        parts.extend(str(item) for item in raw)
    children = node.get("children", [])
    if isinstance(children, list):
        parts.extend(_text(child) for child in children if isinstance(child, dict))
    return " ".join(part for part in parts if part).strip()


def _attrs(node: dict[str, object]) -> dict[str, str | None]:
    raw = node.get("attrs", {})
    return raw if isinstance(raw, dict) else {}


def _has_class(node: dict[str, object], class_name: str) -> bool:
    classes = (_attrs(node).get("class") or "").split()
    return class_name in classes


def _role_text(nodes: list[dict[str, object]], role: str) -> str | None:
    target = next(
        (node for node in nodes if _attrs(node).get("data-role") == role),
        None,
    )
    return _text(target) if target else None


def parse_search_page(html: str, base_url: str = "https://www.zhipin.com") -> JobSearchPage:
    """解析职位列表 Fixture 或兼容页面。"""
    parser = _NodeParser()
    parser.feed(html)
    cards = [
        node
        for node in _all_nodes(parser.nodes)
        if _attrs(node).get("data-job-id") or _has_class(node, "job-card-wrapper")
    ]
    items: list[JobSearchItem] = []
    seen: set[str] = set()
    for card in cards:
        attrs = _attrs(card)
        job_id = attrs.get("data-job-id")
        descendants = _all_nodes([card])
        link = next(
            (node for node in descendants if node.get("tag") == "a" and _attrs(node).get("href")),
            None,
        )
        href = _attrs(link).get("href") if link else None
        if not job_id and href:
            job_id = str(href).rstrip("/").split("/")[-1].split(".")[0]
        if not job_id or job_id in seen:
            continue
        title_node = next(
            (
                node
                for node in descendants
                if _has_class(node, "job-name") or _attrs(node).get("data-role") == "job-title"
            ),
            link,
        )
        company_node = next(
            (
                node
                for node in descendants
                if _has_class(node, "company-name") or _attrs(node).get("data-role") == "company"
            ),
            None,
        )
        location_node = next(
            (
                node
                for node in descendants
                if _has_class(node, "job-area") or _attrs(node).get("data-role") == "location"
            ),
            None,
        )
        salary_node = next(
            (
                node
                for node in descendants
                if _has_class(node, "salary") or _attrs(node).get("data-role") == "salary"
            ),
            None,
        )
        title = _text(title_node) if title_node else ""
        company = _text(company_node) if company_node else ""
        if not title or not company or not href:
            continue
        seen.add(str(job_id))
        items.append(
            JobSearchItem(
                external_job_id=str(job_id),
                canonical_url=urljoin(base_url, str(href)),
                title=title,
                company_name=company,
                location=_text(location_node) if location_node else None,
                salary_text=_text(salary_node) if salary_node else None,
                job_card_text=_text(card),
            )
        )
    if not items:
        raise ProviderPageChanged("未从职位列表页面解析到职位卡片")
    return JobSearchPage(items=items)


def parse_job_detail(html: str, canonical_url: str) -> RawJobDetail:
    """解析职位详情页面。"""
    if any(marker in html for marker in ("职位已下线", "职位不存在", "该职位已关闭")):
        raise ProviderJobExpired("BOSS 职位已过期")
    parser = _NodeParser()
    parser.feed(html)
    nodes = _all_nodes(parser.nodes)

    def by_role(role: str) -> dict[str, object] | None:
        return next((node for node in nodes if _attrs(node).get("data-role") == role), None)

    title_node = by_role("job-title") or next(
        (node for node in nodes if _has_class(node, "name")),
        None,
    )
    company_node = by_role("company") or next(
        (node for node in nodes if _has_class(node, "company-info")),
        None,
    )
    description_node = by_role("description") or next(
        (node for node in nodes if _has_class(node, "job-sec-text")),
        None,
    )
    if not title_node or not company_node or not description_node:
        raise ProviderPageChanged("职位详情页缺少标题、公司或描述")
    root = next((node for node in nodes if _attrs(node).get("data-job-id")), None)
    root_attrs = _attrs(root) if root else {}
    external_id = str(
        root_attrs.get("data-job-id") or canonical_url.rstrip("/").split("/")[-1].split(".")[0]
    )
    requirements = [
        _text(node)
        for node in nodes
        if _attrs(node).get("data-role") == "requirement" and _text(node)
    ]
    benefits = [
        _text(node) for node in nodes if _attrs(node).get("data-role") == "benefit" and _text(node)
    ]
    work_mode = str(root_attrs.get("data-work-mode") or "unknown")
    employment_type = str(root_attrs.get("data-employment-type") or "unknown")
    return RawJobDetail(
        external_job_id=external_id,
        canonical_url=canonical_url,
        title=_text(title_node),
        company_name=_text(company_node),
        location=_text(by_role("location")) if by_role("location") else None,
        description=_text(description_node),
        requirements=requirements,
        benefits=benefits,
        work_mode=work_mode,
        employment_type=employment_type,
        expired=False,
    )


def parse_conversations(html: str) -> ConversationPage:
    """解析站内会话列表。"""
    parser = _NodeParser()
    parser.feed(html)
    items: list[ExternalConversation] = []
    for node in _all_nodes(parser.nodes):
        attrs = _attrs(node)
        conversation_id = attrs.get("data-conversation-id")
        if not conversation_id:
            continue
        descendants = _all_nodes([node])
        unread_raw = attrs.get("data-unread-count") or "0"
        time_raw = attrs.get("data-last-message-at")
        items.append(
            ExternalConversation(
                external_conversation_id=str(conversation_id),
                external_job_id=attrs.get("data-job-id"),
                recruiter_name=_role_text(descendants, "recruiter"),
                recruiter_company=_role_text(descendants, "company"),
                unread_count=int(str(unread_raw)),
                last_message_at=datetime.fromisoformat(str(time_raw)) if time_raw else None,
            )
        )
    if not items and "暂无沟通" not in html:
        raise ProviderPageChanged("未从会话页面解析到会话项")
    return ConversationPage(items=items)


def parse_messages(html: str) -> MessagePage:
    """解析会话消息列表。"""
    parser = _NodeParser()
    parser.feed(html)
    items: list[ExternalMessage] = []
    for node in _all_nodes(parser.nodes):
        attrs = _attrs(node)
        message_id = attrs.get("data-message-id")
        if not message_id:
            continue
        direction = str(attrs.get("data-direction") or "inbound")
        if direction not in {"inbound", "outbound"}:
            direction = "inbound"
        time_raw = attrs.get("data-sent-at")
        items.append(
            ExternalMessage(
                external_message_id=str(message_id),
                direction=direction,
                sender_type=str(attrs.get("data-sender-type") or "recruiter"),
                content=_text(node),
                sent_at=datetime.fromisoformat(str(time_raw)) if time_raw else None,
            )
        )
    if not items and "暂无消息" not in html:
        raise ProviderPageChanged("未从会话页面解析到消息")
    return MessagePage(items=items)
