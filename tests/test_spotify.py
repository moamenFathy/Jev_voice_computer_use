import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.os_controller import OSController
from src.decision.jev_engine import JevDecisionEngine

def test_spotify_queries():
    controller = OSController()
    engine = JevDecisionEngine(controller)

    test_cases = [
        "شغل عمرو دياب على سبوتيفاي",
        "ابحث عن ويجز في سبوتيفاي",
        "شغل اغنية Shape of You على سبوتيفاي",
        "هاتلي تامر حسني في سبوتيفاي"
    ]

    print("=== Testing Spotify Query Extraction ===")
    for tc in test_cases:
        extracted = engine._extract_spotify_query(tc)
        print(f"Command: '{tc}' ➡️ Extracted Query: '{extracted}'")

if __name__ == "__main__":
    test_spotify_queries()
