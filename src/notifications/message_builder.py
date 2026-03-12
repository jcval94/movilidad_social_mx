from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class NotificationEvent(str, Enum):
    OPEN = "OPEN"
    OPEN_PLUS_2H = "OPEN_PLUS_2H"
    OPEN_PLUS_4H = "OPEN_PLUS_4H"
    OPEN_PLUS_6H = "OPEN_PLUS_6H"
    CLOSE = "CLOSE"
    DRIFT_ALERT = "drift alert"
    RETRAIN_DECISION = "retrain decision"
    INCIDENT_ALERT = "incident alert"


@dataclass(frozen=True)
class MessageContext:
    event: NotificationEvent
    timestamp: datetime
    strategy_name: str
    session_id: str
    top_picks: List[str] = field(default_factory=list)
    top_blocks: List[str] = field(default_factory=list)
    expected_floor: Optional[float] = None
    expected_ceiling: Optional[float] = None
    expected_bucket: Optional[str] = None
    reward_risk: Optional[float] = None
    recommended_action: Optional[str] = None
    risk_changes: List[str] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)
    extra: Dict[str, str] = field(default_factory=dict)


def _fmt_pct(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2%}"


def _fmt_num(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}"


def build_message(ctx: MessageContext) -> str:
    lines = [
        f"[{ctx.event.value}] {ctx.strategy_name}",
        f"session={ctx.session_id} ts={ctx.timestamp.isoformat()}",
        f"top_picks={', '.join(ctx.top_picks) if ctx.top_picks else 'N/A'}",
        f"top_blocks={', '.join(ctx.top_blocks) if ctx.top_blocks else 'N/A'}",
        f"piso_esperado={_fmt_pct(ctx.expected_floor)}",
        f"techo_esperado={_fmt_pct(ctx.expected_ceiling)}",
        f"bucket_esperado={ctx.expected_bucket or 'N/A'}",
        f"reward_risk={_fmt_num(ctx.reward_risk)}",
        f"accion_recomendada={ctx.recommended_action or 'N/A'}",
        f"cambios_riesgo={'; '.join(ctx.risk_changes) if ctx.risk_changes else 'N/A'}",
        f"acciones_tomadas={'; '.join(ctx.actions_taken) if ctx.actions_taken else 'N/A'}",
    ]

    if ctx.extra:
        for key in sorted(ctx.extra):
            lines.append(f"{key}={ctx.extra[key]}")

    return "\n".join(lines)
