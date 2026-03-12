from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict


@dataclass(frozen=True)
class ModelHealthReport:
    timestamp: datetime
    model_name: str
    data_drift_score: float
    feature_stability_score: float
    decision: str
    notes: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "model_name": self.model_name,
            "data_drift_score": self.data_drift_score,
            "feature_stability_score": self.feature_stability_score,
            "decision": self.decision,
            "notes": self.notes,
        }


def build_model_health_report(
    timestamp: datetime,
    model_name: str,
    data_drift_score: float,
    feature_stability_score: float,
    drift_threshold: float = 0.3,
) -> ModelHealthReport:
    decision = "retrain" if data_drift_score >= drift_threshold else "keep"
    notes = "auto-decision based on configured drift threshold"
    return ModelHealthReport(
        timestamp=timestamp,
        model_name=model_name,
        data_drift_score=data_drift_score,
        feature_stability_score=feature_stability_score,
        decision=decision,
        notes=notes,
    )
