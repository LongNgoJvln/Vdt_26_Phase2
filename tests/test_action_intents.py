from src.action_intents import message_needs_tools


def test_network_and_kubernetes_actions_promote_to_agent():
    assert message_needs_tools("prepare a Kubernetes change proposal for deployment api")
    assert message_needs_tools("list pods in the core namespace")
    assert message_needs_tools("lấy snapshot mạng trước khi thay đổi")


def test_report_document_and_knowledge_actions_promote_to_agent():
    assert message_needs_tools("create a report from the latest network snapshot")
    assert message_needs_tools("write a markdown runbook")
    assert message_needs_tools("ingest these 4G knowledge files")
    assert message_needs_tools("open my documents")


def test_removed_personal_assistant_actions_stay_plain_chat():
    assert not message_needs_tools("Can you add an entry to my calendar?")
    assert not message_needs_tools("reply to that email")
    assert not message_needs_tools("set a reminder to call Pat at 4pm")
    assert not message_needs_tools("research cost effective local models")


def test_explanatory_network_questions_stay_plain_chat():
    assert not message_needs_tools("explain what a Kubernetes change proposal is")
    assert not message_needs_tools("giải thích network change là gì")

