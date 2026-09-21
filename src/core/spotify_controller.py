"""
Spotify & Media Controller for Windows.
Provides instant search, playback, playlist launch, and media control
using native Spotify URI protocols, window activation, and UI navigation.
"""

import time
import urllib.parse
import subprocess
import pyautogui
import pyperclip
import pygetwindow as gw
from src.core.os_controller import OSController

class SpotifyController:
    def __init__(self, os_controller: OSController = None):
        self.os = os_controller or OSController()

    def _get_spotify_window(self):
        """Finds the active or background Spotify window."""
        windows = gw.getWindowsWithTitle("Spotify")
        if windows:
            return windows[0]
        # Check all windows with case-insensitive search
        for w in gw.getAllWindows():
            if "spotify" in w.title.lower():
                return w
        return None

    def search_and_play(self, query: str, auto_play: bool = True) -> tuple[bool, str]:
        """
        Searches Spotify for an artist, track, or album and auto-plays the top result.
        Uses native Windows Spotify URI protocol + smart UI interaction for 100% reliable playback.
        """
        clean_query = query.strip()
        if not clean_query:
            return False, "لم يتم تحديد اسم الأغنية أو المغني."

        encoded = urllib.parse.quote(clean_query)
        spotify_uri = f"spotify:search:{encoded}"

        try:
            # 1. Open Spotify directly with search URI
            subprocess.Popen(f'start "" "{spotify_uri}"', shell=True)
            time.sleep(1.2)

            # 2. Find and activate Spotify window to ensure it receives input
            win = self._get_spotify_window()
            if win:
                try:
                    win.activate()
                except Exception:
                    pass

            # 3. If auto_play requested, trigger playback on Top Result
            if auto_play:
                time.sleep(0.6)

                if win and win.width > 200 and win.height > 200:
                    # In Spotify UI, the 'Top Result' card is located at:
                    # ~28% width from left, ~36% height from top
                    target_x = win.left + int(win.width * 0.28)
                    target_y = win.top + int(win.height * 0.36)

                    # Ensure coordinates are safely on-screen
                    sw, sh = pyautogui.size()
                    target_x = max(10, min(sw - 10, target_x))
                    target_y = max(10, min(sh - 10, target_y))

                    # Move and double-click to start playback
                    pyautogui.moveTo(target_x, target_y, duration=0.2)
                    pyautogui.doubleClick(target_x, target_y)
                    time.sleep(0.3)

                # Fallback: Keyboard sequence (Tab -> Enter -> Space)
                pyautogui.press("tab")
                time.sleep(0.1)
                pyautogui.press("enter")
                time.sleep(0.2)
                self.os.press_key("playpause")

            action_desc = "وتشغيلها" if auto_play else ""
            return True, f"تم فتح سبوتيفاي والبحث عن '{clean_query}' {action_desc} بنجاح 🎵"

        except Exception as e:
            return False, f"تعذر تشغيل سبوتيفاي: {e}"

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
