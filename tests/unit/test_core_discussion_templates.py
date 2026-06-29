import pytest

from src.lib.discussions import discussion_templates


class TestBuildChatMessages:
    def test_includes_system_prompt_when_provided(self):
        existing_content = ""
        system_prompt = "You are a helpful assistant."
        current_prompt = "Hello"

        result = discussion_templates.build_chat_messages(
            existing_content, system_prompt, current_prompt
        )

        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "You are a helpful assistant."
        assert result[1]["role"] == "user"
        assert result[1]["content"] == "Hello"

    def test_excludes_empty_system_prompt(self):
        existing_content = ""
        system_prompt = "   "
        current_prompt = "Hello"

        result = discussion_templates.build_chat_messages(
            existing_content, system_prompt, current_prompt
        )

        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello"

    def test_parses_existing_conversation(self):
        existing_content = "User: Hi there\nAssistant: Hello!\nUser: How are you?"
        system_prompt = ""
        current_prompt = "I'm fine"

        result = discussion_templates.build_chat_messages(
            existing_content, system_prompt, current_prompt
        )

        assert len(result) == 4
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hi there"
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] == "Hello!"
        assert result[2]["role"] == "user"
        assert result[2]["content"] == "How are you?"
        assert result[3]["role"] == "user"
        assert result[3]["content"] == "I'm fine"

    def test_strips_system_prompt(self):
        existing_content = ""
        system_prompt = "  You are a helpful assistant.  "
        current_prompt = "Hello"

        result = discussion_templates.build_chat_messages(
            existing_content, system_prompt, current_prompt
        )

        assert result[0]["content"] == "You are a helpful assistant."


class TestParseConversationMessages:
    def test_parses_user_and_assistant_messages(self):
        content = "User: Hello\nAssistant: Hi there"
        result = discussion_templates.parse_conversation_messages(content)

        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello"
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] == "Hi there"

    def test_returns_empty_list_for_empty_content(self):
        result = discussion_templates.parse_conversation_messages("")
        assert result == []

    def test_returns_empty_list_when_no_matches(self):
        content = "This is just regular text without role prefixes."
        result = discussion_templates.parse_conversation_messages(content)
        assert result == []

    def test_handles_multiline_content(self):
        content = """User: First message
Assistant: First response
User: Second message
Assistant: Second response"""
        result = discussion_templates.parse_conversation_messages(content)

        assert len(result) == 4
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "First message"
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] == "First response"
        assert result[2]["role"] == "user"
        assert result[2]["content"] == "Second message"
        assert result[3]["role"] == "assistant"
        assert result[3]["content"] == "Second response"

    def test_strips_whitespace_from_content(self):
        content = "User:   Hello   \nAssistant:   Hi there   "
        result = discussion_templates.parse_conversation_messages(content)

        assert result[0]["content"] == "Hello"
        assert result[1]["content"] == "Hi there"

    def test_skips_empty_messages(self):
        content = "User: Hello\nAssistant:\nUser: World"
        result = discussion_templates.parse_conversation_messages(content)

        assert len(result) == 2
        assert result[0]["content"] == "Hello"
        assert result[1]["content"] == "World"

    def test_handles_multiple_spaces_after_colon(self):
        content = "User:  Hello\nAssistant:  Hi there"
        result = discussion_templates.parse_conversation_messages(content)

        assert len(result) == 2
        assert result[0]["content"] == "Hello"
        assert result[1]["content"] == "Hi there"

    def test_handles_no_space_after_colon(self):
        content = "User:Hello\nAssistant:Hi"
        result = discussion_templates.parse_conversation_messages(content)

        assert len(result) == 2
        assert result[0]["content"] == "Hello"
        assert result[1]["content"] == "Hi"

    def test_handles_conversation_with_only_user(self):
        content = "User: Hello\nUser: World"
        result = discussion_templates.parse_conversation_messages(content)

        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello"
        assert result[1]["role"] == "user"
        assert result[1]["content"] == "World"

    def test_handles_conversation_with_only_assistant(self):
        content = "Assistant: Hello\nAssistant: World"
        result = discussion_templates.parse_conversation_messages(content)

        assert len(result) == 2
        assert result[0]["role"] == "assistant"
        assert result[0]["content"] == "Hello"
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] == "World"

    def test_handles_mixed_case_role_prefixes(self):
        content = "User: Hello\nAssistant: Hi"
        result = discussion_templates.parse_conversation_messages(content)

        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"

    def test_handles_content_with_special_characters(self):
        content = "User: Hello! How are you?\nAssistant: I'm fine, thanks."
        result = discussion_templates.parse_conversation_messages(content)

        assert len(result) == 2
        assert result[0]["content"] == "Hello! How are you?"
        assert result[1]["content"] == "I'm fine, thanks."

    def test_parses_named_agent_turns(self):
        content = "Agent (Alpha): Hello everyone\nAgent (Beta): Hi Alpha"
        result = discussion_templates.parse_conversation_messages(content)

        assert len(result) == 2
        assert result[0]["role"] == "assistant"
        assert result[0]["content"] == "Alpha: Hello everyone"
        assert result[1]["content"] == "Beta: Hi Alpha"

    def test_strips_hidden_metadata_comments_from_message_text(self):
        content = """Assistant: Here is the answer.

<!-- apmatia-metadata: {"llama_server_status": {"total_tokens": 1559}} -->

User: Thanks"""
        result = discussion_templates.parse_conversation_messages(content)

        assert len(result) == 2
        assert result[0]["content"] == "Here is the answer."
        assert result[1]["content"] == "Thanks"
