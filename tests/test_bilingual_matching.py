import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.accessibility_scanner import accessibility_scanner, UIElement

def test_matching():
    # Mock UI elements list simulating a music app / Spotify UI tree
    mock_elements = [
        UIElement(
            id=1, name="Lyrics", control_type="Button", automation_id="lyrics-button",
            class_name="Button", left=500, top=600, right=540, bottom=640,
            width=40, height=40, center_x=520, center_y=620,
            is_enabled=True, is_visible=True, value=None, raw_control=None
        ),
        UIElement(
            id=2, name="Next", control_type="Button", automation_id="control-button-skip-forward",
            class_name="Button", left=300, top=600, right=340, bottom=640,
            width=40, height=40, center_x=320, center_y=620,
            is_enabled=True, is_visible=True, value=None, raw_control=None
        ),
        UIElement(
            id=3, name="Previous", control_type="Button", automation_id="control-button-skip-back",
            class_name="Button", left=200, top=600, right=240, bottom=640,
            width=40, height=40, center_x=220, center_y=620,
            is_enabled=True, is_visible=True, value=None, raw_control=None
        ),
        UIElement(
            id=4, name="Search", control_type="Edit", automation_id="search-input",
            class_name="Edit", left=100, top=50, right=400, bottom=90,
            width=300, height=40, center_x=250, center_y=70,
            is_enabled=True, is_visible=True, value="", raw_control=None
        ),
    ]

    test_queries = [
        "دوس علي زرار الكلامات",
        "اضغط على زرار الكلمات",
        "دوس على زرار النيكست",
        "اضغط على next",
        "show lyrics",
        "click next",
        "دوس على البريفيوس",
    ]

    print("=== Testing Bilingual UI Matching ===")
    for q in test_queries:
        match = accessibility_scanner.find_best_match(q, mock_elements)
        if match:
            elem, conf = match
            print(f"Query: '{q}' ➡️ Matched: [{elem.control_type}] '{elem.name}' (Confidence: {conf:.2f})")
        else:
            print(f"Query: '{q}' ➡️ NO MATCH ❌")

if __name__ == "__main__":
    test_matching()
