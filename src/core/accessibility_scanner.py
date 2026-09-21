"""
Windows UI Automation (UIA) Accessibility Scanner & In-App Controller.
Provides sub-second local UI tree inspection, bilingual element matching,
and direct programmatic/coordinate interaction with native Windows controls.
"""

import time
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
import uiautomation as auto
import pyautogui
import pyperclip

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
    "حفظ": ["save", "حفظ", "save as"],
    "سيف": ["save", "save as"],
    "جديد": ["new", "جديد", "create"],
    "فتح": ["open", "فتح"],
    "اوبن": ["open"],
    "ملف": ["file", "ملف"],
    "تعديل": ["edit", "تعديل", "modify"],
    "تحرير": ["edit", "تحرير"],
    "عرض": ["view", "عرض"],
    "بحث": ["search", "find", "بحث", "query"],
    "سيرش": ["search", "find"],
    "تشغيل": ["play", "run", "start", "تشغيل"],
    "بلاي": ["play"],
    "ايقاف": ["pause", "stop", "ايقاف", "pause/resume"],
    "إيقاف": ["pause", "stop", "إيقاف"],
    "بوز": ["pause"],
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
    "التالي": ["next", "forward", "التالي"],
    "السابق": ["back", "previous", "السابق"],
    "رجوع": ["back", "previous", "رجوع"],
    "تنزيل": ["download", "تنزيل"],
    "داونلود": ["download"],
    "تحميل": ["upload", "download", "تحميل"],
    "تسجيل الدخول": ["login", "sign in", "تسجيل الدخول"],
    "لوجين": ["login", "sign in"],
    "خروج": ["logout", "sign out", "خروج"],
    "تسجيل خروج": ["logout", "sign out"],
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
    """Windows UI Automation Accessibility Scanner."""

    def __init__(self):
        # Configure uiautomation settings
        auto.SetGlobalSearchTimeout(1.0)

    def get_active_window(self) -> Optional[Any]:
        """Gets the top-level foreground active window control."""
        try:
            focused = auto.GetFocusedControl()
            if not focused:
                return None
            # Walk up to the top-level WindowControl
            current = focused
            while current:
                if current.ControlType == auto.ControlType.WindowControl:
                    return current
                parent = current.GetParentControl()
                if not parent or parent == auto.GetRootControl():
                    return current
                current = parent
            return focused
        except Exception:
            return None

    def scan_active_window(
        self,
        max_elements: int = 50,
        max_depth: int = 8,
        interactive_only: bool = True,
    ) -> Tuple[str, List[UIElement]]:
        """
        Scans the active window and returns its title and a list of interactive elements.
        Runs locally in ~10-30ms.
        """
        active_window = self.get_active_window()
        if not active_window:
            return "Unknown Window", []

        window_title = active_window.Name or "Active Window"
        elements: List[UIElement] = []
        element_id = 1

        # Check screen bounds to filter offscreen items
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

                # Filter out zero-sized or completely offscreen controls
                if width <= 2 or height <= 2 or right <= 0 or bottom <= 0 or left >= screen_w or top >= screen_h:
                    return

                ctype = control.ControlType
                ctype_name = INTERACTIVE_CONTROL_TYPES.get(ctype)

                # If interactive_only is True, filter only meaningful controls
                if interactive_only:
                    is_candidate = (ctype_name is not None) and (ctype != auto.ControlType.TextControl or len(control.Name or "") > 1)
                else:
                    is_candidate = True

                name = (control.Name or "").strip()
                auto_id = (control.AutomationId or "").strip()
                class_name = (control.ClassName or "").strip()

                # If candidate has name or automation_id or is an edit/document control
                if is_candidate and (name or auto_id or ctype in (auto.ControlType.EditControl, auto.ControlType.DocumentControl)):
                    # Get value if available
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

    def find_best_match(self, query: str, elements: List[UIElement]) -> Optional[Tuple[UIElement, float]]:
        """
        Finds the most relevant UI element matching the user's voice query.
        Uses bilingual dictionary expansion + substring + token overlap scoring.
        Returns (UIElement, confidence_score [0.0 - 1.0]).
        """
        if not elements or not query:
            return None

        clean_query = query.lower().strip()
        # Remove common Arabic prefixes/fillers ("على", "زر", "زرار", "خانة", "حقل", "كلمة", "اضغط", "انقر")
        clean_query = re.sub(r"\b(على|زر|زرار|خانة|حقل|كلمة|اضغط|انقر|دوس|افتح|شغل|اكتب|في|من)\b", "", clean_query).strip()

        # Build candidate search terms (original query + English synonyms if found)
        search_terms = {clean_query}
        for token in clean_query.split():
            search_terms.add(token)
            if token in BILINGUAL_UI_SYNONYMS:
                search_terms.update(BILINGUAL_UI_SYNONYMS[token])

        best_elem = None
        best_score = 0.0

        for elem in elements:
            elem_name = (elem.name or "").lower()
            elem_auto_id = (elem.automation_id or "").lower()
            elem_full = f"{elem_name} {elem_auto_id}"

            score = 0.0

            # 1. Exact match
            for term in search_terms:
                if not term:
                    continue
                if term == elem_name:
                    score = max(score, 1.0)
                elif term in elem_name:
                    # Substring match (weighted by length ratio)
                    score = max(score, 0.85 * (len(term) / max(len(elem_name), 1)))
                elif term in elem_auto_id:
                    score = max(score, 0.75)
                else:
                    # Token overlap
                    for sub in term.split():
                        if len(sub) > 1 and sub in elem_full:
                            score = max(score, 0.6)

            # Prioritize actionable types over plain text
            if elem.control_type in ("Button", "MenuItem", "TabItem", "CheckBox", "Edit"):
                score *= 1.1

            if score > best_score:
                best_score = score
                best_elem = elem

        if best_elem and best_score >= 0.4:
            return best_elem, min(best_score, 1.0)
        return None

    def click_element(self, element: UIElement) -> bool:
        """
        Clicks an element using native UI Automation Invoke/Toggle pattern,
        or falls back to physical mouse click on its center coordinates.
        """
        # Strategy 1: Programmatic Invoke (Instant, no mouse movement required)
        try:
            if element.raw_control:
                # Button / MenuItem
                inv_pat = element.raw_control.GetInvokePattern()
                if inv_pat:
                    inv_pat.Invoke()
                    return True
                # CheckBox / Radio
                tog_pat = element.raw_control.GetTogglePattern()
                if tog_pat:
                    tog_pat.Toggle()
                    return True
                # Tab / List
                sel_pat = element.raw_control.GetSelectionItemPattern()
                if sel_pat:
                    sel_pat.Select()
                    return True
        except Exception:
            pass

        # Strategy 2: Fallback to physical coordinate click
        try:
            pyautogui.moveTo(element.center_x, element.center_y, duration=0.15)
            pyautogui.click()
            return True
        except Exception as e:
            print(f"[AccessibilityScanner] Click failed: {e}")
            return False

    def type_into_element(self, element: UIElement, text: str, clear_first: bool = False) -> bool:
        """
        Types text into an Edit/Document/Input element.
        Uses native ValuePattern or focuses and uses safe Unicode clipboard typing.
        """
        # Strategy 1: Programmatic SetValue
        if not clear_first:
            try:
                if element.raw_control:
                    val_pat = element.raw_control.GetValuePattern()
                    if val_pat:
                        val_pat.SetValue(text)
                        return True
            except Exception:
                pass

        # Strategy 2: Focus & Unicode paste
        try:
            pyautogui.click(element.center_x, element.center_y)
            time.sleep(0.1)

            if clear_first:
                pyautogui.hotkey("ctrl", "a")
                pyautogui.press("backspace")
                time.sleep(0.05)

            # Paste Unicode text safely
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            return True
        except Exception as e:
            print(f"[AccessibilityScanner] Type failed: {e}")
            return False


# Singleton instance for easy import
accessibility_scanner = AccessibilityScanner()
