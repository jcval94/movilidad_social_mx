from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List


@dataclass(frozen=True)
class DailyReport:
    report_date: date
    session_id: str
    summary: str
    top_picks: List[str]
    top_blocks: List[str]
    risk_changes: List[str]
    actions_taken: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "report_date": self.report_date.isoformat(),
            "session_id": self.session_id,
            "summary": self.summary,
            "top_picks": self.top_picks,
            "top_blocks": self.top_blocks,
            "risk_changes": self.risk_changes,
            "actions_taken": self.actions_taken,
        }


def build_daily_report(
    report_date: date,
    session_id: str,
    top_picks: List[str],
    top_blocks: List[str],
    risk_changes: List[str],
    actions_taken: List[str],
) -> DailyReport:
    summary = (
        f"Daily {report_date.isoformat()} session={session_id} "
        f"picks={len(top_picks)} blocks={len(top_blocks)} "
        f"risk_changes={len(risk_changes)} actions={len(actions_taken)}"
    )
    return DailyReport(
        report_date=report_date,
        session_id=session_id,
        summary=summary,
        top_picks=top_picks,
        top_blocks=top_blocks,
        risk_changes=risk_changes,
        actions_taken=actions_taken,
    )
