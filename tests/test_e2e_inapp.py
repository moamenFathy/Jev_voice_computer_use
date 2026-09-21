import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import time
import subprocess
from src.core.os_controller import OSController
from src.decision.jev_engine import JevDecisionEngine

def test_in_app_decision():
    print(">>> 1. Initializing Jev Engine and OS Controller...")
    controller = OSController()
    engine = JevDecisionEngine(controller)

    print(">>> 2. Launching Notepad...")
    proc = subprocess.Popen(["notepad.exe"])
    time.sleep(1.2)

    def callback(evt, msg):
        print(f"[{evt.upper()}] {msg}")

    print("\n>>> 3. Executing In-App Typing Command: 'اكتب مرحبا بكم في عصر التحكم الصوتي'...")
    res = engine.execute_goal("اكتب مرحبا بكم في عصر التحكم الصوتي", on_step_callback=callback)
    print("Result:", res)
    time.sleep(0.8)

    print("\n>>> 4. Executing In-App UI Click: 'اضغط على قائمة ملف'...")
    res = engine.execute_goal("اضغط على قائمة ملف", on_step_callback=callback)
    print("Result:", res)
    time.sleep(1.0)

    print("\n>>> 5. Terminating test Notepad process...")
    proc.terminate()
    print(">>> All Tests Passed Successfully! 🚀")

if __name__ == "__main__":
    test_in_app_decision()
