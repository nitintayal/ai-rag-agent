import unittest
from unittest.mock import patch

from agent.deep_agent import _message_text, _tool_payload


class DeepAgentHelpersTest(unittest.TestCase):
    def test_tool_payload_serializes_sources(self):
        payload = _tool_payload({"context": "result", "sources": ["doc.pdf"]})
        self.assertIn('"doc.pdf"', payload)

    def test_message_text_handles_text_blocks(self):
        message = type(
            "Message",
            (),
            {"content": [{"type": "text", "text": "first"}, {"type": "text", "text": "second"}]},
        )()
        self.assertEqual(_message_text(message), "first\nsecond")

    @patch("agent.deep_agent.run_deep_agent")
    @patch("agent.agent_executor.settings.AGENT_MODE", "deep")
    def test_executor_selects_deep_mode(self, run_deep_agent):
        from agent.agent_executor import run_agent

        run_deep_agent.return_value = {
            "tool": "deep",
            "answer": "answer",
            "sources": [],
        }

        result = run_agent("question", user_id="user-1")

        run_deep_agent.assert_called_once_with(question="question", user_id="user-1")
        self.assertEqual(result["tool"], "deep")


if __name__ == "__main__":
    unittest.main()
