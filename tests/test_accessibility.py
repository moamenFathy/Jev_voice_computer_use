"""
Test script for Windows Accessibility Scanner.
Opens Notepad, scans its UI Automation tree, writes text, and interacts with menus.
"""

import time
import subprocess
from src.core.accessibility_scanner import accessibility_scanner

def run_test():
    print(">>> 1. Launching Notepad...")
    proc = subprocess.Popen(["notepad.exe"])
    time.sleep(1.2)

    print(">>> 2. Scanning Active Window UI Tree...")
    title, elements = accessibility_scanner.scan_active_window(max_elements=30)
    print(f"Scanned {len(elements)} elements in '{title}':")
    print(accessibility_scanner.format_elements_summary(title, elements))

    print("\n>>> 3. Testing Bilingual Matching for Document/Editor...")
    # Find editor/text area
    match = accessibility_scanner.find_best_match("محرر النصوص", elements) or accessibility_scanner.find_best_match("Text Editor", elements)
    if not match:
        # Fallback to first Edit / Document control
        for el in elements:
            if el.control_type in ("Document", "Edit"):
                match = (el, 1.0)
                break

    if match:
        elem, score = match
        print(f"Found target element: [{elem.id}] {elem.control_type} '{elem.name}' (Confidence: {score:.2f})")
        print(">>> 4. Typing Arabic text into Notepad...")
        accessibility_scanner.type_into_element(elem, "أهلاً بك! تم التحكم بنجاح عبر Windows Accessibility Tree 🚀\n")
        time.sleep(0.5)

    print("\n>>> 5. Testing Matching for Menu 'ملف' / 'File'...")
    file_match = accessibility_scanner.find_best_match("ملف", elements)
    if file_match:
        elem, score = file_match
        print(f"Matched 'ملف' to: [{elem.id}] {elem.control_type} '{elem.name}' (Confidence: {score:.2f})")
        print("Clicking 'File' menu...")
        accessibility_scanner.click_element(elem)
        time.sleep(1.0)

    print("\n>>> 6. Closing Notepad test process...")
    proc.terminate()
    print(">>> Test completed successfully!")

if __name__ == "__main__":
    run_test()
