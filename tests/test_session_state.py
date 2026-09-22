"""
Unit Tests for JEV Session State & Contextual Pronoun Resolution (Phase 3 Foundation).
"""

import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.session_state import SessionState, session_state


class TestSessionState(unittest.TestCase):
    def setUp(self):
        self.state = SessionState(max_history=5)

    def test_record_turn_updates_state(self):
        self.state.record_turn(
            goal="افتح المفكرة",
            action="launch_app",
            target="notepad",
            platform="default",
            window_title="Untitled - Notepad",
            success=True,
        )
        self.assertEqual(self.state.last_active_app, "notepad")
        self.assertEqual(self.state.last_window_title, "Untitled - Notepad")
        self.assertEqual(len(self.state.history), 1)

    def test_sliding_history_bounded(self):
        for i in range(10):
            self.state.record_turn(
                goal=f"Goal {i}",
                action="test",
                target=f"Target {i}",
                success=True,
            )
        self.assertEqual(len(self.state.history), 5)

    def test_arabic_pronoun_resolution(self):
        # Close pronoun
        self.assertEqual(self.state.resolve_contextual_query("اقفله"), "اقفل النافذة")
        self.assertEqual(self.state.resolve_contextual_query("اقفلها"), "اقفل النافذة")
        self.assertEqual(self.state.resolve_contextual_query("close it"), "اقفل النافذة")

        # Save pronoun
        self.assertEqual(self.state.resolve_contextual_query("احفظه"), "احفظ الملف")
        self.assertEqual(self.state.resolve_contextual_query("احفظها"), "احفظ الملف")
        self.assertEqual(self.state.resolve_contextual_query("سيفه"), "احفظ الملف")

        # Next / skip pronoun
        self.assertEqual(self.state.resolve_contextual_query("شغل غيرها"), "التالي")
        self.assertEqual(self.state.resolve_contextual_query("هات غيرها"), "التالي")

        # Copy / paste pronoun
        self.assertEqual(self.state.resolve_contextual_query("انسخه"), "نسخ")
        self.assertEqual(self.state.resolve_contextual_query("الصقه"), "لصق")

    def test_play_last_recorded_query(self):
        self.state.record_turn(
            goal="سيرش على عمرو دياب في يوتيوب ميوزك",
            action="youtube_music",
            target="عمرو دياب",
            platform="youtube_music",
            success=True,
        )
        self.assertEqual(self.state.last_search_query, "عمرو دياب")
        resolved = self.state.resolve_contextual_query("شغلها")
        self.assertEqual(resolved, "شغل عمرو دياب في youtube_music")


if __name__ == "__main__":
    unittest.main()
