"""
Web Tools for JEV Tool Registry.
Includes WebNavigationTool (with autonomous top-result clicker) and GoogleSearchTool.
"""

import urllib.parse
import subprocess
import time
from typing import Optional, Dict, Any
from src.tools.base import BaseTool
from src.core.tool_result import ToolResult, FailureReason, VerificationStatus
from src.core.observation import Observation
from src.core.accessibility_scanner import accessibility_scanner
from src.verification.verifier import SearchVerifier, Verifier


class WebNavigationTool(BaseTool):
    name = "web_navigation"
    description = "Navigates directly to websites or autonomous search-and-click navigation"

    def __init__(self, scanner=None):
        self.scanner = scanner or accessibility_scanner
        self.verifier = SearchVerifier()

    def execute(self, target: str, **kwargs) -> ToolResult:
        url = kwargs.get("url")
        is_search_site = kwargs.get("is_search_site", False)
        auto_click_top = kwargs.get("auto_click_top", True)

        if not url:
            url = f"https://www.google.com/search?q={urllib.parse.quote(target)}"

        subprocess.Popen(f'start "" "{url}"', shell=True)
        time.sleep(0.8)

        # Autonomous Navigation: If searching for an unknown site/portal, click the top search result link
        if is_search_site and auto_click_top:
            try:
                clicked = self.scanner.click_top_search_result(query_hint=target, auto_wait=1.2)
                if clicked:
                    return ToolResult(
                        success=True,
                        tool=self.name,
                        message=f"Navigated to '{target}' via top search result.",
                        data={"url": url, "target": target, "auto_navigated": True},
                        execution_success=True,
                    )
            except Exception as e:
                print(f"[DEBUG] Notice on autonomous search result navigation: {e}")

        return ToolResult(
            success=True,
            tool=self.name,
            message=f"Opened '{target}' in browser.",
            data={"url": url, "target": target},
            execution_success=True,
        )

    def observe(self, target: str, **kwargs) -> Observation:
        w_title, _ = self.scanner.scan_active_window(max_elements=15)
        browser_active = any(
            b in w_title.lower()
            for b in ["chrome", "edge", "firefox", "brave", "opera", "browser", "github", "anghami", "spotify", "youtube", "soundcloud", target.lower()]
        )
        target_in_title = target.lower() in w_title.lower() or any(term.lower() in w_title.lower() for term in target.split() if len(term) > 2)
        return Observation(
            source="browser",
            description=f"Active browser window is '{w_title}'",
            data={
                "window_title": w_title,
                "browser_active": browser_active,
                "target_in_title": target_in_title,
                "results_loaded": browser_active and (target_in_title or bool(w_title and w_title != "Desktop")),
            },
        )

    def get_verifier(self) -> Optional[Verifier]:
        return self.verifier


class GoogleSearchTool(BaseTool):
    name = "web_search"
    description = "Searches Google for informational queries"

    def __init__(self, scanner=None):
        self.scanner = scanner or accessibility_scanner
        self.verifier = SearchVerifier()

    def execute(self, target: str, **kwargs) -> ToolResult:
        url = f"https://www.google.com/search?q={urllib.parse.quote(target)}"
        subprocess.Popen(f'start "" "{url}"', shell=True)
        time.sleep(0.8)
        return ToolResult(
            success=True,
            tool=self.name,
            message=f"Opened Google search for '{target}'.",
            data={"url": url, "query": target},
            execution_success=True,
        )

    def observe(self, target: str, **kwargs) -> Observation:
        w_title, _ = self.scanner.scan_active_window(max_elements=15)
        browser_active = any(b in w_title.lower() for b in ["chrome", "edge", "firefox", "brave", "opera", "google", "search"])
        target_in_title = target.lower() in w_title.lower() or "google" in w_title.lower() or "search" in w_title.lower()
        return Observation(
            source="browser",
            description=f"Active search window is '{w_title}'",
            data={
                "window_title": w_title,
                "browser_active": browser_active,
                "target_in_title": target_in_title,
                "results_loaded": browser_active,
            },
        )

    def get_verifier(self) -> Optional[Verifier]:
        return self.verifier
