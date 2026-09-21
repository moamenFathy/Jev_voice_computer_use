import os
import re
import time
import urllib.parse
from typesafe_sdk import TypeSafeClient, Choice, Score, Noul
from src.config import TYPESAFE_API_KEY, MAX_STEPS_PER_COMMAND, STEP_PAUSE_SECONDS, TEMP_DIR
from src.core.os_controller import OSController
from src.core.app_resolver import WindowsAppResolver
from src.core.accessibility_scanner import accessibility_scanner, UIElement
from src.core.spotify_controller import spotify_controller

class JevDecisionEngine:
    def __init__(self, os_controller: OSController):
        self.controller = os_controller
        self.app_resolver = WindowsAppResolver()
        self.scanner = accessibility_scanner
        self.spotify = spotify_controller
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

    def _extract_spotify_query(self, text: str) -> str:
        cleaned = re.sub(
            r'^(شغل|افتح|ابحث عن|دور على|هاتلي|play|search for|open)\s+',
            '', text.strip(), flags=re.IGNORECASE
        )
        cleaned = re.sub(
            r'(على\s+سبوتيفاي|في\s+سبوتيفاي|سبوتيفاي|on\s+spotify|in\s+spotify|spotify)\s*',
            '', cleaned, flags=re.IGNORECASE
        )
        cleaned = re.sub(
            r'^(اغنية|أغنية|تراك|مغني|الفنان|موسيقى|song|track|artist)\s+',
            '', cleaned.strip(), flags=re.IGNORECASE
        )
        return cleaned.strip()

    def _extract_search_or_text(self, text: str) -> str:
        cleaned = re.sub(
            r'^(افتح|شغل|ابحث عن|ابحث في|دور على|اكتب|قوله|احسب|اضغط على|انقر على|دوس على|open|launch|search for|search|type|write|calculate|play|click|press)\s+',
            '', text.strip(), flags=re.IGNORECASE
        )
        cleaned = re.sub(
            r'^(المتصفح|جوجل|كروم|المفكرة|الآلة الحاسبة|اليوتيوب|سبوتيفاي|زر|زرار|خانة|حقل|browser|chrome|notepad|calculator|calc|youtube|google|spotify|button)\s+(and\s+)?(و)?(ابحث عن|واكتب|واحسب|تشغيل|play|type|write|search for|search)?\s*',
            '', cleaned, flags=re.IGNORECASE
        )
        return cleaned.strip()

    def execute_goal(self, goal_arabic: str, on_step_callback=None) -> str:
        self.controller.stop_requested = False
        
        # حفظ الأمر في سجل التاريخ
        try:
            with open(TEMP_DIR / "history.log", "a", encoding="utf-8") as f:
                f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] User Command: '{goal_arabic}'\n")
        except Exception:
            pass

        if on_step_callback:
            on_step_callback("status", f"🎯 الهدف: {goal_arabic}")

        lower_goal = goal_arabic.lower().strip()

        # -------------------------------------------------------------
        # 1. فحص أوامر الميديا و Spotify السريعة (Fast-Path Media & Spotify)
        # -------------------------------------------------------------
        if any(w in lower_goal for w in ["سبوتيفاي", "سبوتفاي", "spotify"]):
            spotify_query = self._extract_spotify_query(goal_arabic)
            if spotify_query and len(spotify_query) > 1:
                auto_play = any(w in lower_goal for w in ["شغل", "هاتلي", "اسمع", "play"])
                if on_step_callback:
                    on_step_callback("thought", f"⚡ مسار سبوتيفاي المباشر: البحث عن '{spotify_query}'")
                    on_step_callback("action", f"🎵 فتح سبوتيفاي وتشغيل '{spotify_query}'...")
                success, msg = self.spotify.search_and_play(spotify_query, auto_play=auto_play)
                if on_step_callback:
                    on_step_callback("finished", msg)
                return msg

        # أوامر التحكم في تشغيل الموسيقى
        if any(w in lower_goal for w in ["وقف الاغنية", "وقف الموسيقى", "وقف التراك", "pause music", "pause song"]):
            msg = self.spotify.play_pause()
            if on_step_callback:
                on_step_callback("finished", msg)
            return msg

        if any(w in lower_goal for w in ["كمل الاغنية", "شغل الاغنية", "شغل الموسيقى", "resume music", "play music"]):
            msg = self.spotify.play_pause()
            if on_step_callback:
                on_step_callback("finished", msg)
            return msg

        if any(w in lower_goal for w in ["الاغنية اللي بعدها", "التراك اللي بعده", "التالي", "next song", "next track"]):
            msg = self.spotify.next_track()
            if on_step_callback:
                on_step_callback("finished", msg)
            return msg

        if any(w in lower_goal for w in ["الاغنية اللي قبلها", "التراك اللي قبله", "السابق", "previous song", "prev track"]):
            msg = self.spotify.previous_track()
            if on_step_callback:
                on_step_callback("finished", msg)
            return msg

        # -------------------------------------------------------------
        # 2. فحص الشجرة البرمجية للنافذة النشطة (UI Automation Tree)
        # -------------------------------------------------------------
        window_title, ui_elements = self.scanner.scan_active_window(max_elements=40)
        
        is_explicit_ui_click = any(w in lower_goal for w in [
            "اضغط", "انقر", "دوس", "زر", "زرار", "قائمة", "تبويب", "تاب", "click", "press", "tab", "menu"
        ])

        if ui_elements and (is_explicit_ui_click or any(syn in lower_goal for syn in ["حفظ", "سيف", "جديد", "ملف", "اغلاق", "close", "save", "file"])):
            match_res = self.scanner.find_best_match(goal_arabic, ui_elements)
            if match_res and match_res[1] >= 0.65:
                target_elem, confidence = match_res
                if on_step_callback:
                    on_step_callback("thought", f"⚡ مطابقة محلية فورية: [{target_elem.control_type}] '{target_elem.name}' (ثقة: {int(confidence*100)}%)")
                    on_step_callback("action", f"🖱️ النقر على: '{target_elem.name}' داخل '{window_title}'...")

                success = self.scanner.click_element(target_elem)
                if success:
                    final_msg = f"تم الضغط على '{target_elem.name}' بنجاح."
                    if on_step_callback:
                        on_step_callback("finished", final_msg)
                    return final_msg

        # -------------------------------------------------------------
        # 3. اتخاذ القرار عبر نموذج Jev (System One)
        # -------------------------------------------------------------
        if on_step_callback:
            on_step_callback("thinking", "🧠 استدعاء Jev Decision Model (TypeSafe AI)...")

        start_time = time.time()

        # إعداد ملخص مضغوط لعناصر الشاشة ليمتلك Jev سياق التطبيق المفتوح
        compact_ui_summary = ""
        if ui_elements:
            top_controls = [f"{e.id}:{e.control_type} '{e.name}'" for e in ui_elements[:15] if e.name]
            compact_ui_summary = " | Controls: " + ", ".join(top_controls)

        try:
            state_context = (
                f"User Goal: '{goal_arabic}'\n"
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
                            "click_ui_element": "Click a specific button, menu item, tab, or checkbox inside the active window",
                            "web_search": "Search the web on Google/YouTube for a query",
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
                            "rider": "JetBrains Rider IDE",
                            "visual_studio": "Visual Studio Community IDE",
                            "code": "Visual Studio Code",
                            "cursor": "Cursor IDE",
                            "calculator": "Windows Calculator",
                            "chrome": "Google Chrome browser",
                            "edge": "Microsoft Edge browser",
                            "youtube": "YouTube",
                            "notepad": "Notepad text editor",
                            "paint": "MS Paint",
                            "explorer": "Windows File Explorer",
                            "cmd": "Command prompt or terminal",
                            "spotify": "Spotify",
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
                    ),
                    "is_multi_step": Noul(
                        instructions="Does this command require both launching an app AND typing/searching within it?"
                    )
                }
            )

            latency_ms = int((time.time() - start_time) * 1000)

        except Exception as e:
            err_msg = f"❌ خطأ أثناء الاتصال بـ Jev Decision Model: {e}"
            if on_step_callback:
                on_step_callback("error", err_msg)
            return err_msg

        action = jev_response.answers["primary_action"].choice
        target_app = jev_response.answers["target_app"].choice
        shortcut = jev_response.answers["shortcut_type"].choice
        is_multi_step = jev_response.answers["is_multi_step"].noul > 0.6
        confidence = jev_response.answers["primary_action"].confidence

        thought = f"قرار Jev: {action} (تطبيق: {target_app}) | سرعة: {latency_ms}ms | ثقة: {int(confidence*100)}%"
        if on_step_callback:
            on_step_callback("thought", thought)

        if self.controller.stop_requested:
            return "تم إيقاف العملية."

        final_message = "تم تنفيذ طلبك بنجاح."

        # -------------------------------------------------------------
        # 4. تنفيذ الأفعال
        # -------------------------------------------------------------
        if action == "click_ui_element":
            match_res = self.scanner.find_best_match(goal_arabic, ui_elements)
            if match_res:
                target_elem, conf = match_res
                if on_step_callback:
                    on_step_callback("action", f"🖱️ النقر على عنصر: [{target_elem.control_type}] '{target_elem.name}'...")
                self.scanner.click_element(target_elem)
                final_message = f"تم الضغط على '{target_elem.name}'."
            else:
                final_message = "لم أجد العنصر المطلوب داخل النافذة الحالية."

        elif action == "launch_app":
            app_query = target_app if target_app != "none" else goal_arabic
            if on_step_callback:
                on_step_callback("action", f"⚡ تشغيل التطبيق: '{app_query}'...")

            success, launch_msg = self.app_resolver.launch(app_query)
            final_message = launch_msg
            self.controller.wait(0.8)

            if is_multi_step:
                sub_text = self._extract_search_or_text(goal_arabic)
                if sub_text and sub_text.lower() != app_query.lower():
                    self.controller.wait(0.4)
                    if on_step_callback:
                        on_step_callback("action", f"✍️ كتابة: '{sub_text}'...")
                    self.controller.type_arabic(sub_text)
                    final_message += f" وتمت كتابة: {sub_text}"

        elif action == "web_search":
            query = self._extract_search_or_text(goal_arabic)
            if not query:
                query = goal_arabic
            
            if on_step_callback:
                on_step_callback("action", f"🌐 فتح المتصفح والبحث عن: {query}...")

            if target_app == "youtube" or "يوتيوب" in goal_arabic or "youtube" in goal_arabic.lower():
                url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
                final_message = f"فتحتلك يوتيوب وبحثت عن: {query}"
            else:
                url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
                final_message = f"فتحتلك جوجل وبدأت البحث عن: {query}"

            import subprocess
            subprocess.Popen(f'start "" "{url}"', shell=True)
            self.controller.wait(1.0)

        elif action == "math_calculate":
            if on_step_callback:
                on_step_callback("action", "🔢 تشغيل الآلة الحاسبة وإجراء الحساب...")
            import subprocess
            subprocess.Popen("start calc", shell=True)
            self.controller.wait(1.0)
            math_text = re.sub(r'[^\d\+\-\*\/\.\(\)\=]', '', goal_arabic)
            if math_text:
                self.controller.type_arabic(math_text)
                self.controller.press_key("enter")
            final_message = "تم فتح الآلة الحاسبة وتجهيز الحسبة."

        elif action == "type_text":
            text_to_type = self._extract_search_or_text(goal_arabic)
            if on_step_callback:
                on_step_callback("action", f"✍️ كتابة: '{text_to_type}'...")
            
            # محاولة الكتابة في العنصر النشط أو محرر النصوص إذا وجد
            editor_elem = next((e for e in ui_elements if e.control_type in ("Edit", "Document")), None)
            if editor_elem:
                self.scanner.type_into_element(editor_elem, text_to_type)
            else:
                self.controller.type_arabic(text_to_type)
            final_message = f"تمت كتابة: {text_to_type}"

        elif action == "keyboard_shortcut":
            if shortcut == "close_window":
                self.controller.hotkey(["alt", "f4"])
                final_message = "تم إغلاق النافذة."
            elif shortcut == "minimize_all":
                self.controller.hotkey(["win", "d"])
                final_message = "تم إظهار سطح المكتب."
            elif shortcut == "copy":
                self.controller.hotkey(["ctrl", "c"])
                final_message = "تم النسخ."
            elif shortcut == "paste":
                self.controller.hotkey(["ctrl", "v"])
                final_message = "تم اللصق."
            elif shortcut == "select_all":
                self.controller.hotkey(["ctrl", "a"])
                final_message = "تم تحديد الكل."
            elif shortcut == "save":
                self.controller.hotkey(["ctrl", "s"])
                final_message = "تم الحفظ (Ctrl + S)."
            elif shortcut == "enter":
                self.controller.press_key("enter")
                final_message = "تم الضغط على زر Enter."
            else:
                self.controller.press_key(shortcut)
                final_message = "تم تنفيذ الاختصار."

        elif action == "volume_control":
            lower_goal = goal_arabic.lower()
            if any(w in lower_goal for w in ["علي", "ارفع", "up", "raise", "increase"]):
                for _ in range(5):
                    self.controller.press_key("volumeup")
                final_message = "تم رفع الصوت."
            elif any(w in lower_goal for w in ["وطي", "اخفض", "down", "lower", "decrease"]):
                for _ in range(5):
                    self.controller.press_key("volumedown")
                final_message = "تم خفض الصوت."
            else:
                self.controller.press_key("volumemute")
                final_message = "تم كتم/إلغاء كتم الصوت."

        if on_step_callback:
            on_step_callback("finished", final_message)

        return final_message
