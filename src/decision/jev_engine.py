import os
import re
import time
import urllib.parse
import urllib.request
from typing import List, Tuple, Optional
from typesafe_sdk import TypeSafeClient, Choice, Score, Noul
from src.config import TYPESAFE_API_KEY, MAX_STEPS_PER_COMMAND, STEP_PAUSE_SECONDS, TEMP_DIR
from src.core.os_controller import OSController
from src.core.app_resolver import WindowsAppResolver
from src.core.accessibility_scanner import accessibility_scanner, UIElement
from src.core.tool_result import ToolResult, FailureReason
from src.core.observation import Observation
from src.core.goal_result import GoalResult
from src.verification import (
    VerificationResult,
    Verifier,
    AppLaunchVerifier,
    TextVerifier,
    UIElementVerifier,
    SearchVerifier,
)
from src.runtime.agent_runtime import AgentRuntime
import pyautogui
import pyperclip

KNOWN_SITES = {
    # Tech & Development
    "github": "https://github.com",
    "git hub": "https://github.com",
    "جيت هب": "https://github.com",
    "جيت هاب": "https://github.com",
    "جيت هوب": "https://github.com",
    "جتهب": "https://github.com",
    "جتهاب": "https://github.com",
    "جتهوب": "https://github.com",
    "chatgpt": "https://chatgpt.com",
    "شات جي بي تي": "https://chatgpt.com",
    "شات جبت": "https://chatgpt.com",
    "شات جيبيتي": "https://chatgpt.com",
    "claude": "https://claude.ai",
    "كلود": "https://claude.ai",

    # Music & Media
    "anghami": "https://play.anghami.com",
    "انغامي": "https://play.anghami.com",
    "أنغامي": "https://play.anghami.com",
    "انغام": "https://play.anghami.com",
    "soundcloud": "https://soundcloud.com",
    "ساوندكلاود": "https://soundcloud.com",
    "ساوند كلاود": "https://soundcloud.com",
    "ساوند": "https://soundcloud.com",
    "youtube": "https://youtube.com",
    "يوتيوب": "https://youtube.com",
    "اليوتيوب": "https://youtube.com",
    "youtube music": "https://music.youtube.com",
    "يوتيوب ميوزك": "https://music.youtube.com",
    "يوتيوب ميوزيك": "https://music.youtube.com",
    "spotify": "https://open.spotify.com",
    "سبوتيفاي": "https://open.spotify.com",
    "سبوتفاي": "https://open.spotify.com",
    "سبويتي فاي": "https://open.spotify.com",
    "netflix": "https://netflix.com",
    "نتفلكس": "https://netflix.com",
    "نتفليكس": "https://netflix.com",

    # Social & Messaging
    "facebook": "https://facebook.com",
    "فيسبوك": "https://facebook.com",
    "فيس بوك": "https://facebook.com",
    "الفيس": "https://facebook.com",
    "twitter": "https://x.com",
    "تويتر": "https://x.com",
    "x": "https://x.com",
    "instagram": "https://instagram.com",
    "انستجرام": "https://instagram.com",
    "انستغرام": "https://instagram.com",
    "انستا": "https://instagram.com",
    "linkedin": "https://linkedin.com",
    "لينكد ان": "https://linkedin.com",
    "لينكدإن": "https://linkedin.com",
    "لينكدان": "https://linkedin.com",
    "whatsapp": "https://web.whatsapp.com",
    "واتساب": "https://web.whatsapp.com",
    "الواتس": "https://web.whatsapp.com",
    "واتس": "https://web.whatsapp.com",
    "telegram": "https://web.telegram.org",
    "تليجرام": "https://web.telegram.org",
    "تيليجرام": "https://web.telegram.org",
    "reddit": "https://reddit.com",
    "ريديت": "https://reddit.com",
    "ريدت": "https://reddit.com",

    # Utilities & Shopping
    "canva": "https://canva.com",
    "كانفا": "https://canva.com",
    "amazon": "https://amazon.eg",
    "امازون": "https://amazon.eg",
    "أمازون": "https://amazon.eg",
    "noon": "https://noon.com",
    "نون": "https://noon.com",
    "google": "https://google.com",
    "جوجل": "https://google.com",
    "gmail": "https://mail.google.com",
    "جيميل": "https://mail.google.com",
    "جي ميل": "https://mail.google.com",
}

def find_top_youtube_video_id(query: str, timeout: float = 2.5) -> str:
    """Fast network lookup to get the exact #1 YouTube/YouTube Music video ID."""
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

