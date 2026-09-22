"""
Session State & Context Memory for JEV (Phase 3 Foundation).
Maintains short-term conversational context across voice turns, allowing resolution
of anaphoric pronouns and contextual follow-ups in Arabic and English
(e.g., 'اقفله', 'احفظه', 'شغل غيرها', 'انسخه').
"""

import time
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class SessionTurn:
    timestamp: float
    goal: str
    action: str
    target: str
    platform: Optional[str] = None
    window_title: Optional[str] = None
    success: bool = True


class SessionState:
    """
    Sliding session memory maintaining current desktop context and recent turn history.
    """

    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.last_active_app: Optional[str] = None
        self.last_target: Optional[str] = None
        self.last_platform: Optional[str] = None
        self.last_search_query: Optional[str] = None
        self.last_window_title: Optional[str] = None
        self.history: List[SessionTurn] = []

    def record_turn(
        self,
        goal: str,
        action: str,
        target: str,
        platform: Optional[str] = None,
        window_title: Optional[str] = None,
        success: bool = True,
    ):
        """Records a completed step/turn into sliding memory."""
        turn = SessionTurn(
            timestamp=time.time(),
            goal=goal,
            action=action,
            target=target,
            platform=platform,
            window_title=window_title,
            success=success,
        )
        self.history.append(turn)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        if success:
            if action == "launch_app" or (target and action not in ("volume_up", "volume_down", "volume_mute")):
                self.last_active_app = target
            if platform and platform != "default":
                self.last_platform = platform
            if action in ("web_search", "in_app_search", "youtube", "youtube_music", "spotify", "anghami", "soundcloud"):
                self.last_search_query = target
            self.last_target = target
            if window_title and window_title not in ("Desktop", "Unknown Window"):
                self.last_window_title = window_title

    def resolve_contextual_query(self, query: str) -> str:
        """
        Resolves Arabic & English contextual pronouns into explicit intent.
        Examples:
          - 'اقفله' / 'اقفلها' -> 'اقفل النافذة'
          - 'احفظه' / 'احفظها' -> 'احفظ الملف'
          - 'شغل غيرها' / 'هات غيرها' -> 'التالي'
          - 'شغلها' / 'شغله' -> 'شغل {last_search_query}' (if last search was recorded)
          - 'انسخه' -> 'نسخ'
          - 'الصقه' -> 'لصق'
        """
        q = query.strip()
        norm = q.lower()

        # Pronoun pattern for close: اقفله / اقفلها / close it
        if norm in ("اقفله", "اقفلها", "قفلها", "قفله", "اغلقه", "اغلقها", "close it"):
            return "اقفل النافذة"

        # Pronoun pattern for save: احفظه / احفظها / سيفه / سيفها / save it
        if norm in ("احفظه", "احفظها", "سيفه", "سيفها", "save it"):
            return "احفظ الملف"

        # Pronoun pattern for copy/paste: انسخه / الصقه / copy it / paste it
        if norm in ("انسخه", "انسخها", "copy it"):
            return "نسخ"
        if norm in ("الصقه", "الصقها", "paste it"):
            return "لصق"

        # Pronoun pattern for next/skip: شغل غيرها / هات غيرها / هات اللي بعدها / play another
        if norm in ("شغل غيرها", "هات غيرها", "غيرها", "play another", "play next"):
            return "التالي"

        # Pronoun pattern for play last: شغلها / شغله (when a query was previously set)
        if norm in ("شغلها", "شغله", "play it") and self.last_search_query:
            if self.last_platform:
                return f"شغل {self.last_search_query} في {self.last_platform}"
            return f"شغل {self.last_search_query}"

        return q

    def clear(self):
        """Clears session history and context."""
        self.last_active_app = None
        self.last_target = None
        self.last_platform = None
        self.last_search_query = None
        self.last_window_title = None
        self.history.clear()


# Global singleton
session_state = SessionState()
