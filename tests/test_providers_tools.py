"""Provider tool conversion + message mapping (no live API)."""

import json
import unittest
from types import SimpleNamespace

from tutor.character_sheet import UPDATE_CHARACTER_SHEET_TOOL
from tutor.conv_session import _split_content, _tool_delta_from_blocks
from tutor.providers import (
    anthropic_tools_to_openai,
    messages_to_openai,
    parse_openai_message_to_anthropic,
)


class TestProviderTools(unittest.TestCase):
    def test_anthropic_to_openai_tools(self):
        oai = anthropic_tools_to_openai([UPDATE_CHARACTER_SHEET_TOOL])
        self.assertEqual(len(oai), 1)
        self.assertEqual(oai[0]["type"], "function")
        self.assertEqual(oai[0]["function"]["name"], "update_character_sheet")
        self.assertIn("properties", oai[0]["function"]["parameters"])

    def test_parse_openai_tool_calls(self):
        msg = {
            "content": "¡Hola Patrick!",
            "tool_calls": [{
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "update_character_sheet",
                    "arguments": json.dumps({
                        "identity": {"preferred_name": "Patrick"},
                        "skills": {"IP-03": {"status": "emerging", "confidence": 0.35}},
                    }),
                },
            }],
        }
        blocks, stop = parse_openai_message_to_anthropic(msg, "tool_calls")
        self.assertEqual(stop, "tool_use")
        types = [b.type for b in blocks]
        self.assertIn("text", types)
        self.assertIn("tool_use", types)
        tool = next(b for b in blocks if b.type == "tool_use")
        self.assertEqual(tool.name, "update_character_sheet")
        self.assertEqual(tool.input["identity"]["preferred_name"], "Patrick")

    def test_messages_tool_result_roundtrip(self):
        messages = [
            {"role": "user", "content": "hola"},
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Hi!"},
                    {
                        "type": "tool_use",
                        "id": "c1",
                        "name": "update_character_sheet",
                        "input": {"identity": {"preferred_name": "Pat"}},
                    },
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "c1",
                        "content": '{"ok": true}',
                    },
                    {"type": "text", "text": "now speak to the learner"},
                ],
            },
        ]
        oai = messages_to_openai(messages)
        roles = [m["role"] for m in oai]
        self.assertIn("tool", roles)
        self.assertEqual(oai[-1]["role"], "user")
        self.assertIn("learner", oai[-1]["content"])

    def test_split_and_merge_tool_delta(self):
        final = SimpleNamespace(content=[
            SimpleNamespace(type="text", text="Mucho gusto."),
            SimpleNamespace(
                type="tool_use",
                id="c1",
                name="update_character_sheet",
                input={
                    "identity": {"preferred_name": "Sam"},
                    "skills": {"IP-03": {"confidence": 0.4}},
                },
            ),
        ])
        text, tools = _split_content(final)
        self.assertEqual(text, "Mucho gusto.")
        delta = _tool_delta_from_blocks(tools)
        self.assertEqual(delta["identity"]["preferred_name"], "Sam")
        self.assertEqual(delta["skills"]["IP-03"]["confidence"], 0.4)


if __name__ == "__main__":
    unittest.main()
