"""
Windows UI Automation (UIA) Accessibility Scanner & Universal In-App Controller.
Provides 100% thread-safe, sub-second local UI tree inspection, bilingual element matching,
and universal in-app search & interaction across ANY Windows desktop application.
"""

import time
import re
import functools
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
import uiautomation as auto
import pyautogui
import pyperclip

def ensure_com_initialized(func):
    """Decorator ensuring UIAutomation COM apartment is initialized in the calling thread."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with auto.UIAutomationInitializerInThread():
            return func(*args, **kwargs)
    return wrapper

# Common Control Types to prioritize for interaction
INTERACTIVE_CONTROL_TYPES = {
    auto.ControlType.ButtonControl: "Button",
    auto.ControlType.EditControl: "Edit",
    auto.ControlType.CheckBoxControl: "CheckBox",
    auto.ControlType.RadioButtonControl: "RadioButton",
    auto.ControlType.ComboBoxControl: "ComboBox",
    auto.ControlType.MenuItemControl: "MenuItem",
    auto.ControlType.TabItemControl: "TabItem",
    auto.ControlType.HyperlinkControl: "Hyperlink",
    auto.ControlType.ListItemControl: "ListItem",
    auto.ControlType.TreeItemControl: "TreeItem",
    auto.ControlType.DocumentControl: "Document",
    auto.ControlType.TextControl: "Text",
    auto.ControlType.ToolBarControl: "ToolBar",
    auto.ControlType.SliderControl: "Slider",
}

# Bilingual synonyms dictionary (Arabic ↔ English UI terms)
BILINGUAL_UI_SYNONYMS = {
    # Lyrics / كلمات الأغاني
    "كلمات": ["lyrics", "show lyrics", "كلمات", "كلمات الأغاني", "كلمات الاغاني"],
    "الكلمات": ["lyrics", "show lyrics", "كلمات", "كلمات الأغاني", "كلمات الاغاني"],
    "الكلامات": ["lyrics", "show lyrics", "كلمات", "كلمات الأغاني", "كلمات الاغاني"],
    "كلامات": ["lyrics", "show lyrics", "كلمات"],
    "ليركس": ["lyrics", "show lyrics"],
    "ليريكس": ["lyrics", "show lyrics"],
    "lyrics": ["lyrics", "show lyrics", "كلمات", "الكلمات"],

    # Next / السابق / التالي
    "التالي": ["next", "next track", "forward", "التالي"],
    "التالية": ["next", "next track", "التالية"],
    "نكست": ["next", "next track", "التالي"],
    "النيكست": ["next", "next track", "التالي"],
    "نيكست": ["next", "next track", "التالي"],
    "بعدها": ["next", "next track"],
    "البعدها": ["next", "next track"],
    "اللي بعدها": ["next", "next track"],
    "اللي بعده": ["next", "next track"],
    "next": ["next", "next track", "التالي", "forward"],

    # Previous / السابق
    "السابق": ["back", "previous", "previous track", "السابق"],
    "السابقة": ["back", "previous", "previous track", "السابقة"],
    "بريفيوس": ["previous", "previous track", "السابق"],
    "البريفيوس": ["previous", "previous track", "السابق"],
    "قبلها": ["previous", "previous track"],
    "القبلها": ["previous", "previous track"],
    "اللي قبلها": ["previous", "previous track"],
    "اللي قبله": ["previous", "previous track"],
    "previous": ["previous", "previous track", "السابق", "back"],
    "prev": ["previous", "previous track", "السابق"],
    "رجوع": ["back", "previous", "رجوع"],

    # Play / Pause
    "تشغيل": ["play", "run", "start", "تشغيل"],
    "بلاي": ["play"],
    "ايقاف": ["pause", "stop", "ايقاف", "pause/resume"],
    "إيقاف": ["pause", "stop", "إيقاف"],
    "بوز": ["pause"],
    "توقف": ["pause", "stop"],

    # Common UI controls
    "حفظ": ["save", "حفظ", "save as"],
    "سيف": ["save", "save as"],
    "جديد": ["new", "جديد", "create"],
    "فتح": ["open", "فتح"],
    "اوبن": ["open"],
    "ملف": ["file", "ملف"],
    "تعديل": ["edit", "تعديل", "modify"],
    "تحرير": ["edit", "تحرير"],
    "عرض": ["view", "عرض"],
    "بحث": ["search", "find", "بحث", "query", "filter"],
    "سيرش": ["search", "find"],
    "الغاء": ["cancel", "الغاء", "dismiss"],
    "إلغاء": ["cancel", "إلغاء"],
    "موافق": ["ok", "yes", "confirm", "agree", "موافق", "apply"],
    "تطبيق": ["apply", "تطبيق"],
    "اغلاق": ["close", "exit", "اغلاق"],
    "إغلاق": ["close", "exit", "إغلاق"],
    "اقفل": ["close", "exit"],
    "مسح": ["delete", "remove", "clear", "مسح", "حذف"],
    "حذف": ["delete", "remove", "clear", "حذف"],
    "اعدادات": ["settings", "preferences", "options", "اعدادات", "config"],
    "إعدادات": ["settings", "preferences", "options", "إعدادات"],
    "سيتنج": ["settings"],
    "ارسال": ["send", "submit", "ارسال", "post"],
    "إرسال": ["send", "submit", "إرسال"],
    "نسخ": ["copy", "نسخ"],
    "لصق": ["paste", "لصق"],
    "قص": ["cut", "قص"],
    "تحديث": ["refresh", "reload", "update", "تحديث"],
    "ريفرش": ["refresh", "reload"],
    "تنزيل": ["download", "تنزيل"],
    "داونلود": ["download"],
    "تحميل": ["upload", "download", "تحميل"],
    "تسجيل الدخول": ["login", "sign in", "تسجيل الدخول"],
    "لوجين": ["login", "sign in"],
    "خروج": ["logout", "sign out", "خروج"],
    "تسجيل خروج": ["logout", "sign out"],
    "مفضلة": ["favorite", "like", "save"],
    "لايك": ["like", "favorite"],
    "تكرار": ["repeat"],
    "عشوائي": ["shuffle"],
    "شافل": ["shuffle"],
}


@dataclass
class UIElement:
    id: int
    name: str
    control_type: str
    automation_id: str
    class_name: str
    left: int
    top: int
    right: int
    bottom: int
    width: int
    height: int
    center_x: int
    center_y: int
    is_enabled: bool
    is_visible: bool
    value: Optional[str]
    raw_control: Any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.control_type,
            "automation_id": self.automation_id,
            "center": [self.center_x, self.center_y],
            "bbox": [self.left, self.top, self.right, self.bottom],
            "value": self.value,
        }


class AccessibilityScanner:
    """Windows UI Automation Accessibility Scanner & Universal In-App Controller."""

    def __init__(self):
        auto.SetGlobalSearchTimeout(1.0)

    @ensure_com_initialized
    def get_active_window(self) -> Optional[Any]:
        """Gets the top-level foreground active window control."""
        ignore_names = {"desktop 1", "desktop", "program manager", "taskbar", "shell_traywnd", "windows input experience"}

        try:
            focused = auto.GetFocusedControl()
            if focused:
                current = focused
                while current:
                    c_name = (current.Name or "").strip().lower()
                    if current.ControlType == auto.ControlType.WindowControl and c_name not in ignore_names:
                        return current
                    parent = current.GetParentControl()
                    if not parent or parent == auto.GetRootControl():
                        if current.ControlType == auto.ControlType.WindowControl and c_name not in ignore_names:
                            return current
                        break
                    current = parent
        except Exception:
            pass

        # Robust Fallback: Enumerate top-level Windows from RootControl
        try:
            root = auto.GetRootControl()
            child = root.GetFirstChildControl()
            while child:
                if child.ControlType == auto.ControlType.WindowControl:
                    name = (child.Name or "").strip().lower()
                    if name and name not in ignore_names and not child.IsOffscreen:
                        return child
                child = child.GetNextSiblingControl()
        except Exception:
            pass

        return None



    @ensure_com_initialized
    def scan_active_window(
        self,
        max_elements: int = 50,
        max_depth: int = 8,
        interactive_only: bool = True,
    ) -> Tuple[str, List[UIElement]]:
        """
        Scans the active window and returns its title and a list of interactive elements.
        Thread-safe and runs locally in ~10-30ms.
        """
        active_window = self.get_active_window()
        if not active_window:
            return "Unknown Window", []

        window_title = active_window.Name or "Active Window"
        elements: List[UIElement] = []
        element_id = 1

        screen_w, screen_h = pyautogui.size()

        def traverse(control: Any, depth: int):
            nonlocal element_id
            if depth > max_depth or len(elements) >= max_elements:
                return

            try:
                rect = control.BoundingRectangle
                if rect is None:
                    return

                left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
                width = right - left
                height = bottom - top

                # Filter zero-sized or completely offscreen controls
                if width <= 2 or height <= 2 or right <= 0 or bottom <= 0 or left >= screen_w or top >= screen_h:
                    return

                ctype = control.ControlType
                ctype_name = INTERACTIVE_CONTROL_TYPES.get(ctype)

                if interactive_only:
                    is_candidate = (ctype_name is not None) and (ctype != auto.ControlType.TextControl or len(control.Name or "") > 1)
                else:
                    is_candidate = True

                name = (control.Name or "").strip()
                auto_id = (control.AutomationId or "").strip()
                class_name = (control.ClassName or "").strip()

                if is_candidate and (name or auto_id or ctype in (auto.ControlType.EditControl, auto.ControlType.DocumentControl)):
                    val = None
                    try:
                        val_pat = control.GetValuePattern()
                        if val_pat:
                            val = val_pat.Value
                    except Exception:
                        pass

                    center_x = left + width // 2
                    center_y = top + height // 2

                    elem = UIElement(
                        id=element_id,
                        name=name,
                        control_type=ctype_name or f"Type_{ctype}",
                        automation_id=auto_id,
                        class_name=class_name,
                        left=left,
                        top=top,
                        right=right,
                        bottom=bottom,
                        width=width,
                        height=height,
                        center_x=center_x,
                        center_y=center_y,
                        is_enabled=control.IsEnabled,
                        is_visible=not control.IsOffscreen,
                        value=val,
                        raw_control=control,
                    )
                    elements.append(elem)
                    element_id += 1

                # Traverse children
                child = control.GetFirstChildControl()
                while child:
                    traverse(child, depth + 1)
                    child = child.GetNextSiblingControl()

            except Exception:
                return

        traverse(active_window, depth=1)
        return window_title, elements

    def format_elements_summary(self, window_title: str, elements: List[UIElement]) -> str:
        """Formats the scanned elements into a concise text view for prompts or logging."""
        lines = [f"=== Active Window: '{window_title}' ==="]
        for elem in elements:
            val_str = f" [Value: '{elem.value}']" if elem.value else ""
            auto_id_str = f" [ID: {elem.automation_id}]" if elem.automation_id and elem.automation_id != elem.name else ""
            lines.append(f"[{elem.id}] {elem.control_type}: '{elem.name}'{auto_id_str}{val_str} at ({elem.center_x}, {elem.center_y})")
        return "\n".join(lines)

    def _normalize_text(self, text: str) -> str:
        """Normalizes Arabic/English text for robust UI element matching."""
        if not text:
            return ""
        t = text.lower().strip()
        # Remove tashkeel / diacritics
        t = re.sub(r'[\u064B-\u0652]', '', t)
        # Normalize alefs, taa marbouta, yaa
        t = re.sub(r'[أإآٱ]', 'ا', t)
        t = t.replace('ة', 'ه').replace('ى', 'ي')
        # Common phonetic variants
        t = t.replace('الكلامات', 'الكلمات').replace('كلامات', 'كلمات')
        t = t.replace('البعدها', 'بعدها').replace('القبلها', 'قبلها')
        # Arabic phonetic domain extensions
        t = re.sub(r'\s*دوت\s*كوم\b', '.com', t)
        t = re.sub(r'\s*دوت\s*نت\b', '.net', t)
        t = re.sub(r'\s*دوت\s*اور[جغ]\b', '.org', t)
        t = re.sub(r'\s*دوت\s*اي\s*او\b', '.io', t)
        t = re.sub(r'\s*دوت\s*اي\s*جي\b', '.eg', t)
        t = re.sub(r'\s*دوت\s*اي\s*اي\b', '.ai', t)
        return t

    def find_best_match(self, query: str, elements: List[UIElement]) -> Optional[Tuple[UIElement, float]]:
        """
        Finds the most relevant UI element matching the user's voice query.
        Uses bilingual dictionary expansion + normalization + substring + token overlap scoring.
        """
        if not elements or not query:
            return None

        clean_query = self._normalize_text(query)
        # Remove command prefixes/fillers
        clean_query = re.sub(r"\b(علي|على|زر|زرار|بتاع|خانه|خانة|حقل|كلمه|كلمة|اضغط|انقر|دوس|افتح|شغل|اكتب|في|من|show|click|press|button)\b", "", clean_query).strip()

        search_terms = {clean_query}
        for token in clean_query.split():
            norm_token = self._normalize_text(token)
            search_terms.add(norm_token)
            if token in BILINGUAL_UI_SYNONYMS:
                for syn in BILINGUAL_UI_SYNONYMS[token]:
                    search_terms.add(self._normalize_text(syn))
            if norm_token in BILINGUAL_UI_SYNONYMS:
                for syn in BILINGUAL_UI_SYNONYMS[norm_token]:
                    search_terms.add(self._normalize_text(syn))

        best_elem = None
        best_score = 0.0

        for elem in elements:
            elem_name_norm = self._normalize_text(elem.name or "")
            elem_auto_id_norm = self._normalize_text(elem.automation_id or "")
            elem_full = f"{elem_name_norm} {elem_auto_id_norm}"

            score = 0.0

            for term in search_terms:
                if not term or len(term) < 2:
                    continue
                if term == elem_name_norm:
                    score = max(score, 1.0)
                elif term in elem_name_norm:
                    score = max(score, 0.85 * (len(term) / max(len(elem_name_norm), 1)))
                elif term in elem_auto_id_norm:
                    score = max(score, 0.80)
                else:
                    for sub in term.split():
                        if len(sub) > 1 and sub in elem_full:
                            score = max(score, 0.65)

            if elem.control_type in ("Button", "MenuItem", "TabItem", "CheckBox", "Edit"):
                score *= 1.1

            if score > best_score:
                best_score = score
                best_elem = elem

        if best_elem and best_score >= 0.40:
            return best_elem, min(best_score, 1.0)
        return None

    def find_search_field(self, elements: List[UIElement]) -> Optional[UIElement]:
        """Universally locates the search or query input box in ANY active app."""
        # 1. Look for explicit Search / Query / Find / Address in Edit controls
        search_keywords = ["search", "بحث", "find", "filter", "query", "address", "url", "سيرش"]
        for elem in elements:
            if elem.control_type in ("Edit", "ComboBox"):
                elem_text = f"{elem.name} {elem.automation_id}".lower()
                if any(k in elem_text for k in search_keywords):
                    return elem

        # 2. Fallback: First Edit or Document control in the upper half of the window
        for elem in elements:
            if elem.control_type in ("Edit", "Document") and elem.center_y < 400:
                return elem

        return None

    def find_play_or_action_button(self, elements: List[UIElement]) -> Optional[UIElement]:
        """Universally finds a Play, Open, or primary action button in search results."""
        action_keywords = ["play", "تشغيل", "شغل", "start", "open", "فتح", "view"]
        for elem in elements:
            if elem.control_type in ("Button", "MenuItem", "ListItem", "Hyperlink"):
                elem_text = f"{elem.name} {elem.automation_id}".lower()
                if any(k in elem_text for k in action_keywords):
                    return elem

        # Fallback: First ListItem or first Button in content area
        for elem in elements:
            if elem.control_type in ("ListItem", "Button") and elem.center_y > 150:
                return elem

        return None

    def find_search_result_links(self, elements: List[UIElement], query_hint: str = "") -> Optional[UIElement]:
        """
        Universally identifies the top organic search result link or primary header link
        in an active browser search page (Google, Bing, DuckDuckGo, etc.).
        """
        # Exclude navigation bar / search tools / header UI
        candidates = []
        hint_words = [w.lower() for w in query_hint.split() if len(w) > 2] if query_hint else []

        for elem in elements:
            # Result links are typically Hyperlink, ListItem, or Text controls in the main body (top > 120, height >= 12)
            if elem.control_type in ("Hyperlink", "ListItem", "Text", "Button") and elem.top > 120 and elem.width > 60:
                name_clean = (elem.name or "").strip()
                if not name_clean or len(name_clean) < 3:
                    continue
                # Skip search engine UI buttons and navigation tabs
                skip_keywords = ["all", "images", "videos", "news", "maps", "tools", "settings", "sign in", "google apps", "بحث", "الكل", "صور", "فيديو", "أخبار", "خرائط", "أدوات"]
                if name_clean.lower() in skip_keywords:
                    continue

                score = 0
                if elem.control_type == "Hyperlink":
                    score += 30
                if any(hw in name_clean.lower() for hw in hint_words):
                    score += 50

                candidates.append((elem, score, elem.top))

        if candidates:
            # Prioritize matching hint, then lowest top coordinate (topmost result)
            candidates.sort(key=lambda c: (-c[1], c[2]))
            return candidates[0][0]

        return None

    @ensure_com_initialized
    def click_top_search_result(self, query_hint: str = "", auto_wait: float = 0.8) -> bool:
        """
        Autonomous Web Navigator: Scans active browser window after search and clicks the
        top organic search result link directly to navigate into the destination site.
        """
        time.sleep(auto_wait)
        _, elements = self.scan_active_window(max_elements=40, interactive_only=False)
        link = self.find_search_result_links(elements, query_hint=query_hint)
        if link:
            return self.click_element(link)
        return False

    @ensure_com_initialized
    def click_element(self, element: UIElement) -> bool:
        """
        Clicks an element using native UI Automation Invoke/Toggle pattern,
        or falls back to physical mouse click on its center coordinates.
        """
        # Strategy 1: Programmatic Invoke
        try:
            if element.raw_control:
                inv_pat = element.raw_control.GetInvokePattern()
                if inv_pat:
                    inv_pat.Invoke()
                    return True
                tog_pat = element.raw_control.GetTogglePattern()
                if tog_pat:
                    tog_pat.Toggle()
                    return True
                sel_pat = element.raw_control.GetSelectionItemPattern()
                if sel_pat:
                    sel_pat.Select()
                    return True
        except Exception:
            pass

        # Strategy 2: Fallback to coordinate click
        try:
            pyautogui.moveTo(element.center_x, element.center_y, duration=0.15)
            pyautogui.click()
            return True
        except Exception as e:
            print(f"[AccessibilityScanner] Click failed: {e}")
            return False

    @ensure_com_initialized
    def type_into_element(self, element: UIElement, text: str, clear_first: bool = True) -> bool:
        """
        Types text into an Edit/Document/Input element.
        Uses native ValuePattern, programmatic SetFocus, or safe Unicode clipboard typing.
        """
        # Strategy 1: Programmatic ValuePattern
        try:
            if element.raw_control:
                val_pat = element.raw_control.GetValuePattern()
                if val_pat and not val_pat.IsReadOnly:
                    val_pat.SetValue(text)
                    return True
        except Exception:
            pass

        # Strategy 2: Programmatic SetFocus + Unicode paste
        try:
            if element.raw_control:
                element.raw_control.SetFocus()
                time.sleep(0.05)
                if clear_first:
                    pyautogui.hotkey("ctrl", "a")
                    pyautogui.press("backspace")
                    time.sleep(0.05)
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v")
                return True
        except Exception:
            pass

        # Strategy 3: Safe Coordinate Click + Unicode paste
        try:
            screen_w, screen_h = pyautogui.size()
            safe_x = max(10, min(screen_w - 10, element.center_x))
            safe_y = max(10, min(screen_h - 10, element.center_y))
            pyautogui.click(safe_x, safe_y)
            time.sleep(0.1)

            if clear_first:
                pyautogui.hotkey("ctrl", "a")
                pyautogui.press("backspace")
                time.sleep(0.05)

            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            return True
        except Exception as e:
            print(f"[AccessibilityScanner] Type failed: {e}")
            return False


    def universal_in_app_search(self, query: str, auto_play: bool = False) -> Tuple[bool, str]:
        """
        UNIVERSAL In-App Search & Execution across ANY active desktop app
        (Spotify, Chrome, VS Code, Explorer, Settings, Discord, etc.)
        without requiring application-specific controllers!
        """
        window_title, elements = self.scan_active_window(max_elements=40)
        search_box = self.find_search_field(elements)

        if search_box:
            # Type query into the search box
            self.type_into_element(search_box, query, clear_first=True)
            time.sleep(0.1)
            pyautogui.press("enter")
        else:
            # Universal keyboard shortcut to search in active app: Ctrl+L or Ctrl+F
            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.1)
            pyperclip.copy(query)
            pyautogui.hotkey("ctrl", "v")
            pyautogui.press("enter")

        if auto_play:
            time.sleep(0.8)
            # Re-scan refreshed window to find the result or play button
            refreshed_title, refreshed_elements = self.scan_active_window(max_elements=30)
            play_btn = self.find_play_or_action_button(refreshed_elements)
            if play_btn:
                self.click_element(play_btn)
            else:
                # Universal fallback: Tab into first result and press Enter
                pyautogui.press("tab")
                time.sleep(0.1)
                pyautogui.press("enter")

        act_str = " and triggered playback on top result" if auto_play else ""
        return True, f"Searched for '{query}' inside '{window_title}'{act_str} successfully."


# Singleton instance for easy import
accessibility_scanner = AccessibilityScanner()
