import os
import re
import time
import urllib.parse
import urllib.request
from typing import List, Tuple
from typesafe_sdk import TypeSafeClient, Choice, Score, Noul
from src.config import TYPESAFE_API_KEY, MAX_STEPS_PER_COMMAND, STEP_PAUSE_SECONDS, TEMP_DIR
from src.core.os_controller import OSController
from src.core.app_resolver import WindowsAppResolver
from src.core.accessibility_scanner import accessibility_scanner, UIElement
import pyautogui
import pyperclip

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

    def _get_active_window_info(self) -> str:
        try:
            active = self.scanner.get_active_window()
            if active and active.Name:
                return active.Name
        except Exception:
            pass
        return "Desktop"

    def _decompose_into_steps(self, goal: str) -> Tuple[List[str], bool]:
        """
        Decomposes compound voice commands into an ordered list of atomic sub-tasks
        and extracts contextual modifiers like 'and play it / وشغلها'.
        """
        g = goal.strip()
        norm = g.lower()

        # Check if this is a standalone playback/resume command (e.g. "شغل الاغنيه", "شغل الموسيقى")
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
                r'\s+و(?=(?:افتح|اكتب|اضغط|دوس|انقر|احفظ|اقفل|دور|سيرش|ابحث|type|click|save|open|launch|search))\s*',
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
        elif any(w in t for w in ["spotify", "سبوتيفاي", "سبوتفاي"]):
            platform = "spotify"
        elif any(w in t for w in ["google", "جوجل", "كروم", "chrome", "المتصفح", "browser"]):
            platform = "google"

        c = t
        # 1. Remove platform mentions
        c = re.sub(
            r'\b(يوتيوب\s+ميوز[كي]|youtube\s+music|يوتيوب|اليوتيوب|youtube|سبوتيفاي|سبوتفاي|spotify|جوجل|google|كروم|chrome|المتصفح|browser)\b',
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

    def execute_goal(self, goal_arabic: str, on_step_callback=None) -> str:
        """
        Main entry point: Decomposes compound goals into steps and executes them
        in a verified Agentic Loop.
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

        step_results = []
        for idx, step_text in enumerate(steps, 1):
            if self.controller.stop_requested:
                return "Operation stopped by user."

            step_prefix = f"[Step {idx}/{total_steps}] " if total_steps > 1 else ""
            print(f"\n{step_prefix}Executing: '{step_text}'")
            if on_step_callback:
                on_step_callback("status", f"🎯 {step_prefix}{step_text}")

            result = self._execute_single_step(step_text, idx, total_steps, global_auto_play, on_step_callback)
            step_results.append(result)

            # Adaptive delay between steps to allow UI rendering
            if idx < total_steps:
                time.sleep(0.7)

        if total_steps > 1:
            final_msg = f"Completed all {total_steps} steps successfully."
            print(f"\n[SUMMARY] {final_msg}\n")
            if on_step_callback:
                on_step_callback("finished", final_msg)
            return final_msg
        else:
            return step_results[0] if step_results else "Executed."

    def _execute_single_step(
        self, step_goal: str, step_idx: int, total_steps: int, auto_play_override: bool = False, on_step_callback=None
    ) -> str:
        """Executes an atomic sub-task."""
        norm_goal = self.scanner._normalize_text(step_goal)

        # -------------------------------------------------------------
        # 1. Global Media Controls (Play / Pause / Next / Prev)
        # -------------------------------------------------------------
        if any(w in norm_goal for w in ["وقف الاغنيه", "وقف الموسيقي", "وقف التراك", "وقف", "ايقاف", "pause music", "pause song", "pause"]):
            print("[ACTION] Pausing media playback")
            self.controller.press_key("playpause")
            msg = "Media playback paused."
            if on_step_callback:
                on_step_callback("finished", msg)
            return msg

        if norm_goal in ["شغل الاغنيه", "كمل الاغنيه", "شغل الموسيقي", "كمل", "استئناف", "resume", "resume music", "play music"]:
            print("[ACTION] Resuming media playback")
            self.controller.press_key("playpause")
            msg = "Media playback resumed."
            if on_step_callback:
                on_step_callback("finished", msg)
            return msg

        if any(w in norm_goal for w in ["بعدها", "بعده", "التالي", "التاليه", "نكست", "next song", "next track", "next", "skip"]):
            print("[ACTION] Skipping to next track")
            self.controller.press_key("nexttrack")
            msg = "Skipped to next track."
            if on_step_callback:
                on_step_callback("finished", msg)
            return msg

        if any(w in norm_goal for w in ["قبلها", "قبله", "السابق", "السابقه", "بريفيوس", "previous song", "prev track", "previous", "prev", "back"]):
            print("[ACTION] Going back to previous track")
            self.controller.press_key("prevtrack")
            msg = "Returned to previous track."
            if on_step_callback:
                on_step_callback("finished", msg)
            return msg

        # -------------------------------------------------------------
        # 2. Smart Platform Detection & Clean Search Query Execution
        # -------------------------------------------------------------
        platform, clean_query = self._extract_clean_entities(step_goal)
        should_play = auto_play_override or any(w in norm_goal for w in ["شغل", "play", "listen", "اسمع"])

        # A. YouTube Music
        if platform == "youtube_music":
            print(f"[ACTION] Processing YouTube Music query: '{clean_query}' (Auto-Play: {should_play})")
            if on_step_callback:
                on_step_callback("action", f"🎵 YouTube Music: '{clean_query}'...")

            video_id = ""
            if should_play:
                print(f"[ACTION] Looking up top track for '{clean_query}' on YouTube Music...")
                video_id = find_top_youtube_video_id(clean_query + " audio") or find_top_youtube_video_id(clean_query)

            if video_id:
                url = f"https://music.youtube.com/watch?v={video_id}"
                print(f"[ACTION] Directly launching YouTube Music track (ID: {video_id})")
                import subprocess
                subprocess.Popen(f'start "" "{url}"', shell=True)
                final_msg = f"Playing '{clean_query}' on YouTube Music."
            else:
                url = f"https://music.youtube.com/search?q={urllib.parse.quote(clean_query)}"
                print(f"[ACTION] Opening YouTube Music search page")
                import subprocess
                subprocess.Popen(f'start "" "{url}"', shell=True)
                final_msg = f"Opened YouTube Music search for '{clean_query}'."

            if on_step_callback:
                on_step_callback("finished", final_msg)
            return final_msg

        # B. YouTube Videos
        if platform == "youtube":
            print(f"[ACTION] Processing YouTube query: '{clean_query}' (Auto-Play: {should_play})")
            if on_step_callback:
                on_step_callback("action", f"🎥 YouTube: '{clean_query}'...")

            video_id = ""
            if should_play:
                video_id = find_top_youtube_video_id(clean_query)

            if video_id:
                url = f"https://www.youtube.com/watch?v={video_id}"
                print(f"[ACTION] Directly launching YouTube video (ID: {video_id})")
                import subprocess
                subprocess.Popen(f'start "" "{url}"', shell=True)
                final_msg = f"Playing '{clean_query}' on YouTube."
            else:
                url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(clean_query)}"
                import subprocess
                subprocess.Popen(f'start "" "{url}"', shell=True)
                final_msg = f"Opened YouTube search for '{clean_query}'."

            if on_step_callback:
                on_step_callback("finished", final_msg)
            return final_msg

        # C. Spotify Auto-Play / Search
        is_music_intent = (platform == "spotify") or any(w in norm_goal for w in ["اغنيه", "تراك", "موسيقي", "مغني", "song", "track", "music"]) or (
            norm_goal.startswith("شغل ") and not any(app in norm_goal for app in ["المفكره", "الحاسبه", "الرسام", "المتصفح", "كروم", "رايدر", "كود", "calc", "notepad"])
        )

        if is_music_intent:
            print(f"[ACTION] Controlling Spotify for query: '{clean_query}' (Auto-Play: {should_play})")
            if on_step_callback:
                on_step_callback("action", f"🎵 Spotify: '{clean_query}' (AutoPlay: {should_play})...")

            # 1. Launch or activate Spotify
            self.app_resolver.launch("spotify")
            self.controller.wait(0.8)

            # 2. Focus Spotify window
            try:
                import uiautomation as auto
                with auto.UIAutomationInitializerInThread():
                    spotify_win = auto.WindowControl(searchDepth=1, SubName="Spotify")
                    if spotify_win.Exists(maxSearchSeconds=1.5):
                        spotify_win.SetActive()
                        spotify_win.SetFocus()
            except Exception:
                pass

            # 3. Spotify Quick Search shortcut (Ctrl + K is instant in Spotify desktop)
            pyautogui.hotkey("ctrl", "k")
            time.sleep(0.2)
            pyperclip.copy(clean_query)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.4)  # Allow Spotify overlay to populate top result

            if should_play:
                # In Spotify Quick Search, Enter immediately plays the top result!
                pyautogui.press("enter")
                time.sleep(0.2)
                final_msg = f"Playing '{clean_query}' on Spotify."
            else:
                pyautogui.press("enter")
                final_msg = f"Searched for '{clean_query}' on Spotify."

            print(f"[RESULT] {final_msg}")
            if on_step_callback:
                on_step_callback("finished", final_msg)
            return final_msg

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
                print(f"[ACTION] Clicking '{target_elem.name}' inside '{window_title}'")
                if on_step_callback:
                    on_step_callback("thought", thought)
                    on_step_callback("action", f"🖱️ Clicking: '{target_elem.name}' inside '{window_title}'...")

                success = self.scanner.click_element(target_elem)
                if success:
                    final_msg = f"Clicked '{target_elem.name}' successfully."
                    print(f"[RESULT] {final_msg}")
                    if on_step_callback:
                        on_step_callback("finished", final_msg)
                    return final_msg

        # -------------------------------------------------------------
        # 4. Jev System One Decision Engine
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
            err_msg = f"❌ Error contacting Jev Decision Model: {e}"
            print(f"[ERROR] {err_msg}")
            if on_step_callback:
                on_step_callback("error", err_msg)
            return err_msg

        action = jev_response.answers["primary_action"].choice
        target_app = jev_response.answers["target_app"].choice
        shortcut = jev_response.answers["shortcut_type"].choice
        confidence = jev_response.answers["primary_action"].confidence

        thought = f"Jev Decision: {action} (Target: {target_app}) | Latency: {latency_ms}ms | Confidence: {int(confidence*100)}%"
        print(f"[THOUGHT] {thought}")
        if on_step_callback:
            on_step_callback("thought", thought)

        if self.controller.stop_requested:
            return "Operation stopped."

        final_message = "Step executed successfully."

        # -------------------------------------------------------------
        # 5. Action Execution
        # -------------------------------------------------------------
        if action == "in_app_search":
            if target_app != "none" and target_app not in window_title.lower():
                print(f"[ACTION] Launching targeted app: '{target_app}'")
                if on_step_callback:
                    on_step_callback("action", f"⚡ Launching '{target_app}'...")
                self.app_resolver.launch(target_app)
                self.controller.wait(1.2)

            print(f"[ACTION] Searching '{clean_query}' inside active app")
            if on_step_callback:
                on_step_callback("action", f"🔍 Searching '{clean_query}' inside active app...")

            success, search_msg = self.scanner.universal_in_app_search(clean_query, auto_play=should_play)
            final_message = search_msg

        elif action == "click_ui_element":
            match_res = self.scanner.find_best_match(step_goal, ui_elements)
            if match_res:
                target_elem, conf = match_res
                print(f"[ACTION] Clicking UI element: [{target_elem.control_type}] '{target_elem.name}'")
                if on_step_callback:
                    on_step_callback("action", f"🖱️ Clicking: [{target_elem.control_type}] '{target_elem.name}'...")
                self.scanner.click_element(target_elem)
                final_message = f"Clicked '{target_elem.name}'."
            else:
                final_message = "Requested UI element not found in active window."

        elif action == "launch_app":
            app_query = target_app if target_app != "none" else step_goal
            print(f"[ACTION] Launching application: '{app_query}'")
            if on_step_callback:
                on_step_callback("action", f"⚡ Launching '{app_query}'...")

            success, launch_msg = self.app_resolver.launch(app_query)
            final_message = launch_msg
            self.controller.wait(0.8)

        elif action == "web_search":
            print(f"[ACTION] Opening web search for: '{clean_query}'")
            if on_step_callback:
                on_step_callback("action", f"🌐 Searching Google for: {clean_query}...")

            url = f"https://www.google.com/search?q={urllib.parse.quote(clean_query)}"
            import subprocess
            subprocess.Popen(f'start "" "{url}"', shell=True)
            self.controller.wait(1.0)
            final_message = f"Opened Google search for: {clean_query}"

        elif action == "math_calculate":
            print("[ACTION] Launching Calculator and calculating expression")
            if on_step_callback:
                on_step_callback("action", "🔢 Launching Calculator...")
            import subprocess
            subprocess.Popen("start calc", shell=True)
            self.controller.wait(1.0)
            math_text = re.sub(r'[^\d\+\-\*\/\.\(\)\=]', '', step_goal)
            if math_text:
                self.controller.type_arabic(math_text)
                self.controller.press_key("enter")
            final_message = "Opened Calculator and evaluated expression."

        elif action == "type_text":
            text_to_type = clean_query
            print(f"[ACTION] Typing text into active document: '{text_to_type}'")
            if on_step_callback:
                on_step_callback("action", f"✍️ Typing: '{text_to_type}'...")
            
            editor_elem = next((e for e in ui_elements if e.control_type in ("Edit", "Document")), None)
            if editor_elem:
                self.scanner.type_into_element(editor_elem, text_to_type)
            else:
                self.controller.type_arabic(text_to_type)
            final_message = f"Typed: {text_to_type}"

        elif action == "keyboard_shortcut":
            print(f"[ACTION] Executing shortcut: {shortcut}")
            if shortcut == "close_window":
                self.controller.hotkey(["alt", "f4"])
                final_message = "Closed window."
            elif shortcut == "minimize_all":
                self.controller.hotkey(["win", "d"])
                final_message = "Minimized all windows."
            elif shortcut == "copy":
                self.controller.hotkey(["ctrl", "c"])
                final_message = "Copied to clipboard."
            elif shortcut == "paste":
                self.controller.hotkey(["ctrl", "v"])
                final_message = "Pasted from clipboard."
            elif shortcut == "select_all":
                self.controller.hotkey(["ctrl", "a"])
                final_message = "Selected all."
            elif shortcut == "save":
                self.controller.hotkey(["ctrl", "s"])
                final_message = "Saved document (Ctrl + S)."
            elif shortcut == "enter":
                self.controller.press_key("enter")
                final_message = "Pressed Enter."
            else:
                self.controller.press_key(shortcut)
                final_message = f"Executed shortcut: {shortcut}."

        elif action == "volume_control":
            if any(w in norm_goal for w in ["علي", "ارفع", "up", "raise", "increase"]):
                for _ in range(5):
                    self.controller.press_key("volumeup")
                final_message = "Increased system volume."
            elif any(w in norm_goal for w in ["وطي", "اخفض", "down", "lower", "decrease"]):
                for _ in range(5):
                    self.controller.press_key("volumedown")
                final_message = "Decreased system volume."
            else:
                self.controller.press_key("volumemute")
                final_message = "Toggled system mute."

        print(f"[RESULT] {final_message}")
        if on_step_callback:
            on_step_callback("finished", final_message)

        return final_message
