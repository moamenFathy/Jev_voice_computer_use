import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.observation import Observation
from src.verification.verifier import (
    AppLaunchVerifier,
    TextVerifier,
    UIElementVerifier,
    SearchVerifier,
    VerificationResult,
)


class TestVerification(unittest.TestCase):
    def setUp(self):
        self.app_verifier = AppLaunchVerifier()
        self.text_verifier = TextVerifier()
        self.ui_verifier = UIElementVerifier()
        self.search_verifier = SearchVerifier()

    # -------------------------------------------------------------
    # 1. App Launch Verifier
    # -------------------------------------------------------------
    def test_app_launch_verifier_success(self):
        obs = Observation(
            source="window",
            description="Active window is 'Untitled - Notepad'",
            data={"window_title": "Untitled - Notepad", "window_found": True, "process_exists": True},
        )
        res = self.app_verifier.verify("notepad", obs)
        self.assertTrue(res.verified)
        self.assertIn("notepad", res.message.lower())

    def test_app_launch_verifier_failure(self):
        obs = Observation(
            source="window",
            description="Active window is 'Google Chrome'",
            data={"window_title": "Google Chrome", "window_found": False, "process_exists": False},
        )
        res = self.app_verifier.verify("rider", obs)
        self.assertFalse(res.verified)

    # -------------------------------------------------------------
    # 2. Text Verifier
    # -------------------------------------------------------------
    def test_text_verifier_success(self):
        obs = Observation(
            source="uia",
            description="Editor contains text",
            data={"text": "مرحبا بكم في عصر التحكم الصوتي"},
        )
        res = self.text_verifier.verify("مرحبا بكم في عصر التحكم الصوتي", obs)
        self.assertTrue(res.verified)

    def test_text_verifier_failure(self):
        obs = Observation(
            source="uia",
            description="Editor contains empty text",
            data={"text": ""},
        )
        res = self.text_verifier.verify("مرحبا بكم", obs)
        self.assertFalse(res.verified)

    # -------------------------------------------------------------
    # 3. UI Element Verifier
    # -------------------------------------------------------------
    def test_ui_element_verifier_success(self):
        obs = Observation(
            source="uia",
            description="Button Save clicked",
            data={"action_performed": True, "element_found": True, "is_enabled": True},
        )
        res = self.ui_verifier.verify("Save", obs)
        self.assertTrue(res.verified)

    def test_ui_element_verifier_failure(self):
        obs = Observation(
            source="uia",
            description="Element missing",
            data={"action_performed": False, "element_found": False},
        )
        res = self.ui_verifier.verify("Save", obs)
        self.assertFalse(res.verified)

    # -------------------------------------------------------------
    # 4. Search Verifier
    # -------------------------------------------------------------
    def test_search_verifier_success(self):
        obs = Observation(
            source="browser",
            description="Google search opened",
            data={"submitted": True, "url_opened": True},
        )
        res = self.search_verifier.verify("عمرو دياب", obs)
        self.assertTrue(res.verified)

    def test_search_verifier_failure(self):
        obs = Observation(
            source="browser",
            description="Network timeout",
            data={"submitted": False, "url_opened": False, "results_loaded": False},
        )
        res = self.search_verifier.verify("عمرو دياب", obs)
        self.assertFalse(res.verified)


if __name__ == "__main__":
    unittest.main()
