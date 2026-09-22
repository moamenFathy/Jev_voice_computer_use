import unittest
import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.tool_result import ToolResult, FailureReason
from src.core.observation import Observation
from src.core.goal_result import GoalResult
from src.runtime.agent_runtime import AgentRuntime
from src.verification.verifier import Verifier, VerificationResult
from src.core.os_controller import OSController
from src.decision.jev_engine import JevDecisionEngine


class MockFailingVerifier(Verifier):
    def __init__(self, succeeds_on_attempt: int = 2):
        self.call_count = 0
        self.succeeds_on_attempt = succeeds_on_attempt

    def verify(self, expected: str, observation: Observation) -> VerificationResult:
        self.call_count += 1
        if self.call_count >= self.succeeds_on_attempt:
            return VerificationResult(verified=True, message="Verified successfully.")
        return VerificationResult(verified=False, message="Simulated verification failure.")


class TestRetryRuntime(unittest.TestCase):
    def setUp(self):
        self.runtime = AgentRuntime(max_retries=2, retry_delay=0.01)

    # -------------------------------------------------------------
    # 1. Retryable Execution: Attempt 1 Fail -> Attempt 2 Success
    # -------------------------------------------------------------
    def test_retryable_execution_success(self):
        attempts = 0

        def flaky_action():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return ToolResult(
                    success=False,
                    tool="click_button",
                    error="UI not ready",
                    failure_reason=FailureReason.APP_NOT_READY,
                    retryable=True,
                )
            return ToolResult(
                success=True,
                tool="click_button",
                message="Button clicked on second try.",
            )

        res = self.runtime.execute_step(
            action="click_button",
            target="Save",
            execute_fn=flaky_action,
        )

        self.assertTrue(res.success)
        self.assertEqual(attempts, 2)
        self.assertEqual(self.runtime.retries_attempted, 1)

    # -------------------------------------------------------------
    # 2. Retry Exhaustion (Bounded Retries, No Infinite Loop)
    # -------------------------------------------------------------
    def test_retry_exhaustion_stops(self):
        attempts = 0

        def always_failing_action():
            nonlocal attempts
            attempts += 1
            return ToolResult(
                success=False,
                tool="find_window",
                error="Window never appeared",
                failure_reason=FailureReason.TIMEOUT,
                retryable=True,
            )

        res = self.runtime.execute_step(
            action="find_window",
            target="NonExistentApp",
            execute_fn=always_failing_action,
        )

        self.assertFalse(res.success)
        # Max retries = 2, so total attempts = 1 initial + 2 retries = 3
        self.assertEqual(attempts, 3)
        self.assertEqual(self.runtime.retries_attempted, 2)

    # -------------------------------------------------------------
    # 3. Non-Retryable Failure: Stops After 1 Attempt
    # -------------------------------------------------------------
    def test_non_retryable_failure_stops_immediately(self):
        attempts = 0

        def invalid_input_action():
            nonlocal attempts
            attempts += 1
            return ToolResult(
                success=False,
                tool="launch_app",
                error="Invalid app path",
                failure_reason=FailureReason.INVALID_INPUT,
                retryable=False,
            )

        res = self.runtime.execute_step(
            action="launch_app",
            target="unknown_app",
            execute_fn=invalid_input_action,
        )

        self.assertFalse(res.success)
        self.assertEqual(attempts, 1)
        self.assertEqual(self.runtime.retries_attempted, 0)

    # -------------------------------------------------------------
    # 4. Verification Failure (Execution Success != Goal Success)
    # -------------------------------------------------------------
    def test_verification_failure_causes_overall_failure(self):
        # Action succeeds at OS level, but verifier always fails
        always_fail_verifier = MockFailingVerifier(succeeds_on_attempt=999)

        def succeed_action():
            return ToolResult(success=True, tool="click_save", message="OS clicked successfully")

        def mock_obs():
            return Observation(source="uia", description="File not saved yet")

        res = self.runtime.execute_step(
            action="click_save",
            target="Save",
            execute_fn=succeed_action,
            observer_fn=mock_obs,
            verifier=always_fail_verifier,
            expected="Save",
        )

        # Crucial principle: Execution != Goal Success
        self.assertFalse(res.success)
        self.assertEqual(res.failure_reason, FailureReason.VERIFICATION_FAILED)
        self.assertIn("Verification failed", res.error)

    # -------------------------------------------------------------
    # 5. Multi-Step Failure Propagation in JevDecisionEngine
    # -------------------------------------------------------------
    def test_multistep_failure_propagation(self):
        controller = OSController()
        engine = JevDecisionEngine(controller)

        step_counter = 0

        def mock_execute_single_step(step_text, idx, total, auto_play=False, callback=None):
            nonlocal step_counter
            step_counter += 1
            if idx == 1:
                return ToolResult(success=True, tool="launch_app", message="Notepad launched.")
            elif idx == 2:
                return ToolResult(
                    success=False,
                    tool="type_text",
                    error="UI Element disconnected.",
                    failure_reason=FailureReason.APP_NOT_READY,
                    retryable=False,
                )
            elif idx == 3:
                return ToolResult(success=True, tool="save_file", message="Saved.")
            return ToolResult(success=True, tool="default")

        engine._execute_single_step = mock_execute_single_step

        # 3-step compound goal
        goal = "افتح المفكرة واكتب مرحبا وبعدين احفظ الملف"
        goal_res: GoalResult = engine.execute_goal(goal)

        # Assert: Step 2 failed -> Step 3 must NOT have been executed
        self.assertFalse(goal_res.success)
        self.assertEqual(step_counter, 2)
        self.assertEqual(len(goal_res.steps), 2)
        self.assertIn("Step 2/3 failed", goal_res.message)

    # -------------------------------------------------------------
    # 6. Reliability Metrics
    # -------------------------------------------------------------
    def test_metrics_collection(self):
        self.runtime.record_goal_outcome(True)
        self.runtime.record_goal_outcome(False)
        metrics = self.runtime.get_metrics()
        self.assertEqual(metrics["total_goals"], 2)
        self.assertEqual(metrics["successful_goals"], 1)
        self.assertEqual(metrics["goal_success_rate_pct"], 50.0)


if __name__ == "__main__":
    unittest.main()
