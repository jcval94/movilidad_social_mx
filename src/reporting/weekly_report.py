from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List


@dataclass(frozen=True)
class WeeklyReport:
    week_start: date
    week_end: date
    sessions: List[str]
    daily_summaries: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "week_start": self.week_start.isoformat(),
            "week_end": self.week_end.isoformat(),
            "sessions": self.sessions,
            "daily_summaries": self.daily_summaries,
            "days": len(self.daily_summaries),
        }


def build_weekly_report(week_start: date, week_end: date, sessions: List[str], daily_summaries: List[str]) -> WeeklyReport:
    return WeeklyReport(
        week_start=week_start,
        week_end=week_end,
        sessions=sessions,
        daily_summaries=daily_summaries,
    )
