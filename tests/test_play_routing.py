import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.os_controller import OSController
from src.decision.jev_engine import JevDecisionEngine

def test_routing():
    controller = OSController()
    engine = JevDecisionEngine(controller)

    test_goals = [
        "شغل الاغنيه",
        "شغل اغنية ويجز",
        "شغل تراك عمرو دياب",
        "شغل سورة الكهف على يوتيوب",
        "ابحث في جوجل عن اسعار الذهب",
        "دوس علي زرار الكلامات"
    ]

    print("=== Testing Play vs Search Intent Routing ===")
    for g in test_goals:
        norm = engine.scanner._normalize_text(g)
        is_music = any(w in norm for w in ["اغنيه", "تراك", "موسيقي", "مغني", "song", "track", "music"]) or (
            norm.startswith("شغل ") and not any(app in norm for app in ["المفكره", "الحاسبه", "الرسام", "المتصفح", "كروم", "رايدر", "كود"])
        )
        print(f"Goal: '{g}' ➡️ Normalized: '{norm}' ➡️ Is Music Play: {is_music}")

if __name__ == "__main__":
    test_routing()
