"""
Stage-by-Stage Latency Telemetry & Benchmarking Engine for JEV.
Measures and logs precise microsecond durations across STT, Cognitive Decision,
Tool Execution, OS Observation, and Verification.
"""

import time
import json
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from pathlib import Path
from src.config import TEMP_DIR


@dataclass
class TelemetryRecord:
    timestamp: float
    goal: str
    action: str
    target: str
    decision_path: str  # "fast_path" or "system_one"
    t_stt_ms: float = 0.0
    t_decision_ms: float = 0.0
    t_execution_ms: float = 0.0
    t_observation_ms: float = 0.0
    t_verification_ms: float = 0.0
    t_total_ms: float = 0.0
    success: bool = True


class TelemetryManager:
    """
    Collects real-time stage benchmarks and writes structured JSONL telemetry.
    """

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or (TEMP_DIR / "telemetry.jsonl")
        self.records: List[TelemetryRecord] = []

    def record_step(
        self,
        goal: str,
        action: str,
        target: str,
        decision_path: str = "fast_path",
        t_stt_ms: float = 0.0,
        t_decision_ms: float = 0.0,
        t_execution_ms: float = 0.0,
        t_observation_ms: float = 0.0,
        t_verification_ms: float = 0.0,
        t_total_ms: float = 0.0,
        success: bool = True,
    ) -> TelemetryRecord:
        """Records a completed step lifecycle with timing metrics."""
        rec = TelemetryRecord(
            timestamp=time.time(),
            goal=goal,
            action=action,
            target=target,
            decision_path=decision_path,
            t_stt_ms=round(t_stt_ms, 2),
            t_decision_ms=round(t_decision_ms, 2),
            t_execution_ms=round(t_execution_ms, 2),
            t_observation_ms=round(t_observation_ms, 2),
            t_verification_ms=round(t_verification_ms, 2),
            t_total_ms=round(t_total_ms, 2),
            success=success,
        )
        self.records.append(rec)

        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[DEBUG] Error writing telemetry record: {e}")

        return rec

    def get_summary(self) -> Dict[str, Any]:
        """Calculates aggregate latency statistics across all recorded steps."""
        if not self.records:
            return {
                "total_recorded_steps": 0,
                "avg_total_latency_ms": 0.0,
                "avg_decision_latency_ms": 0.0,
                "avg_execution_latency_ms": 0.0,
                "avg_observation_latency_ms": 0.0,
                "avg_verification_latency_ms": 0.0,
                "fast_path_ratio_pct": 0.0,
            }

        n = len(self.records)
        fast_path_count = sum(1 for r in self.records if r.decision_path == "fast_path")
        return {
            "total_recorded_steps": n,
            "avg_total_latency_ms": round(sum(r.t_total_ms for r in self.records) / n, 2),
            "avg_decision_latency_ms": round(sum(r.t_decision_ms for r in self.records) / n, 2),
            "avg_execution_latency_ms": round(sum(r.t_execution_ms for r in self.records) / n, 2),
            "avg_observation_latency_ms": round(sum(r.t_observation_ms for r in self.records) / n, 2),
            "avg_verification_latency_ms": round(sum(r.t_verification_ms for r in self.records) / n, 2),
            "fast_path_ratio_pct": round((fast_path_count / n) * 100.0, 2),
        }


# Global singleton telemetry manager
telemetry = TelemetryManager()
