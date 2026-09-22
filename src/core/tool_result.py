"""
ToolResult Model & Failure Categories for JEV Reliability Architecture (Phase 1).
Provides explicit, structured outcomes for every tool execution.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class FailureReason(str, Enum):
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    INVALID_INPUT = "invalid_input"
    EXECUTION_ERROR = "execution_error"
    VERIFICATION_FAILED = "verification_failed"
    APP_NOT_READY = "app_not_ready"
    TARGET_CHANGED = "target_changed"
    UNKNOWN = "unknown"


@dataclass
class ToolResult:
    success: bool
    tool: str
    message: str = ""
    data: Any = None
    error: Optional[str] = None
    retryable: bool = False
    failure_reason: Optional[FailureReason] = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "tool": self.tool,
            "message": self.message,
            "data": self.data,
            "error": self.error,
            "retryable": self.retryable,
            "failure_reason": self.failure_reason.value if self.failure_reason else None,
            "evidence": self.evidence,
        }
