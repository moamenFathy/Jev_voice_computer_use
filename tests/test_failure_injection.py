"""
Failure Injection Tests for JEV Phase 1 Reliability Architecture.
Validates detection, classification, bounded retry, and structured failure handling
under simulated environment faults.
"""

import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.tool_result import ToolResult, FailureReason, VerificationStatus
from src.core.observation import Observation
from src.core.goal_result import GoalResult
from src.runtime.agent_runtime import AgentRuntime
from src.verification.verifier import AppLaunchVerifier, UIElementVerifier, VerificationResult
from src.core.os_controller import OSController
from src.decision.jev_engine import JevDecisionEngine


class TestFailureInjection(unittest.TestCase):
    def setUp(self):
        self.runtime = AgentRuntime(max_retries=2, retry_delay=0.01)

    # -------------------------------------------------------------
    # 1. Invalid App Launch Injection
    # -------------------------------------------------------------
    def test_invalid_app_launch_failure(self):
        controller = OSController()
        engine = JevDecisionEngine(controller)

        # Non-existent application
        res: GoalResult = engine.execute_goal("افتح برنامج_مش_موجود_نهائيا_12345")
        self.assertFalse(res.success)
        self.assertGreaterEqual(len(res.steps), 1)
        self.assertEqual(res.steps[0].failure_reason, FailureReason.NOT_FOUND)
        self.assertFalse(res.steps[0].retryable)

    # -------------------------------------------------------------
    # 2. Missing UI Element Injection
    # -------------------------------------------------------------
    def test_missing_ui_element_injection(self):
        ui_verifier = UIElementVerifier()

        def mock_click_missing():
            return ToolResult(
                success=False,
                tool="click_ui_element",
                error="Requested UI element 'NonExistentButtonXYZ' not found.",
                failure_reason=FailureReason.NOT_FOUND,
                execution_success=False,
                retryable=True,
            )

        res = self.runtime.execute_step(
            action="click_ui_element",
            target="NonExistentButtonXYZ",
            execute_fn=mock_click_missing,
            verifier=ui_verifier,
            expected="NonExistentButtonXYZ",
        )

        self.assertFalse(res.success)
        self.assertEqual(res.failure_reason, FailureReason.NOT_FOUND)
        self.assertEqual(self.runtime.retries_attempted, 2)  # retried up to max

    # -------------------------------------------------------------
    # 3. Tool Exception Injection (Unhandled crash in tool)
    # -------------------------------------------------------------
    def test_tool_exception_injection_caught_safely(self):
        def crashing_tool():
            raise RuntimeError("Hardware communication bus error!")

        res = self.runtime.execute_step(
            action="hardware_action",
            target="hardware_device",
            execute_fn=crashing_tool,
        )

        self.assertFalse(res.success)
        self.assertEqual(res.failure_reason, FailureReason.EXECUTION_ERROR)
        self.assertIn("Exception during execution", res.error)

    # -------------------------------------------------------------
    # 4. Closed / Wrong Active Window Injection
    # -------------------------------------------------------------
    def test_wrong_target_window_injection(self):
        app_verifier = AppLaunchVerifier()

        def successful_command_dispatch():
            return ToolResult(success=True, tool="launch_app", message="Process spawned", execution_success=True)

        def observe_wrong_window():
            # Window that appeared is not Calculator, but Cmd
            return Observation(
                source="window",
                description="Active window is 'cmd.exe'",
                data={"window_title": "Command Prompt", "process_name": "cmd.exe", "window_found": True},
            )

        res = self.runtime.execute_step(
            action="launch_app",
            target="calculator",
            execute_fn=successful_command_dispatch,
            observer_fn=observe_wrong_window,
            verifier=app_verifier,
            expected="calculator",
        )

        self.assertFalse(res.success)
        self.assertEqual(res.verification_status, VerificationStatus.FAILED)
        self.assertEqual(res.failure_reason, FailureReason.VERIFICATION_FAILED)


if __name__ == "__main__":
    unittest.main()
