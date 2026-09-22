"""
System Tools for JEV Tool Registry.
Includes VolumeTool, WindowManagementTool, DocumentShortcutTool, and MathCalculateTool.
"""

import subprocess
import re
from typing import Optional, Dict, Any, List
from src.tools.base import BaseTool
from src.core.tool_result import ToolResult, FailureReason, VerificationStatus
from src.core.observation import Observation
from src.core.os_controller import OSController
from src.verification.verifier import Verifier


class VolumeTool(BaseTool):
    name = "volume_control"
    description = "Increases, decreases, or mutes master system volume"

    def __init__(self, os_controller: Optional[OSController] = None):
        self.controller = os_controller or OSController()

    def execute(self, target: str, **kwargs) -> ToolResult:
        t = target.lower().strip()
        if t in ("up", "volume_up", "raise", "increase"):
            for _ in range(5):
                self.controller.press_key("volumeup")
            msg = "Increased system volume."
        elif t in ("down", "volume_down", "lower", "decrease"):
            for _ in range(5):
                self.controller.press_key("volumedown")
            msg = "Decreased system volume."
        elif t in ("mute", "volume_mute", "unmute"):
            self.controller.press_key("volumemute")
            msg = "Toggled system mute."
        else:
            self.controller.press_key("volumeup")
            msg = "Adjusted system volume."

        return ToolResult(
            success=True,
            tool=self.name,
            message=msg,
            verification_status=VerificationStatus.UNAVAILABLE,
            execution_success=True,
        )


class WindowManagementTool(BaseTool):
    name = "window_management"
    description = "Manages desktop window states (close window, minimize all / show desktop)"

    def __init__(self, os_controller: Optional[OSController] = None):
        self.controller = os_controller or OSController()

    def execute(self, target: str, **kwargs) -> ToolResult:
        t = target.lower().strip()
        if t in ("close", "close_window", "alt_f4"):
            self.controller.hotkey(["alt", "f4"])
            msg = "Closed active window."
        elif t in ("minimize", "minimize_all", "show_desktop", "win_d"):
            self.controller.hotkey(["win", "d"])
            msg = "Minimized all windows."
        else:
            self.controller.hotkey(["alt", "f4"])
            msg = f"Executed window action: {t}."

        return ToolResult(
            success=True,
            tool=self.name,
            message=msg,
            verification_status=VerificationStatus.UNAVAILABLE,
            execution_success=True,
        )


class DocumentShortcutTool(BaseTool):
    name = "document_shortcut"
    description = "Dispatches document editing hotkeys (save, copy, paste, select all, enter)"

    def __init__(self, os_controller: Optional[OSController] = None):
        self.controller = os_controller or OSController()

    def execute(self, target: str, **kwargs) -> ToolResult:
        t = target.lower().strip()
        if t in ("save", "save_file", "ctrl_s"):
            self.controller.hotkey(["ctrl", "s"])
            msg = "Saved document (Ctrl + S)."
        elif t in ("copy", "ctrl_c"):
            self.controller.hotkey(["ctrl", "c"])
            msg = "Copied to clipboard."
        elif t in ("paste", "ctrl_v"):
            self.controller.hotkey(["ctrl", "v"])
            msg = "Pasted from clipboard."
        elif t in ("select_all", "ctrl_a"):
            self.controller.hotkey(["ctrl", "a"])
            msg = "Selected all."
        elif t in ("enter", "return"):
            self.controller.press_key("enter")
            msg = "Pressed Enter."
        elif t in ("escape", "esc"):
            self.controller.press_key("escape")
            msg = "Pressed Escape."
        else:
            self.controller.press_key(t)
            msg = f"Executed shortcut: {t}."

        return ToolResult(
            success=True,
            tool=self.name,
            message=msg,
            verification_status=VerificationStatus.UNAVAILABLE,
            execution_success=True,
        )


class MathCalculateTool(BaseTool):
    name = "math_calculate"
    description = "Opens Windows Calculator and computes mathematical expressions"

    def __init__(self, os_controller: Optional[OSController] = None):
        self.controller = os_controller or OSController()

    def execute(self, target: str, **kwargs) -> ToolResult:
        subprocess.Popen("start calc", shell=True)
        self.controller.wait(0.8)
        math_text = re.sub(r'[^\d\+\-\*\/\.\(\)\=]', '', target)
        if math_text:
            self.controller.type_arabic(math_text)
            self.controller.press_key("enter")
        return ToolResult(
            success=True,
            tool=self.name,
            message="Opened Calculator and evaluated expression.",
            verification_status=VerificationStatus.UNAVAILABLE,
            execution_success=True,
        )