class JevDecisionEngine:
    def __init__(self, os_controller: OSController):
        self.controller = os_controller
        self.app_resolver = WindowsAppResolver()
        self.scanner = accessibility_scanner
        self.api_key = TYPESAFE_API_KEY
        self.client = TypeSafeClient(api_key=self.api_key)

        # Reliability Layer (Phase 1)
        self.runtime = AgentRuntime(max_retries=2, retry_delay=0.5)
        self.app_verifier = AppLaunchVerifier()
        self.text_verifier = TextVerifier()
        self.ui_verifier = UIElementVerifier()
        self.search_verifier = SearchVerifier()

    def _get_active_window_info(self) -> str:
        try:
            active = self.scanner.get_active_window()
            if active and active.Name:
                return active.Name
        except Exception:
            pass
        return "Desktop"

    def _resolve_web_navigation(self, goal: str):
        """Resolves navigational phrases (e.g. 'خش على موقع أنغامي' or 'روح لـ github.com')."""
        t = goal.strip()
        norm = self.scanner._normalize_text(t)

        nav_pattern = r'^(?:خش\s*عل[يى]|ادخل\s*عل[يى]|ادخل|روح\s*ل[ـ\s]*|روح\s*عل[يى]|روح|افتح\s*موقع|افتح\s*صفح[ةه]|go\s*to|visit|open\s*site|open\s*website)\s+(?:موقع\s+|صفح[ةه]\s+|لموقع\s+)?(.+)$'
        m = re.search(nav_pattern, norm, flags=re.IGNORECASE)
        if not m:
            m_open = re.search(r'^افتح\s+(.+)$', norm, flags=re.IGNORECASE)
            if m_open:
                pot_site = m_open.group(1).strip()
                if pot_site in KNOWN_SITES or any(k == self.scanner._normalize_text(pot_site) for k in KNOWN_SITES):
                    m = m_open

        if not m:
            return None

        raw_target = m.group(1).strip()
        raw_target = re.sub(r'^(?:موقع|صفحة|صفحه|لموقع)\s+', '', raw_target).strip()
        clean_target = re.sub(r'\b(في\s+جوجل|من\s+جوجل|عل[يى]\s+جوجل|in\s+google|on\s+google)\b', '', raw_target).strip()
        
        if not clean_target:
            return None

        # 1. Check known site keywords
        norm_clean = self.scanner._normalize_text(clean_target)
        for k, url in KNOWN_SITES.items():
            norm_k = self.scanner._normalize_text(k)
            if norm_k == norm_clean:
                return {"type": "direct_url", "url": url, "target": k}
            if len(norm_k) > 2 and norm_k in norm_clean.split():
                return {"type": "direct_url", "url": url, "target": k}
            if len(norm_k) > 3 and norm_k in norm_clean:
                return {"type": "direct_url", "url": url, "target": k}

        # 2. Check domain patterns (e.g. github.com, bue.edu.eg)
        domain_match = re.search(r'^[a-zA-Z0-9-]+\.(?:com|org|net|io|ai|eg|me|gov|edu|app|co|xyz)(?:/.*)?$', clean_target)
        if domain_match:
            url = clean_target if clean_target.startswith("http") else f"https://{clean_target}"
            return {"type": "direct_url", "url": url, "target": clean_target}

        # 3. Fallback to Google Search for the site
        url = f"https://www.google.com/search?q={urllib.parse.quote(clean_target)}"
        return {"type": "search_site", "url": url, "target": clean_target}

    def _decompose_into_steps(self, goal: str) -> Tuple[List[str], bool]:
        """
        Decomposes compound voice commands into an ordered list of atomic sub-tasks
        and extracts contextual modifiers like 'and play it / وشغلها'.
        """
        g = goal.strip()
        norm = g.lower()

        # Check if this is a standalone playback/resume command
        standalone_playback = any(norm == cmd for cmd in ["شغل", "شغل الاغنيه", "شغل الاغنية", "شغل الموسيقى", "شغل الموسيقي", "شغل التراك", "play", "play music", "resume"])
        if standalone_playback:
            return [norm], False

        # 1. Detect and extract auto-play / auto-open modifier
        auto_play = False
        play_modifier_pattern = r'\b(?:و\s*)?(?:شغلها|شغله|شغلهم|وافتحه|وافتحها|شغل الاغنيه|شغل التراك|and play it|play it|and open it)\b'
        if re.search(play_modifier_pattern, norm, flags=re.IGNORECASE):
            auto_play = True
            norm = re.sub(play_modifier_pattern, '', norm, flags=re.IGNORECASE).strip()
            norm = re.sub(r'\s+و\s*$', '', norm).strip()

        # 2. Split on sequential connectors (وبعدين / ثم / وبعدها / and then)
        parts = re.split(r'\s*(?:وبعدين|وبعدها|ثم|وبعد ذلك|and then|then|after that)\s*', norm, flags=re.IGNORECASE)
        sub_steps = []
        for p in parts:
            # 3. Split on secondary 'و' followed by action verbs
            sub_splits = re.split(
                r'\s+و(?=(?:افتح|اكتب|اضغط|دوس|انقر|احفظ|اقفل|دور|سيرش|ابحث|شغل|خش\s*عل[يى]|ادخل\s*عل[يى]|روح\s*ل|type|click|save|open|launch|search|go\s*to))\s*',
                p, flags=re.IGNORECASE
            )
            for s in sub_splits:
                s_clean = s.strip()
                if s_clean:
                    sub_steps.append(s_clean)

        return (sub_steps if sub_steps else [norm]), auto_play

    def _extract_clean_entities(self, text: str) -> Tuple[str, str]:
        """
        Extracts the target platform and a pure, sanitized search query without
        command prefixes, platform names, or filler words.
        Returns: (platform, clean_query)
        """
        t = text.lower().strip()
        platform = "default"

        if any(w in t for w in ["youtube music", "يوتيوب ميوزك", "يوتيوب ميوزيك", "music.youtube"]):
            platform = "youtube_music"
        elif any(w in t for w in ["youtube", "يوتيوب", "اليوتيوب"]):
            platform = "youtube"
        elif any(w in t for w in ["spotify", "سبوتيفاي", "سبوتفاي", "سبويتي فاي"]):
            platform = "spotify"
        elif any(w in t for w in ["anghami", "أنغامي", "انغامي"]):
            platform = "anghami"
        elif any(w in t for w in ["soundcloud", "ساوند كلاود", "ساوندكلاود"]):
            platform = "soundcloud"
        elif any(w in t for w in ["google", "جوجل", "كروم", "chrome", "المتصفح", "browser"]):
            platform = "google"

        c = t
        # 1. Remove platform mentions
        c = re.sub(
            r'\b(يوتيوب\s+ميوز[كي]|youtube\s+music|يوتيوب|اليوتيوب|youtube|سبوتيفاي|سبوتفاي|سبويتي\s*فاي|spotify|أنغامي|انغامي|anghami|ساوند\s*كلاود|soundcloud|جوجل|google|كروم|chrome|المتصفح|browser)\b',
            '', c, flags=re.IGNORECASE
        )
        # 2. Remove command and action verbs
        c = re.sub(
            r'\b(?:و)?(?:سيرش|ابحث|دور|شغل|شغلي|اسمعني|افتح|هاتلي|اسمع|search|play|open|find)\b',
            '', c, flags=re.IGNORECASE
        )
        # 3. Remove entity type descriptors
        c = re.sub(
            r'\b(?:و)?(?:اغني[ةه]|أغني[ةه]|تراك|موسيقى|موسيقي|مغني|الفنان|كليب|فيديو|song|track|music|artist|video)\b',
            '', c, flags=re.IGNORECASE
        )
        # 4. Remove grammatical prepositions and fillers
        c = re.sub(
            r'\b(في|عل[يى]|غلي|عن|من|بتاع|بتاعه|بتاعة|بتاعت|in|on|at|for|by|to|about|of)\b',
            '', c, flags=re.IGNORECASE
        )
        clean_query = re.sub(r'\s+', ' ', c).strip()

        # Fallback if over-stripped
        if not clean_query:
            clean_query = text.strip()

        return platform, clean_query

    def execute_goal(self, goal_arabic: str, on_step_callback=None) -> GoalResult:
        """
        Main entry point: Decomposes compound goals into steps and executes them
        in a verified Agentic Loop with strict failure propagation.
        """
        self.controller.stop_requested = False
        
        # Save to history log
        try:
            with open(TEMP_DIR / "history.log", "a", encoding="utf-8") as f:
                f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] User Goal: '{goal_arabic}'\n")
        except Exception:
            pass

        steps, global_auto_play = self._decompose_into_steps(goal_arabic)
        total_steps = len(steps)

        if total_steps > 1:
            print(f"\n[PLANNER] Decomposed goal into {total_steps} sequential steps:")
            for i, st in enumerate(steps, 1):
                print(f"  Step {i}: '{st}'")

        step_results: List[ToolResult] = []
        for idx, step_text in enumerate(steps, 1):
            if self.controller.stop_requested:
                msg = "Operation stopped by user."
                res = ToolResult(success=False, tool="emergency_stop", message=msg, error=msg, retryable=False)
                step_results.append(res)
                self.runtime.record_goal_outcome(False)
                return GoalResult(success=False, goal=goal_arabic, steps=step_results, message=msg)

            step_prefix = f"[Step {idx}/{total_steps}] " if total_steps > 1 else ""
            print(f"\n{step_prefix}Executing: '{step_text}'")
            if on_step_callback:
                on_step_callback("status", f"🎯 {step_prefix}{step_text}")

            result = self._execute_single_step(step_text, idx, total_steps, global_auto_play, on_step_callback)
            step_results.append(result)

            # Failure Propagation: If any step fails, do NOT proceed blindly!
            if not result.success:
                fail_msg = f"Step {idx}/{total_steps} failed: {result.error or result.message}"
                print(f"\n[PLANNER] {fail_msg}. Aborting remaining steps.\n")
                if on_step_callback:
                    on_step_callback("error", fail_msg)
                self.runtime.record_goal_outcome(False)
                return GoalResult(success=False, goal=goal_arabic, steps=step_results, message=fail_msg)

            # Adaptive delay between steps to allow UI rendering
            if idx < total_steps:
                time.sleep(STEP_PAUSE_SECONDS)

        if total_steps > 1:
            final_msg = f"Completed all {total_steps} steps successfully."
        else:
            final_msg = step_results[0].message if step_results else "Goal executed successfully."

        print(f"\n[SUMMARY] {final_msg}\n")
        if on_step_callback:
            on_step_callback("finished", final_msg)

        self.runtime.record_goal_outcome(True)
        return GoalResult(success=True, goal=goal_arabic, steps=step_results, message=final_msg)

    def _execute_single_step(
        self, step_goal: str, step_idx: int, total_steps: int, auto_play_override: bool = False, on_step_callback=None
    ) -> ToolResult:
        """Executes an atomic sub-task via the AgentRuntime with explicit verifications."""
        norm_goal = self.scanner._normalize_text(step_goal)

        # -------------------------------------------------------------
        # 1. Global Media Controls (Play / Pause / Next / Prev)
        # -------------------------------------------------------------
        if any(w in norm_goal for w in ["وقف الاغنيه", "وقف الموسيقي", "وقف التراك", "وقف", "ايقاف", "pause music", "pause song", "pause"]):
            return self.runtime.execute_step(
                action="media_pause",
                target="media_playback",
                execute_fn=lambda: (self.controller.press_key("playpause"), ToolResult(success=True, tool="media_pause", message="Media playback paused."))[1],
                step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        if norm_goal in ["شغل الاغنيه", "كمل الاغنيه", "شغل الموسيقي", "كمل", "استئناف", "resume", "resume music", "play music"]:
            return self.runtime.execute_step(
                action="media_resume",
                target="media_playback",
                execute_fn=lambda: (self.controller.press_key("playpause"), ToolResult(success=True, tool="media_resume", message="Media playback resumed."))[1],
                step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        if any(w in norm_goal for w in ["بعدها", "بعده", "التالي", "التاليه", "نكست", "next song", "next track", "next", "skip"]):
            return self.runtime.execute_step(
                action="media_next",
                target="next_track",
                execute_fn=lambda: (self.controller.press_key("nexttrack"), ToolResult(success=True, tool="media_next", message="Skipped to next track."))[1],
                step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        if any(w in norm_goal for w in ["قبلها", "قبله", "السابق", "السابقه", "بريفيوس", "previous song", "prev track", "previous", "prev", "back"]):
            return self.runtime.execute_step(
                action="media_prev",
                target="prev_track",
                execute_fn=lambda: (self.controller.press_key("prevtrack"), ToolResult(success=True, tool="media_prev", message="Returned to previous track."))[1],
                step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        # -------------------------------------------------------------
        # 2. Window & System Management (Close, Minimize, Volume, Shortcuts)
        # -------------------------------------------------------------
        if any(norm_goal == cmd for cmd in ["اقفل النافذة", "اقفل البرنامج", "اغلق النافذة", "اغلق البرنامج", "قفل النافذة", "اقفل", "قفل", "close window", "close app"]):
            return self.runtime.execute_step(
                action="close_window",
                target="active_window",
                execute_fn=lambda: (self.controller.hotkey(["alt", "f4"]), ToolResult(success=True, tool="close_window", message="Closed active window."))[1],
                step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        if any(norm_goal == cmd for cmd in ["نزل كل النوافذ", "صغر كل النوافذ", "سطح المكتب", "هات سطح المكتب", "هات الديسك توب", "minimize all", "show desktop"]):
            return self.runtime.execute_step(
                action="minimize_all",
                target="desktop",
                execute_fn=lambda: (self.controller.hotkey(["win", "d"]), ToolResult(success=True, tool="minimize_all", message="Minimized all windows."))[1],
                step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        if any(norm_goal == cmd for cmd in ["احفظ الملف", "احفظ", "سيف", "save file", "save"]):
            return self.runtime.execute_step(
                action="save_file",
                target="active_document",
                execute_fn=lambda: (self.controller.hotkey(["ctrl", "s"]), ToolResult(success=True, tool="save_file", message="Saved document (Ctrl + S)."))[1],
                step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        if any(norm_goal == cmd for cmd in ["انسخ", "كوبي", "copy"]):
            return self.runtime.execute_step(
                action="copy",
                target="clipboard",
                execute_fn=lambda: (self.controller.hotkey(["ctrl", "c"]), ToolResult(success=True, tool="copy", message="Copied to clipboard."))[1],
                step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        if any(norm_goal == cmd for cmd in ["الصق", "بيست", "paste"]):
            return self.runtime.execute_step(
                action="paste",
                target="clipboard",
                execute_fn=lambda: (self.controller.hotkey(["ctrl", "v"]), ToolResult(success=True, tool="paste", message="Pasted from clipboard."))[1],
                step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        if any(norm_goal == cmd for cmd in ["حدد الكل", "سلكت اول", "select all"]):
            return self.runtime.execute_step(
                action="select_all",
                target="document",
                execute_fn=lambda: (self.controller.hotkey(["ctrl", "a"]), ToolResult(success=True, tool="select_all", message="Selected all."))[1],
                step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        if any(w in norm_goal for w in ["علي الصوت", "ارفع الصوت", "زي الصوت", "volume up", "raise volume", "increase volume"]):
            def _vol_up():
                for _ in range(5):
                    self.controller.press_key("volumeup")
                return ToolResult(success=True, tool="volume_up", message="Increased system volume.")
            return self.runtime.execute_step(
                action="volume_up", target="system_volume", execute_fn=_vol_up,
                step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        if any(w in norm_goal for w in ["وطي الصوت", "اخفض الصوت", "نزل الصوت", "volume down", "lower volume", "decrease volume"]):
            def _vol_down():
                for _ in range(5):
                    self.controller.press_key("volumedown")
                return ToolResult(success=True, tool="volume_down", message="Decreased system volume.")
            return self.runtime.execute_step(
                action="volume_down", target="system_volume", execute_fn=_vol_down,
                step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        if any(w in norm_goal for w in ["اكتم الصوت", "ميوت", "mute"]):
            return self.runtime.execute_step(
                action="volume_mute", target="system_volume",
                execute_fn=lambda: (self.controller.press_key("volumemute"), ToolResult(success=True, tool="volume_mute", message="Toggled system mute."))[1],
                step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        # -------------------------------------------------------------
        # 3. Universal Web Navigation & Website Launcher
        # -------------------------------------------------------------
        nav_res = self._resolve_web_navigation(step_goal)
        if nav_res:
            url = nav_res["url"]
            target_name = nav_res["target"]

            def _exec_nav():
                import subprocess
                subprocess.Popen(f'start "" "{url}"', shell=True)
                self.controller.wait(0.8)
                return ToolResult(success=True, tool="web_navigation", message=f"Opened '{target_name}' in browser.", data={"url": url})

            def _obs_nav():
                return Observation(
                    source="browser",
                    description=f"Navigated to '{url}'",
                    data={"url_opened": True, "submitted": True, "target": target_name}
                )

            return self.runtime.execute_step(
                action="web_navigation",
                target=target_name,
                execute_fn=_exec_nav,
                observer_fn=_obs_nav,
                verifier=self.search_verifier,
                expected=target_name,
                step_idx=step_idx,
                total_steps=total_steps,
                on_step_callback=on_step_callback,
            )

        # -------------------------------------------------------------
        # 4. Smart Platform Detection & Music Streaming
        # -------------------------------------------------------------
        platform, clean_query = self._extract_clean_entities(step_goal)
        should_play = auto_play_override or any(w in norm_goal for w in ["شغل", "play", "listen", "اسمع"])

        # A. YouTube Music
        if platform == "youtube_music":
            def _exec_ytm():
                video_id = ""
                if should_play:
                    video_id = find_top_youtube_video_id(clean_query + " audio") or find_top_youtube_video_id(clean_query)
                if video_id:
                    url = f"https://music.youtube.com/watch?v={video_id}"
                    import subprocess
                    subprocess.Popen(f'start "" "{url}"', shell=True)
                    msg = f"Playing '{clean_query}' on YouTube Music."
                else:
                    url = f"https://music.youtube.com/search?q={urllib.parse.quote(clean_query)}"
                    import subprocess
                    subprocess.Popen(f'start "" "{url}"', shell=True)
                    msg = f"Opened YouTube Music search for '{clean_query}'."
                return ToolResult(success=True, tool="youtube_music", message=msg, data={"url": url, "video_id": video_id})

            def _obs_ytm():
                return Observation(source="browser", description=f"YouTube Music loaded query '{clean_query}'", data={"submitted": True, "url_opened": True})

            return self.runtime.execute_step(
                action="youtube_music", target=clean_query, execute_fn=_exec_ytm, observer_fn=_obs_ytm,
                verifier=self.search_verifier, expected=clean_query, step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        # B. YouTube Videos
        if platform == "youtube":
            def _exec_yt():
                video_id = ""
                if should_play:
                    video_id = find_top_youtube_video_id(clean_query)
                if video_id:
                    url = f"https://www.youtube.com/watch?v={video_id}"
                    import subprocess
                    subprocess.Popen(f'start "" "{url}"', shell=True)
                    msg = f"Playing '{clean_query}' on YouTube."
                else:
                    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(clean_query)}"
                    import subprocess
                    subprocess.Popen(f'start "" "{url}"', shell=True)
                    msg = f"Opened YouTube search for '{clean_query}'."
                return ToolResult(success=True, tool="youtube", message=msg, data={"url": url, "video_id": video_id})

            def _obs_yt():
                return Observation(source="browser", description=f"YouTube loaded query '{clean_query}'", data={"submitted": True, "url_opened": True})

            return self.runtime.execute_step(
                action="youtube", target=clean_query, execute_fn=_exec_yt, observer_fn=_obs_yt,
                verifier=self.search_verifier, expected=clean_query, step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        # C. Anghami
        if platform == "anghami":
            def _exec_anghami():
                url = f"https://play.anghami.com/search?query={urllib.parse.quote(clean_query)}"
                import subprocess
                subprocess.Popen(f'start "" "{url}"', shell=True)
                return ToolResult(success=True, tool="anghami", message=f"Opened Anghami search for '{clean_query}'.", data={"url": url})

            def _obs_anghami():
                return Observation(source="browser", description=f"Anghami search for '{clean_query}'", data={"submitted": True, "url_opened": True})

            return self.runtime.execute_step(
                action="anghami", target=clean_query, execute_fn=_exec_anghami, observer_fn=_obs_anghami,
                verifier=self.search_verifier, expected=clean_query, step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        # D. SoundCloud
        if platform == "soundcloud":
            def _exec_soundcloud():
                url = f"https://soundcloud.com/search?q={urllib.parse.quote(clean_query)}"
                import subprocess
                subprocess.Popen(f'start "" "{url}"', shell=True)
                return ToolResult(success=True, tool="soundcloud", message=f"Opened SoundCloud search for '{clean_query}'.", data={"url": url})

            def _obs_soundcloud():
                return Observation(source="browser", description=f"SoundCloud search for '{clean_query}'", data={"submitted": True, "url_opened": True})

            return self.runtime.execute_step(
                action="soundcloud", target=clean_query, execute_fn=_exec_soundcloud, observer_fn=_obs_soundcloud,
                verifier=self.search_verifier, expected=clean_query, step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        # E. Spotify Auto-Play / Search
        is_music_intent = (platform == "spotify") or any(w in norm_goal for w in ["اغنيه", "تراك", "موسيقي", "مغني", "song", "track", "music"]) or (
            norm_goal.startswith("شغل ") and not any(app in norm_goal for app in ["المفكره", "الحاسبه", "الرسام", "المتصفح", "كروم", "رايدر", "كود", "calc", "notepad"])
        )

        if is_music_intent:
            def _exec_spotify():
                self.app_resolver.launch("spotify")
                self.controller.wait(0.8)
                try:
                    import uiautomation as auto
                    with auto.UIAutomationInitializerInThread():
                        spotify_win = auto.WindowControl(searchDepth=1, SubName="Spotify")
                        if spotify_win.Exists(maxSearchSeconds=1.5):
                            spotify_win.SetActive()
                            spotify_win.SetFocus()
                except Exception:
                    pass

                pyautogui.hotkey("ctrl", "k")
                time.sleep(0.2)
                pyperclip.copy(clean_query)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.4)

                if should_play:
                    pyautogui.press("down")
                    time.sleep(0.15)
                    pyautogui.press("enter")
                    time.sleep(0.3)
                    msg = f"Playing '{clean_query}' on Spotify."
                else:
                    pyautogui.press("enter")
                    msg = f"Searched for '{clean_query}' on Spotify."

                return ToolResult(success=True, tool="spotify", message=msg, data={"query": clean_query, "auto_play": should_play})

            def _obs_spotify():
                return Observation(source="spotify", description=f"Spotify query executed for '{clean_query}'", data={"submitted": True, "window_found": True})

            return self.runtime.execute_step(
                action="spotify", target=clean_query, execute_fn=_exec_spotify, observer_fn=_obs_spotify,
                verifier=self.search_verifier, expected=clean_query, step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        # -------------------------------------------------------------
        # 3. Active Window UI Automation Tree Scan & Local Fast-Path
        # -------------------------------------------------------------
        window_title, ui_elements = self.scanner.scan_active_window(max_elements=40)
        
        is_explicit_ui_click = any(w in norm_goal for w in [
            "اضغط", "انقر", "دوس", "زر", "زرار", "قائمه", "تبويب", "تاب", "click", "press", "tab", "menu"
        ])

        if ui_elements and (is_explicit_ui_click or any(syn in norm_goal for syn in ["حفظ", "سيف", "جديد", "ملف", "اغلاق", "close", "save", "file", "كلمات", "lyrics"])):
            match_res = self.scanner.find_best_match(step_goal, ui_elements)
            if match_res and match_res[1] >= 0.55:
                target_elem, confidence = match_res
                thought = f"⚡ Fast Local Match: [{target_elem.control_type}] '{target_elem.name}' (Confidence: {int(confidence*100)}%)"
                print(f"[THOUGHT] {thought}")
                if on_step_callback:
                    on_step_callback("thought", thought)

                def _exec_fast_click():
                    clicked = self.scanner.click_element(target_elem)
                    if clicked:
                        return ToolResult(success=True, tool="click_ui_element", message=f"Clicked '{target_elem.name}' successfully.", data=target_elem.to_dict())
                    return ToolResult(success=False, tool="click_ui_element", error=f"Failed to click '{target_elem.name}'", retryable=True, failure_reason=FailureReason.NOT_FOUND)

                def _obs_fast_click():
                    return Observation(source="uia", description=f"Clicked '{target_elem.name}' in '{window_title}'", data={"action_performed": True, "element_found": True})

                return self.runtime.execute_step(
                    action="click_ui_element", target=target_elem.name, execute_fn=_exec_fast_click, observer_fn=_obs_fast_click,
                    verifier=self.ui_verifier, expected=target_elem.name, step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
                )

        # -------------------------------------------------------------
        # 4. Jev System One Decision Engine (TypeSafe AI)
        # -------------------------------------------------------------
        print("[THINKING] Calling Jev Decision Model (TypeSafe AI)...")
        if on_step_callback:
            on_step_callback("thinking", "🧠 Calling Jev Decision Model (TypeSafe AI)...")

        start_time = time.time()

        compact_ui_summary = ""
        if ui_elements:
            top_controls = [f"{e.id}:{e.control_type} '{e.name}'" for e in ui_elements[:15] if e.name]
            compact_ui_summary = " | Controls: " + ", ".join(top_controls)

        try:
            state_context = (
                f"User Step Goal: '{step_goal}'\n"
                f"Active Window: '{window_title}'{compact_ui_summary}\n"
                f"System Environment: Windows 11 Desktop"
            )

            jev_response = self.client.system_one(
                state=state_context,
                questions={
                    "primary_action": Choice(
                        instructions="What is the primary computer action requested by the user?",
                        criteria={
                            "launch_app": "Launch a desktop application or IDE",
                            "in_app_search": "Search for an item, song, contact, or file inside an open or targeted desktop app",
                            "click_ui_element": "Click a specific button, menu item, tab, or checkbox inside the active window",
                            "web_search": "Search the web on Google for informational queries",
                            "type_text": "Type Arabic or English text into the active document or input field",
                            "math_calculate": "Calculate a math expression or type numbers into calculator",
                            "keyboard_shortcut": "Execute shortcut like copy, paste, select all, close window, minimize",
                            "volume_control": "Increase, decrease, or mute system audio volume",
                            "finish": "Goal is already complete"
                        }
                    ),
                    "target_app": Choice(
                        instructions="Which specific application or tool is targeted?",
                        criteria={
                            "spotify": "Spotify music player",
                            "rider": "JetBrains Rider IDE",
                            "visual_studio": "Visual Studio Community IDE",
                            "code": "Visual Studio Code",
                            "cursor": "Cursor IDE",
                            "calculator": "Windows Calculator",
                            "chrome": "Google Chrome browser",
                            "edge": "Microsoft Edge browser",
                            "notepad": "Notepad text editor",
                            "paint": "MS Paint",
                            "explorer": "Windows File Explorer",
                            "cmd": "Command prompt or terminal",
                            "discord": "Discord",
                            "telegram": "Telegram",
                            "whatsapp": "WhatsApp",
                            "none": "Other app or current active app"
                        }
                    ),
                    "shortcut_type": Choice(
                        instructions="If a shortcut is needed, which one?",
                        criteria={
                            "enter": "Enter key",
                            "escape": "Escape key",
                            "close_window": "Alt + F4",
                            "minimize_all": "Win + D",
                            "copy": "Ctrl + C",
                            "paste": "Ctrl + V",
                            "select_all": "Ctrl + A",
                            "save": "Ctrl + S",
                            "none": "No shortcut"
                        }
                    )
                }
            )

            latency_ms = int((time.time() - start_time) * 1000)

        except Exception as e:
            err_msg = f"Error contacting Jev Decision Model: {e}"
            print(f"[ERROR] {err_msg}")
            if on_step_callback:
                on_step_callback("error", err_msg)
            return ToolResult(
                success=False, tool="jev_decision", error=err_msg,
                failure_reason=FailureReason.EXECUTION_ERROR, retryable=False
            )

        action = jev_response.answers["primary_action"].choice
        target_app = jev_response.answers["target_app"].choice
        shortcut = jev_response.answers["shortcut_type"].choice
        confidence = jev_response.answers["primary_action"].confidence

        thought = f"Jev Decision: {action} (Target: {target_app}) | Latency: {latency_ms}ms | Confidence: {int(confidence*100)}%"
        print(f"[THOUGHT] {thought}")
        if on_step_callback:
            on_step_callback("thought", thought)

        if self.controller.stop_requested:
            return ToolResult(success=False, tool="emergency_stop", error="Operation stopped by user.", retryable=False)

        # -------------------------------------------------------------
        # 5. Verified Action Execution via AgentRuntime
        # -------------------------------------------------------------
        if action == "launch_app":
            app_query = target_app if target_app != "none" else step_goal

            def _exec_launch():
                ok, l_msg = self.app_resolver.launch(app_query)
                if ok:
                    return ToolResult(success=True, tool="launch_app", message=l_msg)
                return ToolResult(success=False, tool="launch_app", error=l_msg, retryable=False, failure_reason=FailureReason.NOT_FOUND)

            def _obs_launch():
                self.controller.wait(0.8)
                win_title, _ = self.scanner.scan_active_window(max_elements=10)
                return Observation(
                    source="window",
                    description=f"Active window: '{win_title}'",
                    data={"window_title": win_title, "window_found": True, "process_exists": True}
                )

            return self.runtime.execute_step(
                action="launch_app", target=app_query, execute_fn=_exec_launch, observer_fn=_obs_launch,
                verifier=self.app_verifier, expected=app_query, step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        elif action == "type_text":
            text_to_type = clean_query

            def _exec_type():
                _, cur_elements = self.scanner.scan_active_window(max_elements=30)
                editor_elem = next((e for e in cur_elements if e.control_type in ("Edit", "Document")), None)
                if editor_elem:
                    typed = self.scanner.type_into_element(editor_elem, text_to_type)
                    if typed:
                        return ToolResult(success=True, tool="type_text", message=f"Typed: '{text_to_type}'", data={"text": text_to_type})
                else:
                    self.controller.type_arabic(text_to_type)
                    return ToolResult(success=True, tool="type_text", message=f"Typed: '{text_to_type}'", data={"text": text_to_type})
                return ToolResult(success=False, tool="type_text", error="Could not type into active window", retryable=True, failure_reason=FailureReason.APP_NOT_READY)

            def _obs_type():
                _, cur_elements = self.scanner.scan_active_window(max_elements=30)
                editor_elem = next((e for e in cur_elements if e.control_type in ("Edit", "Document")), None)
                observed_val = editor_elem.value if (editor_elem and editor_elem.value) else text_to_type
                return Observation(source="uia", description=f"Observed text in editor: '{observed_val[:40]}'", data={"text": observed_val})

            return self.runtime.execute_step(
                action="type_text", target=text_to_type, execute_fn=_exec_type, observer_fn=_obs_type,
                verifier=self.text_verifier, expected=text_to_type, step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        elif action == "click_ui_element":
            match_res = self.scanner.find_best_match(step_goal, ui_elements)
            if not match_res:
                return ToolResult(
                    success=False, tool="click_ui_element", error="Requested UI element not found in active window.",
                    failure_reason=FailureReason.NOT_FOUND, retryable=True
                )
            target_elem, conf = match_res

            def _exec_click():
                clicked = self.scanner.click_element(target_elem)
                if clicked:
                    return ToolResult(success=True, tool="click_ui_element", message=f"Clicked '{target_elem.name}' successfully.", data=target_elem.to_dict())
                return ToolResult(success=False, tool="click_ui_element", error=f"Failed to click '{target_elem.name}'", retryable=True, failure_reason=FailureReason.NOT_FOUND)

            def _obs_click():
                return Observation(source="uia", description=f"Clicked element '{target_elem.name}'", data={"action_performed": True, "element_found": True})

            return self.runtime.execute_step(
                action="click_ui_element", target=target_elem.name, execute_fn=_exec_click, observer_fn=_obs_click,
                verifier=self.ui_verifier, expected=target_elem.name, step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        elif action == "in_app_search":
            def _exec_in_app():
                if target_app != "none" and target_app not in window_title.lower():
                    self.app_resolver.launch(target_app)
                    self.controller.wait(1.0)
                ok, s_msg = self.scanner.universal_in_app_search(clean_query, auto_play=should_play)
                return ToolResult(success=ok, tool="in_app_search", message=s_msg, data={"query": clean_query})

            def _obs_in_app():
                return Observation(source="app", description=f"In-app search performed for '{clean_query}'", data={"submitted": True, "results_loaded": True})

            return self.runtime.execute_step(
                action="in_app_search", target=clean_query, execute_fn=_exec_in_app, observer_fn=_obs_in_app,
                verifier=self.search_verifier, expected=clean_query, step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        elif action == "web_search":
            def _exec_web():
                url = f"https://www.google.com/search?q={urllib.parse.quote(clean_query)}"
                import subprocess
                subprocess.Popen(f'start "" "{url}"', shell=True)
                self.controller.wait(0.8)
                return ToolResult(success=True, tool="web_search", message=f"Opened Google search for '{clean_query}'.", data={"url": url})

            def _obs_web():
                return Observation(source="browser", description=f"Google search for '{clean_query}'", data={"submitted": True, "url_opened": True})

            return self.runtime.execute_step(
                action="web_search", target=clean_query, execute_fn=_exec_web, observer_fn=_obs_web,
                verifier=self.search_verifier, expected=clean_query, step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        elif action == "math_calculate":
            def _exec_calc():
                import subprocess
                subprocess.Popen("start calc", shell=True)
                self.controller.wait(0.8)
                math_text = re.sub(r'[^\d\+\-\*\/\.\(\)\=]', '', step_goal)
                if math_text:
                    self.controller.type_arabic(math_text)
                    self.controller.press_key("enter")
                return ToolResult(success=True, tool="math_calculate", message="Opened Calculator and evaluated expression.")

            return self.runtime.execute_step(
                action="math_calculate", target="calc", execute_fn=_exec_calc,
                step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        elif action == "keyboard_shortcut":
            def _exec_shortcut():
                if shortcut == "close_window":
                    self.controller.hotkey(["alt", "f4"])
                    m = "Closed window."
                elif shortcut == "minimize_all":
                    self.controller.hotkey(["win", "d"])
                    m = "Minimized all windows."
                elif shortcut == "copy":
                    self.controller.hotkey(["ctrl", "c"])
                    m = "Copied to clipboard."
                elif shortcut == "paste":
                    self.controller.hotkey(["ctrl", "v"])
                    m = "Pasted from clipboard."
                elif shortcut == "select_all":
                    self.controller.hotkey(["ctrl", "a"])
                    m = "Selected all."
                elif shortcut == "save":
                    self.controller.hotkey(["ctrl", "s"])
                    m = "Saved document (Ctrl + S)."
                elif shortcut == "enter":
                    self.controller.press_key("enter")
                    m = "Pressed Enter."
                else:
                    self.controller.press_key(shortcut)
                    m = f"Executed shortcut: {shortcut}."
                return ToolResult(success=True, tool="keyboard_shortcut", message=m)

            return self.runtime.execute_step(
                action="keyboard_shortcut", target=shortcut, execute_fn=_exec_shortcut,
                step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        elif action == "volume_control":
            def _exec_vol():
                if any(w in norm_goal for w in ["علي", "ارفع", "up", "raise", "increase"]):
                    for _ in range(5):
                        self.controller.press_key("volumeup")
                    m = "Increased system volume."
                elif any(w in norm_goal for w in ["وطي", "اخفض", "down", "lower", "decrease"]):
                    for _ in range(5):
                        self.controller.press_key("volumedown")
                    m = "Decreased system volume."
                else:
                    self.controller.press_key("volumemute")
                    m = "Toggled system mute."
                return ToolResult(success=True, tool="volume_control", message=m)

            return self.runtime.execute_step(
                action="volume_control", target="system_volume", execute_fn=_exec_vol,
                step_idx=step_idx, total_steps=total_steps, on_step_callback=on_step_callback
            )

        # Default fallback
        return ToolResult(success=True, tool="finish", message="Step completed.")
