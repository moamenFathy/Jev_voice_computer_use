"""
App Launch Tool for JEV Tool Registry.
Resolves and executes desktop applications, IDEs, and Windows protocols.
"""

from typing import Optional
from src.tools.base import BaseTool
from src.core.tool_result import ToolResult, FailureReason, VerificationStatus
from src.core.observation import Observation
from src.core.app_resolver import WindowsAppResolver
from src.core.accessibility_scanner import accessibility_scanner
from src.verification.verifier import AppLaunchVerifier, Verifier


class AppLaunchTool(BaseTool):
    name = "launch_app"
    description = "Launches native Windows applications, IDEs, or system protocols"

    def __init__(self, app_resolver: Optional[WindowsAppResolver] = None):
        self.resolver = app_resolver or WindowsAppResolver()
        self.verifier = AppLaunchVerifier()

    def execute(self, target: str, **kwargs) -> ToolResult:
        ok, msg = self.resolver.launch(target)
        if ok:
            return ToolResult(
                success=True,
                tool=self.name,
                message=msg,
                data={"target": target},
                execution_success=True,
            )
        return ToolResult(
            success=False,
            tool=self.name,
            error=msg,
            retryable=False,
            failure_reason=FailureReason.NOT_FOUND,
            execution_success=False,
        )

    def observe(self, target: str, **kwargs) -> Observation:
        import time
        time.sleep(0.8)
        win_title, _ = accessibility_scanner.scan_active_window(max_elements=10)
        return Observation(
            source="window",
            description=f"Active window: '{win_title}'",
            data={
                "window_title": win_title,
                "window_found": bool(win_title and win_title.lower() != "desktop"),
            },
        )

    def get_verifier(self) -> Optional[Verifier]:
        return self.verifier
