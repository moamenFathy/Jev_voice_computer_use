"""
Media & Streaming Tools for JEV Tool Registry.
Includes YouTube Music, YouTube, Spotify, Anghami, SoundCloud, and Win32 Hardware Media Controls.
"""

import urllib.parse
import subprocess
import time
import re
from typing import Optional, Dict, Any
from src.tools.base import BaseTool
from src.core.tool_result import ToolResult, FailureReason, VerificationStatus
from src.core.observation import Observation
from src.core.os_controller import OSController
from src.core.accessibility_scanner import accessibility_scanner
from src.core.app_resolver import WindowsAppResolver
from src.verification.verifier import SearchVerifier, Verifier
import pyautogui
import pyperclip


def find_top_youtube_video_id(query: str, timeout: float = 2.5) -> str:
    """Fast network lookup to get the exact #1 YouTube/YouTube Music video ID."""
    import urllib.request
    try:
        q = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={q}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        html = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8")
        video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
        seen = set()
        for vid in video_ids:
            if vid not in seen:
                return vid
    except Exception:
        pass
    return ""


class YouTubeMusicTool(BaseTool):
    name = "youtube_music"
    description = "Searches or directly plays audio tracks on YouTube Music"

    def __init__(self, scanner=None):
        self.scanner = scanner or accessibility_scanner
        self.verifier = SearchVerifier()

    def execute(self, target: str, **kwargs) -> ToolResult:
        should_play = kwargs.get("should_play", True)
        video_id = ""
        if should_play:
            video_id = find_top_youtube_video_id(target + " audio") or find_top_youtube_video_id(target)

        if video_id:
            url = f"https://music.youtube.com/watch?v={video_id}"
            subprocess.Popen(f'start "" "{url}"', shell=True)
            msg = f"Playing '{target}' on YouTube Music."
        else:
            url = f"https://music.youtube.com/search?q={urllib.parse.quote(target)}"
            subprocess.Popen(f'start "" "{url}"', shell=True)
            msg = f"Opened YouTube Music search for '{target}'."

        return ToolResult(
            success=True,
            tool=self.name,
            message=msg,
            data={"url": url, "video_id": video_id, "query": target},
            execution_success=True,
        )

    def observe(self, target: str, **kwargs) -> Observation:
        w_title, _ = self.scanner.scan_active_window(max_elements=15)
        browser_active = any(b in w_title.lower() for b in ["chrome", "edge", "firefox", "brave", "opera", "youtube", "music"])
        return Observation(
            source="browser",
            description=f"Active media window is '{w_title}'",
            data={
                "window_title": w_title,
                "browser_active": browser_active,
                "target_in_title": "youtube" in w_title.lower() or "music" in w_title.lower() or target.lower() in w_title.lower(),
                "results_loaded": browser_active,
            },
        )

    def get_verifier(self) -> Optional[Verifier]:
        return self.verifier


class YouTubeTool(BaseTool):
    name = "youtube"
    description = "Searches or directly plays videos on YouTube"

    def __init__(self, scanner=None):
        self.scanner = scanner or accessibility_scanner
        self.verifier = SearchVerifier()

    def execute(self, target: str, **kwargs) -> ToolResult:
        should_play = kwargs.get("should_play", True)
        video_id = ""
        if should_play:
            video_id = find_top_youtube_video_id(target)

        if video_id:
            url = f"https://www.youtube.com/watch?v={video_id}"
            subprocess.Popen(f'start "" "{url}"', shell=True)
            msg = f"Playing '{target}' on YouTube."
        else:
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(target)}"
            subprocess.Popen(f'start "" "{url}"', shell=True)
            msg = f"Opened YouTube search for '{target}'."

        return ToolResult(
            success=True,
            tool=self.name,
            message=msg,
            data={"url": url, "video_id": video_id, "query": target},
            execution_success=True,
        )

    def observe(self, target: str, **kwargs) -> Observation:
        w_title, _ = self.scanner.scan_active_window(max_elements=15)
        browser_active = any(b in w_title.lower() for b in ["chrome", "edge", "firefox", "brave", "opera", "youtube"])
        return Observation(
            source="browser",
            description=f"Active media window is '{w_title}'",
            data={
                "window_title": w_title,
                "browser_active": browser_active,
                "target_in_title": "youtube" in w_title.lower() or target.lower() in w_title.lower(),
                "results_loaded": browser_active,
            },
        )

    def get_verifier(self) -> Optional[Verifier]:
        return self.verifier


