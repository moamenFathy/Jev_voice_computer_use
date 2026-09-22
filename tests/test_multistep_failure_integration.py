"""
Full Multi-Step Failure Propagation & Action-Aware Reliability Integration Tests.
Validates strict failure propagation, non-idempotent action retry safety,
UNAVAILABLE verification semantics, and live reliability metrics across multi-step sequences.
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
from src.verification.verifier import Verifier, VerificationResult
from src.core.os_controller import OSController
from src.decision.jev_engine import JevDecisionEngine


class MockFlakyVerifier(Verifier):
    def __init__(self, succeeds_on_attempt: int = 2):
        self.call_count = 0
        self.succeeds_on_attempt = succeeds_on_attempt

    def verify(self, expected: str, observation: Observation) -> VerificationResult:
        self.call_count += 1
        if self.call_count >= self.succeeds_on_attempt:
            return VerificationResult(
                verified=True,
                status=VerificationStatus.VERIFIED,
                message="Observed target successfully.",
            )
        return VerificationResult(
            verified=False,
            status=VerificationStatus.FAILED,
            message="Target not yet visible in UI.",
        )


class TestMultiStepFailureIntegration(unittest.TestCase):
    def setUp(self):
        self.controller = OSController()
        self.engine = JevDecisionEngine(self.controller)
        self.engine.runtime = AgentRuntime(max_retries=2, retry_delay=0.01)

    def test_multistep_step2_failure_blocks_step3(self):
        """
        Scenario: 3-step goal:
          Step 1: Open Notepad (succeeds)
          Step 2: Click NonExistentButton (fails with NOT_FOUND)
          Step 3: Save Document (MUST NOT EXECUTE)
        """
        executed_steps = []

        def mock_step(step_text, idx, total, auto_play=False, callback=None):
            executed_steps.append((idx, step_text))
            if idx == 1:
                return ToolResult(success=True, tool="launch_app", message="Notepad opened.")
            elif idx == 2:
                return ToolResult(
                    success=False,
                    tool="click_ui_element",
                    error="Button 'MissingBtn' not found.",
                    failure_reason=FailureReason.NOT_FOUND,
                    retryable=False,
                )
            elif idx == 3:
                return ToolResult(success=True, tool="save_file", message="Document saved.")
            return ToolResult(success=True, tool="default")

        self.engine._execute_single_step = mock_step

        goal = "افتح المفكرة ودوس على زرار مش موجود وبعدين احفظ الملف"
        res: GoalResult = self.engine.execute_goal(goal)

        # Strict assertion: Step 3 was never called
        self.assertFalse(res.success)
        self.assertEqual(len(executed_steps), 2)
        self.assertEqual(executed_steps[0], (1, "افتح المفكرة"))
        self.assertIn("زرار مش موجود", executed_steps[1][1])
        self.assertEqual(len(res.steps), 2)
        self.assertIn("Step 2/3 failed", res.message)

        # Reliability metrics check
        metrics = self.engine.runtime.get_metrics()
        self.assertEqual(metrics["total_goals"], 1)
        self.assertEqual(metrics["successful_goals"], 0)
        self.assertEqual(metrics["goal_success_rate_pct"], 0.0)

    def test_multistep_all_steps_succeed(self):
        """
        Scenario: 3-step goal where all steps succeed.
        """
        executed_steps = []

        def mock_step(step_text, idx, total, auto_play=False, callback=None):
            executed_steps.append((idx, step_text))
            return ToolResult(success=True, tool=f"tool_step_{idx}", message=f"Step {idx} done.")

        self.engine._execute_single_step = mock_step

        goal = "افتح المفكرة واكتب تقرير اليوم وبعدين احفظ الملف"
        res: GoalResult = self.engine.execute_goal(goal)

        self.assertTrue(res.success)
        self.assertEqual(len(executed_steps), 3)
        self.assertEqual(len(res.steps), 3)
        self.assertEqual(res.message, "Completed all 3 steps successfully.")

        metrics = self.engine.runtime.get_metrics()
        self.assertEqual(metrics["total_goals"], 1)
        self.assertEqual(metrics["successful_goals"], 1)
        self.assertEqual(metrics["goal_success_rate_pct"], 100.0)

    def test_non_idempotent_action_not_duplicated_on_retry(self):
        """
        Scenario: Non-idempotent action (e.g. type_text) succeeds on attempt 1,
        but verifier is flaky and only confirms on attempt 2.
        execute_fn must be called EXACTLY ONCE (no double-typing!).
        """
        execute_calls = 0

        def non_idempotent_type():
            nonlocal execute_calls
            execute_calls += 1
            return ToolResult(
                success=True,
                tool="type_text",
                message="Typed 'Hello'",
                execution_success=True,
            )

        flaky_verifier = MockFlakyVerifier(succeeds_on_attempt=2)

        def mock_obs():
            return Observation(source="uia", description="Editor text sample")

        res = self.engine.runtime.execute_step(
            action="type_text",
            target="Hello",
            execute_fn=non_idempotent_type,
            observer_fn=mock_obs,
            verifier=flaky_verifier,
            expected="Hello",
            is_idempotent=False,  # Non-idempotent action
        )

        self.assertTrue(res.success)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED)
        # execute_fn was called only ONCE!
        self.assertEqual(execute_calls, 1)
        # Verifier was polled twice until verified
        self.assertEqual(flaky_verifier.call_count, 2)

    def test_unavailable_verification_status_treated_as_success(self):
        """
        Scenario: Action execution succeeds and verifier indicates UNAVAILABLE.
        Must succeed without marking as a verification failure.
        """
        class UnavailableVerifier(Verifier):
            def verify(self, expected: str, observation: Observation) -> VerificationResult:
                return VerificationResult(
                    verified=False,
                    status=VerificationStatus.UNAVAILABLE,
                    message="Hardware volume state inspection unavailable",
                )

        def vol_action():
            return ToolResult(success=True, tool="volume_control", message="Volume pulse sent.")

        def mock_obs():
            return Observation(source="system", description="Hardware state")

        res = self.engine.runtime.execute_step(
            action="volume_control",
            target="volume_up",
            execute_fn=vol_action,
            observer_fn=mock_obs,
            verifier=UnavailableVerifier(),
            expected="volume_up",
        )

        self.assertTrue(res.success)
        self.assertEqual(res.verification_status, VerificationStatus.UNAVAILABLE)
        # Did not record a verification failure
        self.assertEqual(self.engine.runtime.verification_failures, 0)


if __name__ == "__main__":
    unittest.main()
