import sys
from pathlib import Path

# Add src to Python Path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.ui.dynamic_island import launch_dynamic_island

if __name__ == "__main__":
    print("=" * 60)
    print("⚡ JEV SYSTEM ONE | DYNAMIC ISLAND VOICE ASSISTANT")
    print("🎙️ Real-time Bilingual Voice Control (Arabic & English)")
    print("🛑 Emergency Abort: Press ESC or move mouse to any screen corner")
    print("=" * 60)
    launch_dynamic_island()
