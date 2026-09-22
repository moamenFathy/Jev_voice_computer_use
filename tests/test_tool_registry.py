"""
Unit Tests for JEV Tool Registry Subsystem (Phase 2).
Validates tool registration, discovery, execution, observation, and verifier integration.
"""

import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.tools import (
    tool_registry,
    BaseTool,
    ToolRegistry,
    AppLaunchTool,
    ClickUIElementTool,
    TypeTextTool,
    InAppSearchTool,
    WebNavigationTool,
    GoogleSearchTool,
    YouTubeMusicTool,
    YouTubeTool,
    SpotifyTool,
    AnghamiTool,
    SoundCloudTool,
    MediaPlaybackTool,
    VolumeTool,
    WindowManagementTool,
    DocumentShortcutTool,
    MathCalculateTool,
)
from src.core.tool_result import ToolResult, VerificationStatus
from src.verification import AppLaunchVerifier, TextVerifier, UIElementVerifier, SearchVerifier


class TestToolRegistry(unittest.TestCase):
    def test_global_registry_populated(self):
        expected_tools = [
            "launch_app",
            "click_ui_element",
            "type_text",
            "in_app_search",
            "web_navigation",
            "web_search",
            "youtube_music",
            "youtube",
            "spotify",
            "anghami",
            "soundcloud",
            "media_playback",
            "volume_control",
            "window_management",
            "document_shortcut",
            "math_calculate",
        ]
        for name in expected_tools:
            self.assertIn(name, tool_registry, f"Expected tool '{name}' in tool_registry")
            tool = tool_registry[name]
            self.assertIsInstance(tool, BaseTool)
            self.assertEqual(tool.name, name)

    def test_custom_tool_registration(self):
        registry = ToolRegistry()

        class CustomEchoTool(BaseTool):
            name = "custom_echo"
            description = "Custom test echo tool"

            def execute(self, target: str, **kwargs) -> ToolResult:
                return ToolResult(success=True, tool=self.name, message=f"Echo: {target}")

        echo_tool = CustomEchoTool()
        registry.register(echo_tool)
        self.assertIn("custom_echo", registry)
        res = registry["custom_echo"].execute("Hello World")
        self.assertTrue(res.success)
        self.assertEqual(res.message, "Echo: Hello World")

    def test_tool_verifiers_configured(self):
        self.assertIsInstance(tool_registry["launch_app"].get_verifier(), AppLaunchVerifier)
        self.assertIsInstance(tool_registry["type_text"].get_verifier(), TextVerifier)
        self.assertIsInstance(tool_registry["click_ui_element"].get_verifier(), UIElementVerifier)
        self.assertIsInstance(tool_registry["web_navigation"].get_verifier(), SearchVerifier)
        self.assertIsInstance(tool_registry["web_search"].get_verifier(), SearchVerifier)
        self.assertIsInstance(tool_registry["youtube_music"].get_verifier(), SearchVerifier)
        self.assertIsInstance(tool_registry["youtube"].get_verifier(), SearchVerifier)
        self.assertIsInstance(tool_registry["spotify"].get_verifier(), SearchVerifier)

    def test_media_playback_tool_dispatches(self):
        tool: MediaPlaybackTool = tool_registry["media_playback"]
        res = tool.execute("pause")
        self.assertTrue(res.success)
        self.assertEqual(res.message, "Media playback paused.")

        res_next = tool.execute("next")
        self.assertTrue(res_next.success)
        self.assertEqual(res_next.message, "Skipped to next track.")


if __name__ == "__main__":
    unittest.main()
