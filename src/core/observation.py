"""
Observation Model for JEV Reliability Architecture (Phase 1).
Represents what the system observed from the environment/OS after an action.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Observation:
    source: str
    description: str
    data: Any = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "description": self.description,
            "data": self.data,
            "evidence": self.evidence,
        }
