import sys
import time
from collections.abc import Iterable

import streamlit as st

# Umbral por objeto en session_state (~1.5 MB)
MAX_SESSION_OBJECT_BYTES = 1_500_000
# Tiempo máximo de inactividad antes de limpiar estado efímero (45 min)
SESSION_IDLE_TIMEOUT_S = 45 * 60

# Claves que pueden permanecer entre limpiezas por inactividad
PERSISTENT_SESSION_KEYS = {
    "selected_vars",
    "base_selected_vars",
    "section4_target_select",
    "section4_last_target",
    "section4_form_expanded",
    "origin_default",
    "dest_default",
}


def _estimate_size_bytes(value) -> int:
    """Estimación ligera y segura de tamaño en memoria."""
    try:
        return sys.getsizeof(value)
    except Exception:
        return 0


def _drop_oversized_session_objects(max_bytes: int = MAX_SESSION_OBJECT_BYTES) -> list[str]:
    removed = []
    for key in list(st.session_state.keys()):
        size_b = _estimate_size_bytes(st.session_state.get(key))
        if size_b > max_bytes:
            st.session_state.pop(key, None)
            removed.append(f"{key} ({size_b / (1024 * 1024):.2f} MB)")
    return removed


def _clear_idle_ephemeral_state(now_ts: float, idle_timeout_s: int = SESSION_IDLE_TIMEOUT_S) -> bool:
    last_activity = float(st.session_state.get("_last_activity_ts", now_ts))
    idle_seconds = now_ts - last_activity
    is_idle = idle_seconds > idle_timeout_s
    if not is_idle:
        return False

    for key in list(st.session_state.keys()):
        if key not in PERSISTENT_SESSION_KEYS and not key.startswith("cats_") and not key.startswith("base_cats_"):
            st.session_state.pop(key, None)
    return True


def run_session_hygiene() -> None:
    """
    Higiene de estado:
    1) limpia llaves sobredimensionadas,
    2) limpia estado efímero por inactividad.
    """
    now_ts = time.time()
    was_idle = _clear_idle_ephemeral_state(now_ts)
    removed = _drop_oversized_session_objects()
    st.session_state["_last_activity_ts"] = now_ts

    if was_idle:
        st.info("Se limpió estado de sesión por inactividad para reducir uso de memoria.")

    if removed:
        st.warning(
            "Se eliminaron objetos grandes de la sesión: " + ", ".join(removed)
        )


def validate_payload_limits(payload_items: Iterable, *, max_items: int = 5000) -> bool:
    """Control simple para evitar cargas excesivas en memoria."""
    try:
        if hasattr(payload_items, "__len__"):
            return len(payload_items) <= max_items
        count = 0
        for _ in payload_items:
            count += 1
            if count > max_items:
                return False
        return True
    except Exception:
        return False
