"""
Spotify & Media Controller for Windows.
Provides instant search, playback, playlist launch, and media control
using native Spotify URI protocols, Windows Multimedia keys, and UI Automation.
"""

import time
import urllib.parse
import subprocess
import pyautogui
import pyperclip
from src.core.os_controller import OSController
from src.core.accessibility_scanner import accessibility_scanner

class SpotifyController:
    def __init__(self, os_controller: OSController = None):
        self.os = os_controller or OSController()

    def search_and_play(self, query: str, auto_play: bool = True) -> tuple[bool, str]:
        """
        Searches Spotify for an artist, track, or album and optionally auto-plays the top result.
        Uses native Windows Spotify URI protocol for sub-second response.
        """
        clean_query = query.strip()
        if not clean_query:
            return False, "لم يتم تحديد اسم الأغنية أو المغني."

        encoded = urllib.parse.quote(clean_query)
        spotify_uri = f"spotify:search:{encoded}"

        try:
            # 1. Open Spotify directly into search results
            subprocess.Popen(f'start "" "{spotify_uri}"', shell=True)
            time.sleep(1.0)

            # 2. If auto_play requested, simulate Enter or Click top result
            if auto_play:
                time.sleep(0.5)
                # Press Enter to start playing top hit in Spotify
                pyautogui.press("enter")
                time.sleep(0.2)
                # Fallback: Space / Play key
                pyautogui.press("space")

            action_desc = "وتشغيلها" if auto_play else ""
            return True, f"تم فتح سبوتيفاي والبحث عن '{clean_query}' {action_desc} بنجاح."

        except Exception as e:
            # Fallback: If URI fails, focus Spotify window and use Ctrl+L
            try:
                subprocess.Popen('start "" "spotify:"', shell=True)
                time.sleep(0.8)
                pyautogui.hotkey("ctrl", "l")
                time.sleep(0.1)
                pyperclip.copy(clean_query)
                pyautogui.hotkey("ctrl", "v")
                pyautogui.press("enter")
                if auto_play:
                    time.sleep(0.6)
                    pyautogui.press("enter")
                return True, f"تم البحث عن '{clean_query}' في سبوتيفاي."
            except Exception as ex:
                return False, f"تعذر فتح سبوتيفاي: {ex}"

    def play_pause(self) -> str:
        """Toggles play/pause for Spotify or system media."""
        self.os.press_key("playpause")
        return "تم تبديل حالة التشغيل / الإيقاف المؤقت."

    def next_track(self) -> str:
        """Skips to next track in Spotify."""
        self.os.press_key("nexttrack")
        return "تم الانتقال إلى الأغنية التالية."

    def previous_track(self) -> str:
        """Goes back to previous track in Spotify."""
        self.os.press_key("prevtrack")
        return "تم الرجوع إلى الأغنية السابقة."

spotify_controller = SpotifyController()