class SpotifyTool(BaseTool):
    name = "spotify"
    description = "Searches and auto-plays tracks in the Spotify desktop app"

    def __init__(self, app_resolver: Optional[WindowsAppResolver] = None, scanner=None, os_controller: Optional[OSController] = None):
        self.resolver = app_resolver or WindowsAppResolver()
        self.scanner = scanner or accessibility_scanner
        self.controller = os_controller or OSController()
        self.verifier = SearchVerifier()

    def execute(self, target: str, **kwargs) -> ToolResult:
        should_play = kwargs.get("should_play", True)
        self.resolver.launch("spotify")
        self.controller.wait(0.8)

        try:
            import uiautomation as auto
            with auto.UIAutomationInitializerInThread():
                spotify_win = auto.WindowControl(searchDepth=1, SubName="Spotify")
                if spotify_win.Exists(maxSearchSeconds=1.5):
                    spotify_win.SetActive()
                    spotify_win.SetFocus()
        except Exception as e:
            print(f"[DEBUG] Notice on Spotify window activation: {e}")

        pyautogui.hotkey("ctrl", "k")
        time.sleep(0.2)
        pyperclip.copy(target)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.4)

        if should_play:
            pyautogui.press("down")
            time.sleep(0.15)
            pyautogui.press("enter")
            time.sleep(0.3)
            msg = f"Playing '{target}' on Spotify."
        else:
            pyautogui.press("enter")
            msg = f"Searched for '{target}' on Spotify."

        return ToolResult(
            success=True,
            tool=self.name,
            message=msg,
            data={"query": target, "auto_play": should_play},
            execution_success=True,
        )

    def observe(self, target: str, **kwargs) -> Observation:
        w_title, _ = self.scanner.scan_active_window(max_elements=15)
        spotify_active = "spotify" in w_title.lower()
        return Observation(
            source="spotify",
            description=f"Active Spotify window is '{w_title}'",
            data={
                "window_title": w_title,
                "browser_active": spotify_active,
                "target_in_title": spotify_active,
                "results_loaded": spotify_active,
            },
        )

    def get_verifier(self) -> Optional[Verifier]:
        return self.verifier


class AnghamiTool(BaseTool):
    name = "anghami"
    description = "Searches and plays music on Anghami web player"

    def __init__(self, scanner=None):
        self.scanner = scanner or accessibility_scanner
        self.verifier = SearchVerifier()

    def execute(self, target: str, **kwargs) -> ToolResult:
        url = f"https://play.anghami.com/search?query={urllib.parse.quote(target)}"
        subprocess.Popen(f'start "" "{url}"', shell=True)
        return ToolResult(
            success=True,
            tool=self.name,
            message=f"Opened Anghami search for '{target}'.",
            data={"url": url, "query": target},
            execution_success=True,
        )

    def observe(self, target: str, **kwargs) -> Observation:
        w_title, _ = self.scanner.scan_active_window(max_elements=15)
        browser_active = any(b in w_title.lower() for b in ["chrome", "edge", "firefox", "brave", "opera", "anghami"])
        return Observation(
            source="browser",
            description=f"Active media window is '{w_title}'",
            data={
                "window_title": w_title,
                "browser_active": browser_active,
                "target_in_title": "anghami" in w_title.lower(),
                "results_loaded": browser_active,
            },
        )

    def get_verifier(self) -> Optional[Verifier]:
        return self.verifier


class SoundCloudTool(BaseTool):
    name = "soundcloud"
    description = "Searches tracks on SoundCloud web player"

    def __init__(self, scanner=None):
        self.scanner = scanner or accessibility_scanner
        self.verifier = SearchVerifier()

    def execute(self, target: str, **kwargs) -> ToolResult:
        url = f"https://soundcloud.com/search?q={urllib.parse.quote(target)}"
        subprocess.Popen(f'start "" "{url}"', shell=True)
        return ToolResult(
            success=True,
            tool=self.name,
            message=f"Opened SoundCloud search for '{target}'.",
            data={"url": url, "query": target},
            execution_success=True,
        )

    def observe(self, target: str, **kwargs) -> Observation:
        w_title, _ = self.scanner.scan_active_window(max_elements=15)
        browser_active = any(b in w_title.lower() for b in ["chrome", "edge", "firefox", "brave", "opera", "soundcloud"])
        return Observation(
            source="browser",
            description=f"Active media window is '{w_title}'",
            data={
                "window_title": w_title,
                "browser_active": browser_active,
                "target_in_title": "soundcloud" in w_title.lower(),
                "results_loaded": browser_active,
            },
        )

    def get_verifier(self) -> Optional[Verifier]:
        return self.verifier


class MediaPlaybackTool(BaseTool):
    name = "media_playback"
    description = "Dispatches hardware Win32 multimedia keys (pause, resume, next, prev)"
    is_idempotent: bool = False

    def __init__(self, os_controller: Optional[OSController] = None):
        self.controller = os_controller or OSController()

    def execute(self, target: str, **kwargs) -> ToolResult:
        t = target.lower().strip()
        if t in ("pause", "stop", "media_pause"):
            self.controller.press_key("playpause")
            msg = "Media playback paused."
        elif t in ("resume", "play", "media_resume"):
            self.controller.press_key("playpause")
            msg = "Media playback resumed."
        elif t in ("next", "media_next", "nexttrack"):
            self.controller.press_key("nexttrack")
            msg = "Skipped to next track."
        elif t in ("prev", "previous", "media_prev", "prevtrack"):
            self.controller.press_key("prevtrack")
            msg = "Returned to previous track."
        else:
            self.controller.press_key("playpause")
            msg = f"Dispatched media playback command: {t}."

        return ToolResult(
            success=True,
            tool=self.name,
            message=msg,
            verification_status=VerificationStatus.UNAVAILABLE,
            execution_success=True,
        )
