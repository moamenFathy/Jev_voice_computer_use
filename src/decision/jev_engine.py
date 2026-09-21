import os
import re
import time
import urllib.parse
from typesafe_sdk import TypeSafeClient, Choice, Score, Noul
from src.config import TYPESAFE_API_KEY, MAX_STEPS_PER_COMMAND, STEP_PAUSE_SECONDS, TEMP_DIR
from src.core.os_controller import OSController
from src.core.app_resolver import WindowsAppResolver

class JevDecisionEngine:
    def __init__(self, os_controller: OSController):
        self.controller = os_controller
        self.app_resolver = WindowsAppResolver()
        self.api_key = TYPESAFE_API_KEY
        self.client = TypeSafeClient(api_key=self.api_key)

    def _get_active_window_info(self) -> str:
        try:
            import pygetwindow as gw
            active = gw.getActiveWindow()
            if active and active.title:
                return active.title
        except Exception:
            pass
        return "Unknown Window"

    def _extract_search_or_text(self, text: str) -> str:
        cleaned = re.sub(
            r'^(افتح|شغل|ابحث عن|ابحث في|دور على|اكتب|قوله|احسب|open|launch|search for|search|type|write|calculate|play)\s+',
            '', text.strip(), flags=re.IGNORECASE
        )
        cleaned = re.sub(
            r'^(المتصفح|جوجل|كروم|المفكرة|الآلة الحاسبة|اليوتيوب|browser|chrome|notepad|calculator|calc|youtube|google)\s+(and\s+)?(و)?(ابحث عن|واكتب|واحسب|type|write|search for|search)?\s*',
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
            on_step_callback("thinking", "🧠 استدعاء Jev Decision Model (TypeSafe AI)...")

        active_window = self._get_active_window_info()
        start_time = time.time()

        try:
            state_context = (
                f"User Goal: '{goal_arabic}'\n"
                f"Active Windows Title: '{active_window}'\n"
                f"System Environment: Windows 11 Desktop"
            )

            jev_response = self.client.system_one(
                state=state_context,
                questions={
                    "primary_action": Choice(
                        instructions="What is the primary computer action requested by the user?",
                        criteria={
                            "launch_app": "Launch a desktop application or IDE",
                            "web_search": "Search the web on Google/YouTube for a query",
                            "type_text": "Type Arabic or English text into the active document",
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
                            "none": "Other app or none"
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

        # تنفيذ الأفعال
        if action == "launch_app":
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
            elif shortcut == "enter":
                self.controller.press_key("enter")
                final_message = "تم الضغط على زر Enter."
            else:
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
