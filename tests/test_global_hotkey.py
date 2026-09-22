"""
Unit Tests for OSController Global Emergency Hotkey Lifecycle.
"""

import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.os_controller import OSController


class TestGlobalHotkey(unittest.TestCase):
    def test_global_hotkey_lifecycle(self):
        controller = OSController()
        abort_called = False

        def on_abort():
            nonlocal abort_called
            abort_called = True

        controller.start_global_emergency_listener(on_abort_callback=on_abort)
        # Should not crash and should start background daemon
        self.assertFalse(controller.stop_requested)

        # Trigger programmatic emergency stop
        controller.emergency_stop()
        self.assertTrue(controller.stop_requested)

        # Clean shutdown
        controller.stop_global_emergency_listener()
        self.assertIsNone(controller._global_listener)


if __name__ == "__main__":
    unittest.main()
