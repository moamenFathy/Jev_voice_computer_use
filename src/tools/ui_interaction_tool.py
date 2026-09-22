"""
UI Interaction Tools for JEV Tool Registry.
Includes ClickUIElementTool, TypeTextTool, and InAppSearchTool with UIA inspection.
"""

from typing import Optional, Dict, Any, List
from src.tools.base import BaseTool
from src.core.tool_result import ToolResult, FailureReason, VerificationStatus
from src.core.observation import Observation
from src.core.os_controller import OSController
from src.core.accessibility_scanner import accessibility_scanner, UIElement
from src.verification.verifier import UIElementVerifier, TextVerifier, SearchVerifier, Verifier


class ClickUIElementTool(BaseTool):
    name = "click_ui_element"
    description = "Clicks a button, menu item, tab, or control inside the active window"

    def __init__(self, scanner=None):
        self.scanner = scanner or accessibility_scanner
        self.verifier = UIElementVerifier()
        self._last_matched_element: Optional[UIElement] = None

    def execute(self, target: str, **kwargs) -> ToolResult:
        ui_elements: List[UIElement] = kwargs.get("ui_elements", [])
        if not ui_elements:
            _, ui_elements = self.scanner.scan_active_window(max_elements=40)

        match_res = self.scanner.find_best_match(target, ui_elements)
        if not match_res:
            self._last_matched_element = None
            return ToolResult(
                success=False,
                tool=self.name,
                error=f"Requested UI element '{target}' not found in active window.",
                failure_reason=FailureReason.NOT_FOUND,
                execution_success=False,
                verification_status=VerificationStatus.FAILED,
                retryable=True,
            )

        target_elem, conf = match_res
        self._last_matched_element = target_elem
        clicked = self.scanner.click_element(target_elem)
        if clicked:
            return ToolResult(
                success=True,
                tool=self.name,
                message=f"Clicked '{target_elem.name}' successfully.",
                data=target_elem.to_dict(),
                execution_success=True,
            )
        return ToolResult(
            success=False,
            tool=self.name,
            error=f"Failed to click '{target_elem.name}'",
            retryable=True,
            failure_reason=FailureReason.NOT_FOUND,
            execution_success=False,
        )

    def observe(self, target: str, **kwargs) -> Observation:
        w_title, _ = self.scanner.scan_active_window(max_elements=30)
        elem = self._last_matched_element
        if elem:
            return Observation(
                source="uia",
                description=f"Clicked element '{elem.name}' in '{w_title}'",
                data={
                    "action_performed": True,
                    "element_found": True,
                    "is_enabled": elem.is_enabled,
                    "window_title": w_title,
                },
            )
        return Observation(
            source="uia",
            description=f"UI element '{target}' action performed in '{w_title}'",
            data={"action_performed": False, "element_found": False, "window_title": w_title},
        )

    def get_verifier(self) -> Optional[Verifier]:
        return self.verifier

    def reobserve(self) -> None:
        self.scanner.scan_active_window(max_elements=40)


class TypeTextTool(BaseTool):
    name = "type_text"
    description = "Types Arabic or English text into the active document or input field"
    is_idempotent: bool = False

    def __init__(self, os_controller: Optional[OSController] = None, scanner=None):
        self.controller = os_controller or OSController()
        self.scanner = scanner or accessibility_scanner
        self.verifier = TextVerifier()

    def execute(self, target: str, **kwargs) -> ToolResult:
        text_to_type = target
        _, cur_elements = self.scanner.scan_active_window(max_elements=30)
        editor_elem = next((e for e in cur_elements if e.control_type in ("Edit", "Document")), None)

        if editor_elem:
            typed = self.scanner.type_into_element(editor_elem, text_to_type)
            if typed:
                return ToolResult(
                    success=True,
                    tool=self.name,
                    message=f"Typed: '{text_to_type}'",
                    data={"text": text_to_type},
                    execution_success=True,
                )
        else:
            self.controller.type_arabic(text_to_type)
            return ToolResult(
                success=True,
                tool=self.name,
                message=f"Typed: '{text_to_type}'",
                data={"text": text_to_type},
                execution_success=True,
            )

        return ToolResult(
            success=False,
            tool=self.name,
            error="Could not type into active window",
            retryable=True,
            failure_reason=FailureReason.APP_NOT_READY,
            execution_success=False,
        )

    def observe(self, target: str, **kwargs) -> Observation:
        w_title, cur_elements = self.scanner.scan_active_window(max_elements=30)
        editor_elem = next((e for e in cur_elements if e.control_type in ("Edit", "Document")), None)
        observed_val = None
        if editor_elem and editor_elem.raw_control:
            try:
                val_pat = editor_elem.raw_control.GetValuePattern()
                if val_pat:
                    observed_val = val_pat.Value
            except Exception:
                pass
            if observed_val is None:
                observed_val = editor_elem.value

        if observed_val is not None:
            return Observation(
                source="uia",
                description=f"Observed text in editor: '{str(observed_val)[:40]}'",
                data={"text": observed_val, "window_title": w_title},
            )
        return Observation(
            source="uia",
            description="Editor text unavailable from UI",
            data={"text": None, "window_title": w_title},
        )

    def get_verifier(self) -> Optional[Verifier]:
        return self.verifier

    def reobserve(self) -> None:
        self.scanner.scan_active_window(max_elements=30)


class InAppSearchTool(BaseTool):
    name = "in_app_search"
    description = "Searches for an item, song, or text inside the active or targeted app"

    def __init__(self, scanner=None):
        self.scanner = scanner or accessibility_scanner
        self.verifier = SearchVerifier()

    def execute(self, target: str, **kwargs) -> ToolResult:
        auto_play = kwargs.get("auto_play", False)
        ok, s_msg = self.scanner.universal_in_app_search(target, auto_play=auto_play)
        return ToolResult(
            success=ok,
            tool=self.name,
            message=s_msg,
            data={"query": target, "auto_play": auto_play},
            execution_success=ok,
        )

    def observe(self, target: str, **kwargs) -> Observation:
        w_title, _ = self.scanner.scan_active_window(max_elements=20)
        return Observation(
            source="app",
            description=f"In-app search performed in window '{w_title}'",
            data={
                "window_title": w_title,
                "browser_active": True,
                "target_in_title": target.lower() in w_title.lower(),
                "results_loaded": True,
            },
        )

    def get_verifier(self) -> Optional[Verifier]:
        return self.verifier
