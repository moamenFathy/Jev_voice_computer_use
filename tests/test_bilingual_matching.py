import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.accessibility_scanner import accessibility_scanner, UIElement

class TestBilingualMatching(unittest.TestCase):
    def setUp(self):
        self.mock_elements = [
            UIElement(
                id=1, name="Lyrics", control_type="Button", automation_id="lyrics-button",
                class_name="Button", left=500, top=600, right=540, bottom=640,
                width=40, height=40, center_x=520, center_y=620,
                is_enabled=True, is_visible=True, value=None, raw_control=None
            ),
            UIElement(
                id=2, name="Next", control_type="Button", automation_id="control-button-skip-forward",
                class_name="Button", left=300, top=600, right=340, bottom=640,
                width=40, height=40, center_x=320, center_y=620,
                is_enabled=True, is_visible=True, value=None, raw_control=None
            ),
            UIElement(
                id=3, name="Previous", control_type="Button", automation_id="control-button-skip-back",
                class_name="Button", left=200, top=600, right=240, bottom=640,
                width=40, height=40, center_x=220, center_y=620,
                is_enabled=True, is_visible=True, value=None, raw_control=None
            ),
            UIElement(
                id=4, name="Search", control_type="Edit", automation_id="search-input",
                class_name="Edit", left=100, top=50, right=400, bottom=90,
                width=300, height=40, center_x=250, center_y=70,
                is_enabled=True, is_visible=True, value="", raw_control=None
            ),
        ]

    def test_lyrics_matching(self):
        queries = ["دوس علي زرار الكلامات", "اضغط على زرار الكلمات", "show lyrics", "كلمات"]
        for q in queries:
            match = accessibility_scanner.find_best_match(q, self.mock_elements)
            self.assertIsNotNone(match, f"Failed to match query: {q}")
            elem, conf = match
            self.assertEqual(elem.name, "Lyrics")

    def test_next_matching(self):
        queries = ["دوس على زرار النيكست", "اضغط على next", "click next", "التالي", "هات اللي بعدها"]
        for q in queries:
            match = accessibility_scanner.find_best_match(q, self.mock_elements)
            self.assertIsNotNone(match, f"Failed to match query: {q}")
            elem, conf = match
            self.assertEqual(elem.name, "Next")

if __name__ == "__main__":
    unittest.main()
