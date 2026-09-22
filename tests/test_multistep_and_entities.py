import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.os_controller import OSController
from src.decision.jev_engine import JevDecisionEngine

class TestMultistepAndEntities(unittest.TestCase):
    def setUp(self):
        self.controller = OSController()
        self.engine = JevDecisionEngine(self.controller)

    def test_multi_step_decomposition(self):
        steps, ap = self.engine._decompose_into_steps("افتح المفكرة واكتب تقرير اليوم وبعدين احفظ الملف")
        self.assertEqual(len(steps), 3)

        steps, ap = self.engine._decompose_into_steps("افتح يوتيوب ميوزك وشغل اغنية اغيب")
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0], "افتح يوتيوب ميوزك")
        self.assertEqual(steps[1], "شغل اغنية اغيب")

    def test_entity_extraction(self):
        p, q = self.engine._extract_clean_entities("سيرش في youtube music على اغنية اغيب")
        self.assertEqual(p, "youtube_music")
        self.assertEqual(q, "اغيب")

        p, q = self.engine._extract_clean_entities("ابحث في جوجل عن اسعار الذهب اليوم")
        self.assertEqual(p, "google")
        self.assertEqual(q, "اسعار الذهب اليوم")

if __name__ == "__main__":
    unittest.main()
