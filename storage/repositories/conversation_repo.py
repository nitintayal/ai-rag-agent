"""Conversation repository — dispatches to the active backend."""

from storage.factory import get_backend


def create_conversation(user_id, title=None, conversation_id=None):
    return get_backend().conversation.create_conversation(user_id, title, conversation_id)

def get_conversation(conversation_id):
    return get_backend().conversation.get_conversation(conversation_id)

def list_conversations(user_id, limit=20, offset=0):
    return get_backend().conversation.list_conversations(user_id, limit, offset)

def add_message(conversation_id, role, content, tool_name=None, tool_result=None):
    return get_backend().conversation.add_message(conversation_id, role, content, tool_name, tool_result)

def get_messages(conversation_id, limit=20):
    return get_backend().conversation.get_messages(conversation_id, limit)
