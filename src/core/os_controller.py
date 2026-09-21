import os
import time
from PIL import Image, ImageGrab
import pyautogui
import pyperclip
from src.config import FAILSAFE_ENABLED, TEMP_DIR

# إعدادات الأمان لـ PyAutoGUI
pyautogui.FAILSAFE = FAILSAFE_ENABLED
pyautogui.PAUSE = 0.1

class OSController:
    def __init__(self):
        self.stop_requested = False
        try:
            self.screen_width, self.screen_height = pyautogui.size()
        except Exception:
            self.screen_width, self.screen_height = 1920, 1080

    def capture_screenshot(self, target_size=(1280, 720)) -> tuple[Image.Image, str]:
        """التقاط صورة الشاشة بأعلى كفاءة"""
        screen_path = str(TEMP_DIR / "latest_screen.png")
        img = None

        try:
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except Exception:
            try:
                img = ImageGrab.grab(all_screens=False)
            except Exception:
                img = pyautogui.screenshot()

        if img:
            self.screen_width, self.screen_height = img.size
            img_resized = img.resize(target_size, Image.Resampling.LANCZOS)
            img_resized.save(screen_path, format="JPEG", quality=85)
            return img, screen_path
        raise RuntimeError("فشل التقاط صورة الشاشة.")

    def norm_to_pixels(self, norm_x: int, norm_y: int) -> tuple[int, int]:
        px_x = int((norm_x / 1000.0) * self.screen_width)
        px_y = int((norm_y / 1000.0) * self.screen_height)
        return max(0, min(self.screen_width - 1, px_x)), max(0, min(self.screen_height - 1, px_y))

    def click(self, x: int, y: int, button: str = "left", normalized: bool = True):
        if self.stop_requested:
            return
        px, py = self.norm_to_pixels(x, y) if normalized else (x, y)
        pyautogui.moveTo(px, py, duration=0.2)
        pyautogui.click(px, py, button=button)

    def double_click(self, x: int, y: int, normalized: bool = True):
        if self.stop_requested:
            return
        px, py = self.norm_to_pixels(x, y) if normalized else (x, y)
        pyautogui.moveTo(px, py, duration=0.2)
        pyautogui.doubleClick(px, py)

    def right_click(self, x: int, y: int, normalized: bool = True):
        self.click(x, y, button="right", normalized=normalized)

    def type_arabic(self, text: str):
        """كتابة النصوص بالعربي أو الإنجليزي عبر الـ Clipboard لضمان سلامة الحروف"""
        if self.stop_requested:
            return
        try:
            pyperclip.copy(text)
            time.sleep(0.05)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.1)
        except Exception as e:
            print(f"⚠️ خطأ أثناء الكتابة: {e}")

    def press_key(self, key_name: str):
        if self.stop_requested:
            return
        key_map = {
            "enter": "enter", "return": "enter", "win": "win", "windows": "win",
            "esc": "escape", "escape": "escape", "backspace": "backspace",
            "tab": "tab", "space": "space", "up": "up", "down": "down",
            "left": "left", "right": "right", "delete": "delete",
            "volumeup": "volumeup", "volumedown": "volumedown", "volumemute": "volumemute",
            "playpause": "playpause", "nexttrack": "nexttrack", "prevtrack": "prevtrack"
        }
        actual_key = key_map.get(key_name.lower(), key_name.lower())
        pyautogui.press(actual_key)

    def hotkey(self, keys: list[str]):
        if self.stop_requested:
            return
        pyautogui.hotkey(*keys)

    def scroll(self, direction: str = "down", amount: int = 5):
        if self.stop_requested:
            return
        clicks = -amount if direction == "down" else amount
        pyautogui.scroll(clicks * 100)

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, normalized: bool = True):
        if self.stop_requested:
            return
        sx, sy = self.norm_to_pixels(start_x, start_y) if normalized else (start_x, start_y)
        ex, ey = self.norm_to_pixels(end_x, end_y) if normalized else (end_x, end_y)
        pyautogui.moveTo(sx, sy, duration=0.2)
        pyautogui.dragTo(ex, ey, duration=0.5, button='left')

    def wait(self, seconds: float = 1.0):
        time.sleep(seconds)

    def emergency_stop(self):
        self.stop_requested = True
        print("🛑 تم تفعيل إيقاف الطوارئ!")
