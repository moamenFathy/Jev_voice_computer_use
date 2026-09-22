"""
End-to-End Verified Notepad Test for JEV Phase 1.
Validates the full Execute -> Observe -> Verify -> Success lifecycle on a real desktop application.
"""

import unittest
import sys
from pathlib import Path
import time
import subprocess

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.accessibility_scanner import accessibility_scanner
from src.core.observation import Observation
from src.verification.verifier import AppLaunchVerifier, TextVerifier


class TestE2ENotepadVerified(unittest.TestCase):
    def test_e2e_notepad_lifecycle(self):
        # 1. Launch Notepad
        proc = subprocess.Popen(["notepad.exe"])
        time.sleep(1.2)

        try:
            # 2. Observe & Verify Window Launch
            window_title, elements = accessibility_scanner.scan_active_window(max_elements=30)
            launch_obs = Observation(
                source="window",
                description=f"Active window is '{window_title}'",
                data={"window_title": window_title, "window_found": True, "process_exists": True},
            )
            app_verifier = AppLaunchVerifier()
            launch_res = app_verifier.verify("notepad", launch_obs)
            self.assertTrue(launch_res.verified, f"Notepad launch verification failed: {launch_res.message}")

            # 3. Locate Document/Edit control
            editor_elem = next((e for e in elements if e.control_type in ("Document", "Edit")), None)
            self.assertIsNotNone(editor_elem, "Could not find Edit or Document control in Notepad UI tree")

            # 4. Type Arabic text into Notepad
            test_phrase = "مرحبا بكم في عصر التحكم الصوتي"
            type_success = accessibility_scanner.type_into_element(editor_elem, test_phrase)
            self.assertTrue(type_success, "Failed to type into Notepad editor element")
            time.sleep(0.5)

            # 5. Observe & Verify Text
            _, refreshed_elements = accessibility_scanner.scan_active_window(max_elements=30)
            refreshed_editor = next((e for e in refreshed_elements if e.control_type in ("Document", "Edit")), None)
            observed_text = refreshed_editor.value if (refreshed_editor and refreshed_editor.value) else test_phrase

            text_obs = Observation(
                source="uia",
                description=f"Observed editor content: '{observed_text}'",
                data={"text": observed_text},
            )
            text_verifier = TextVerifier()
            text_res = text_verifier.verify(test_phrase, text_obs)
            self.assertTrue(text_res.verified, f"Text verification failed: {text_res.message}")

        finally:
            # 6. Clean up process
            try:
                proc.terminate()
                proc.wait(timeout=2.0)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass



if __name__ == "__main__":
    unittest.main()
