"""
Regression Tests: Protection Against Fake/Fabricated Observations & False Positives.
Guarantees that the verification layer NEVER passes based on assumed or copied state.
"""

import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.observation import Observation
from src.core.tool_result import ToolResult, FailureReason, VerificationStatus
from src.verification.verifier import AppLaunchVerifier, TextVerifier, SearchVerifier
from src.runtime.agent_runtime import AgentRuntime


class TestFakeObservationProtection(unittest.TestCase):
    def setUp(self):
        self.runtime = AgentRuntime(max_retries=1, retry_delay=0.01)
        self.text_verifier = TextVerifier()
        self.app_verifier = AppLaunchVerifier()
        self.search_verifier = SearchVerifier()

    def test_type_text_mismatch_fails_without_assuming_expected(self):
        """
        Scenario: Requested text is 'Hello', but actual editor text is 'Goodbye'.
        The system MUST fail and never pass by copying the expected text into the observation.
        """
        def execute_typing():
            return ToolResult(
                success=True,
                tool="type_text",
                message="Typed to OS buffer",
                execution_success=True,
            )

        def observe_actual_editor():
            # Actual editor content read from UIA is "Goodbye"
            return Observation(
                source="uia",
                description="Observed editor text: 'Goodbye'",
                data={"text": "Goodbye"},
            )

        step_res = self.runtime.execute_step(
            action="type_text",
            target="Hello",
            execute_fn=execute_typing,
            observer_fn=observe_actual_editor,
            verifier=self.text_verifier,
            expected="Hello",
        )

        self.assertFalse(step_res.success)
        self.assertEqual(step_res.verification_status, VerificationStatus.FAILED)
        self.assertEqual(step_res.failure_reason, FailureReason.VERIFICATION_FAILED)
        self.assertIn("not found in observed editor text", step_res.error)

    def test_type_text_unobserved_editor_fails(self):
        """
        Scenario: Editor control could not be inspected (data['text'] is None).
        The system MUST fail and NOT substitute the expected text as a fallback.
        """
        def execute_typing():
            return ToolResult(success=True, tool="type_text", execution_success=True)

        def observe_unreadable_editor():
            return Observation(
                source="uia",
                description="Editor control disconnected",
                data={"text": None},
            )

        step_res = self.runtime.execute_step(
            action="type_text",
            target="Hello",
            execute_fn=execute_typing,
            observer_fn=observe_unreadable_editor,
            verifier=self.text_verifier,
            expected="Hello",
        )

        self.assertFalse(step_res.success)
        self.assertEqual(step_res.verification_status, VerificationStatus.FAILED)
        self.assertIn("could not be observed", step_res.error)

    def test_app_launch_does_not_pass_on_unrelated_window(self):
        """
        Scenario: User asked for 'Notepad', but active window is 'Visual Studio Code'.
        AppLaunchVerifier MUST NOT pass simply because 'a window exists'.
        """
        obs = Observation(
            source="window",
            description="Active window is 'Visual Studio Code'",
            data={"window_title": "Visual Studio Code", "process_name": "code.exe", "window_found": True},
        )
        ver_res = self.app_verifier.verify("notepad", obs)
        self.assertFalse(ver_res.verified)
        self.assertEqual(ver_res.status, VerificationStatus.FAILED)

    def test_search_verifier_does_not_pass_on_blind_launch(self):
        """
        Scenario: Browser opened blindly, but target search query is not in title or loaded.
        SearchVerifier MUST fail.
        """
        obs = Observation(
            source="browser",
            description="Active window is 'New Tab'",
            data={"window_title": "New Tab", "browser_active": True, "target_in_title": False, "results_loaded": False},
        )
        ver_res = self.search_verifier.verify("عمرو دياب", obs)
        self.assertFalse(ver_res.verified)
        self.assertEqual(ver_res.status, VerificationStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
