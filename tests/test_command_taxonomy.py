import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.os_controller import OSController
from src.decision.jev_engine import JevDecisionEngine

class TestCommandTaxonomy(unittest.TestCase):
    def setUp(self):
        self.controller = OSController()
        self.engine = JevDecisionEngine(self.controller)

    # -------------------------------------------------------------
    # 1. Media & Music
    # -------------------------------------------------------------
    def test_media_playback_and_entity_extraction(self):
        # Direct track search and platform
        p, q = self.engine._extract_clean_entities("شغل اغنية اغيب في youtube music")
        self.assertEqual(p, "youtube_music")
        self.assertEqual(q, "اغيب")

        p, q = self.engine._extract_clean_entities("سيرش على عمرو دياب في سبوتيفاي")
        self.assertEqual(p, "spotify")
        self.assertEqual(q, "عمرو دياب")

        p, q = self.engine._extract_clean_entities("شغل ويجز في انغامي")
        self.assertEqual(p, "anghami")
        self.assertEqual(q, "ويجز")

        p, q = self.engine._extract_clean_entities("شغل مروان بابلو في ساوند كلاود")
        self.assertEqual(p, "soundcloud")
        self.assertEqual(q, "مروان بابلو")

    # -------------------------------------------------------------
    # 2. Web Navigation
    # -------------------------------------------------------------
    def test_web_navigation(self):
        # Known site direct resolution
        res = self.engine._resolve_web_navigation("خش على موقع أنغامي")
        self.assertIsNotNone(res)
        self.assertEqual(res["type"], "direct_url")
        self.assertIn("anghami.com", res["url"])

        res = self.engine._resolve_web_navigation("ادخل على فيسبوك")
        self.assertIsNotNone(res)
        self.assertEqual(res["url"], "https://facebook.com")

        res = self.engine._resolve_web_navigation("خش على github.com")
        self.assertIsNotNone(res)
        self.assertEqual(res["url"], "https://github.com")

        res = self.engine._resolve_web_navigation("روح لموقع البنك الاهلي المصري")
        self.assertIsNotNone(res)
        self.assertEqual(res["type"], "search_site")

    # -------------------------------------------------------------
    # 3. Multi-Step Decomposition
    # -------------------------------------------------------------
    def test_multistep_chains(self):
        steps, auto_play = self.engine._decompose_into_steps("افتح المفكرة واكتب تقرير اليوم وبعدين احفظ الملف")
        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[0], "افتح المفكرة")
        self.assertEqual(steps[1], "اكتب تقرير اليوم")
        self.assertEqual(steps[2], "احفظ الملف")

        steps, auto_play = self.engine._decompose_into_steps("سيرش على اغيب في يوتيوب ميوزك وشغلها")
        self.assertEqual(len(steps), 1)
        self.assertTrue(auto_play)

        steps, auto_play = self.engine._decompose_into_steps("خش على موقع أنغامي وشغل عمرو دياب")
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0], "خش على موقع أنغامي")
        self.assertEqual(steps[1], "شغل عمرو دياب")

if __name__ == "__main__":
    unittest.main()
