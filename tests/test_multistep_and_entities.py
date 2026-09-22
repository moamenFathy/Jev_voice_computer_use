import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.os_controller import OSController
from src.decision.jev_engine import JevDecisionEngine

def test_multi_step():
    controller = OSController()
    engine = JevDecisionEngine(controller)

    print("=== 1. Testing Step Decomposition ===")
    test_goals = [
        "افتح المفكرة واكتب تقرير اليوم وبعدين احفظ الملف",
        "افتح يوتيوب ميوزك وشغل اغنية اغيب",
        "افتح المتصفح وابحث عن اخبار الذكاء الاصطناعي",
        "شغل عمرو دياب"
    ]

    for g in test_goals:
        steps = engine._decompose_into_steps(g)
        print(f"Goal: '{g}'\n  ➡️ Steps ({len(steps)}): {steps}\n")

    print("=== 2. Testing Entity & Clean Query Extraction ===")
    query_tests = [
        "سيرش في youtube music على اغنية اغيب",
        "سيرش علي اغير في youtube music علي اغنيه اغيب",
        "شغل اغنية Shape of You على سبوتيفاي",
        "افتح اليوتيوب وشغل سورة الكهف",
        "ابحث في جوجل عن اسعار الذهب اليوم"
    ]

    for qt in query_tests:
        platform, clean_q = engine._extract_clean_entities(qt)
        print(f"Input: '{qt}'\n  ➡️ Platform: {platform} | Clean Query: '{clean_q}'\n")

if __name__ == "__main__":
    test_multi_step()
