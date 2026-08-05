"""BOSS 会话和消息解析测试。"""

from jobos.providers.boss.parser import parse_conversations, parse_messages


def test_parse_conversations_and_messages() -> None:
    conversations = parse_conversations(
        '<div data-conversation-id="c1" data-job-id="j1" data-unread-count="2">'
        '<span data-role="recruiter">张 HR</span>'
        '<span data-role="company">示例科技</span></div>'
    )
    assert conversations.items[0].unread_count == 2
    messages = parse_messages(
        '<div data-message-id="m1" data-direction="inbound" '
        'data-sender-type="recruiter">每周可投入多少时间？</div>'
    )
    assert messages.items[0].content == "每周可投入多少时间？"
