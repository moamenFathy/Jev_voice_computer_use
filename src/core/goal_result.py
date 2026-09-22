"""
GoalResult Model for JEV Multi-Step Goals (Phase 1).
Maintains structured execution outcomes across atomic sub-tasks and propagates failure.
"""

from dataclasses import dataclass, field
from typing import List
from src.core.tool_result import ToolResult


@dataclass
class GoalResult:
    success: bool
    goal: str
    steps: List[ToolResult] = field(default_factory=list)
    message: str = ""

    def __str__(self) -> str:
        return self.message

    def __bool__(self) -> bool:
        return self.success

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "goal": self.goal,
            "message": self.message,
            "steps": [s.to_dict() for s in self.steps],
            "total_steps": len(self.steps),
            "successful_steps": sum(1 for s in self.steps if s.success),
        }

