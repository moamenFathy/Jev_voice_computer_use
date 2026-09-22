import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.os_controller import OSController
from src.decision.jev_engine import JevDecisionEngine

class TestPlayRouting(unittest.TestCase):
    def setUp(self):
        self.controller = OSController()
        self.engine = JevDecisionEngine(self.controller)

    def test_music_intent_detection(self):
        test_phrases = [
            ("شغل اغنية ويجز", True),
            ("شغل تراك عمرو دياب", True),
            ("شغل سورة الكهف على يوتيوب", True),
            ("افتح المفكرة", False),
            ("احسب 50 زائد 10", False),
        ]

        for phrase, expected in test_phrases:
            norm = self.engine.scanner._normalize_text(phrase)
            is_music = any(w in norm for w in ["اغنيه", "تراك", "موسيقي", "مغني", "song", "track", "music"]) or (
                norm.startswith("شغل ") and not any(app in norm for app in ["المفكره", "الحاسبه", "الرسام", "المتصفح", "كروم", "رايدر", "كود"])
            )
            self.assertEqual(is_music, expected, f"Failed for phrase: {phrase}")

if __name__ == "__main__":
    unittest.main()
