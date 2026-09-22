"""
Unit Tests for Latency Telemetry & Stage Benchmarking Engine.
"""

import unittest
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.telemetry import TelemetryManager, TelemetryRecord


class TestTelemetry(unittest.TestCase):
    def setUp(self):
        self.temp_file = Path(tempfile.gettempdir()) / "test_telemetry.jsonl"
        if self.temp_file.exists():
            self.temp_file.unlink()
        self.mgr = TelemetryManager(log_path=self.temp_file)

    def tearDown(self):
        if self.temp_file.exists():
            try:
                self.temp_file.unlink()
            except Exception:
                pass

    def test_record_and_aggregate_metrics(self):
        self.mgr.record_step(
            goal="افتح المفكرة",
            action="launch_app",
            target="notepad",
            decision_path="fast_path",
            t_stt_ms=120.0,
            t_decision_ms=0.5,
            t_execution_ms=45.0,
            t_observation_ms=25.0,
            t_verification_ms=10.0,
            t_total_ms=200.5,
            success=True,
        )

        self.mgr.record_step(
            goal="احسب المسألة",
            action="math_calculate",
            target="calc",
            decision_path="system_one",
            t_stt_ms=150.0,
            t_decision_ms=250.0,
            t_execution_ms=30.0,
            t_observation_ms=0.0,
            t_verification_ms=0.0,
            t_total_ms=430.0,
            success=True,
        )

        summary = self.mgr.get_summary()
        self.assertEqual(summary["total_recorded_steps"], 2)
        self.assertEqual(summary["fast_path_ratio_pct"], 50.0)
        self.assertGreater(summary["avg_total_latency_ms"], 300.0)
        self.assertTrue(self.temp_file.exists())


if __name__ == "__main__":
    unittest.main()
