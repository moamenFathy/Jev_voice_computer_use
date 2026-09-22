import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.observation import Observation
from src.core.tool_result import VerificationStatus
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
            data={"window_title": "Untitled - Notepad", "process_name": "notepad.exe", "window_found": True},
        )
        res = self.app_verifier.verify("notepad", obs)
        self.assertTrue(res.verified)
        self.assertEqual(res.status, VerificationStatus.VERIFIED)
        self.assertIn("notepad", res.message.lower())

    def test_app_launch_verifier_rejects_unrelated_window(self):
        # Crucial test: Chrome is active, but we requested Rider. Must FAIL!
        obs = Observation(
            source="window",
            description="Active window is 'Google Chrome'",
            data={"window_title": "Google Chrome", "process_name": "chrome.exe", "window_found": True},
        )
        res = self.app_verifier.verify("rider", obs)
        self.assertFalse(res.verified)
        self.assertEqual(res.status, VerificationStatus.FAILED)
        self.assertIn("Expected app 'rider' not found", res.message)

    def test_app_launch_verifier_rejects_desktop_empty(self):
        obs = Observation(
            source="window",
            description="Active window is 'Desktop'",
            data={"window_title": "Desktop", "process_name": "", "window_found": False},
        )
        res = self.app_verifier.verify("notepad", obs)
        self.assertFalse(res.verified)
        self.assertEqual(res.status, VerificationStatus.FAILED)

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
        self.assertEqual(res.status, VerificationStatus.VERIFIED)

    def test_text_verifier_failure_mismatch(self):
        obs = Observation(
            source="uia",
            description="Editor contains different text",
            data={"text": "Goodbye World"},
        )
        res = self.text_verifier.verify("Hello World", obs)
        self.assertFalse(res.verified)
        self.assertEqual(res.status, VerificationStatus.FAILED)

    def test_text_verifier_failure_unobserved_none(self):
        # Target editor value was not available from UI (None) -> Must FAIL
        obs = Observation(
            source="uia",
            description="Editor text unavailable",
            data={"text": None},
        )
        res = self.text_verifier.verify("Hello World", obs)
        self.assertFalse(res.verified)
        self.assertEqual(res.status, VerificationStatus.FAILED)
        self.assertIn("could not be observed", res.message)

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
        self.assertEqual(res.status, VerificationStatus.VERIFIED)

    def test_ui_element_verifier_missing_element(self):
        obs = Observation(
            source="uia",
            description="Element missing",
            data={"action_performed": False, "element_found": False, "is_enabled": False},
        )
        res = self.ui_verifier.verify("Save", obs)
        self.assertFalse(res.verified)
        self.assertEqual(res.status, VerificationStatus.FAILED)

    def test_ui_element_verifier_disabled_element(self):
        obs = Observation(
            source="uia",
            description="Element disabled",
            data={"action_performed": False, "element_found": True, "is_enabled": False},
        )
        res = self.ui_verifier.verify("Save", obs)
        self.assertFalse(res.verified)
        self.assertEqual(res.status, VerificationStatus.FAILED)
        self.assertIn("disabled", res.message)

    # -------------------------------------------------------------
    # 4. Search Verifier
    # -------------------------------------------------------------
    def test_search_verifier_success(self):
        obs = Observation(
            source="browser",
            description="Google search opened",
            data={"window_title": "عمرو دياب - Google Search", "browser_active": True, "target_in_title": True, "results_loaded": True},
        )
        res = self.search_verifier.verify("عمرو دياب", obs)
        self.assertTrue(res.verified)
        self.assertEqual(res.status, VerificationStatus.VERIFIED)

    def test_search_verifier_failure_generic_window(self):
        obs = Observation(
            source="browser",
            description="Generic desktop active",
            data={"window_title": "Desktop", "browser_active": False, "target_in_title": False, "results_loaded": False},
        )
        res = self.search_verifier.verify("عمرو دياب", obs)
        self.assertFalse(res.verified)
        self.assertEqual(res.status, VerificationStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
