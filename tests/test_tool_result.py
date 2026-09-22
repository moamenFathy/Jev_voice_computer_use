import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.tool_result import ToolResult, FailureReason
from src.core.observation import Observation
from src.core.goal_result import GoalResult


class TestToolResultModels(unittest.TestCase):
    def test_successful_tool_result(self):
        res = ToolResult(
            success=True,
            tool="launch_app",
            message="Rider launched.",
            evidence={"process_started": True, "window_found": True},
        )
        self.assertTrue(res.success)
        self.assertEqual(res.tool, "launch_app")
        self.assertEqual(res.message, "Rider launched.")
        self.assertIsNone(res.error)
        self.assertFalse(res.retryable)
        self.assertTrue(res.evidence.get("process_started"))

        d = res.to_dict()
        self.assertTrue(d["success"])
        self.assertEqual(d["tool"], "launch_app")
        self.assertIsNone(d["failure_reason"])

    def test_failed_non_retryable_tool_result(self):
        res = ToolResult(
            success=False,
            tool="launch_app",
            message="Could not launch Rider.",
            error="Application executable was not found.",
            failure_reason=FailureReason.NOT_FOUND,
            retryable=False,
        )
        self.assertFalse(res.success)
        self.assertFalse(res.retryable)
        self.assertEqual(res.failure_reason, FailureReason.NOT_FOUND)
        self.assertEqual(res.to_dict()["failure_reason"], "not_found")

    def test_retryable_tool_result(self):
        res = ToolResult(
            success=False,
            tool="click_element",
            message="Target was not found yet.",
            error="UI element unavailable.",
            failure_reason=FailureReason.APP_NOT_READY,
            retryable=True,
        )
        self.assertFalse(res.success)
        self.assertTrue(res.retryable)
        self.assertEqual(res.failure_reason, FailureReason.APP_NOT_READY)

    def test_observation_model(self):
        obs = Observation(
            source="uia",
            description="Save button was found and is enabled.",
            evidence={"control_name": "Save", "enabled": True, "control_type": "Button"},
        )
        self.assertEqual(obs.source, "uia")
        self.assertEqual(obs.to_dict()["evidence"]["control_name"], "Save")

    def test_goal_result_model(self):
        step1 = ToolResult(success=True, tool="launch_app", message="Launched Notepad")
        step2 = ToolResult(success=True, tool="type_text", message="Typed Hello")
        goal_res = GoalResult(
            success=True,
            goal="افتح المفكرة واكتب Hello",
            steps=[step1, step2],
            message="Completed all 2 steps successfully.",
        )
        self.assertTrue(goal_res.success)
        self.assertTrue(bool(goal_res))
        self.assertEqual(str(goal_res), "Completed all 2 steps successfully.")
        self.assertEqual(len(goal_res.steps), 2)
        d = goal_res.to_dict()
        self.assertEqual(d["total_steps"], 2)
        self.assertEqual(d["successful_steps"], 2)


if __name__ == "__main__":
    unittest.main()
