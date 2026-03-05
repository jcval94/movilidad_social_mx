import io
import pickle
import time
from typing import Iterable

import pandas as pd
import streamlit as st

from config import (
    MAX_SESSION_OBJECT_SIZE_MB,
    MAX_UPLOAD_SIZE_MB,
    SESSION_IDLE_TIMEOUT_SECONDS,
    SESSION_MAX_RUNTIME_SECONDS,
)

SESSION_META_KEYS = {
    "_session_created_at",
    "_session_last_activity_at",
    "_session_cleanup_notice",
}


def _estimate_size_bytes(value) -> int:
    if isinstance(value, pd.DataFrame):
        return int(value.memory_usage(deep=True).sum())
    if isinstance(value, (bytes, bytearray)):
        return len(value)
    if isinstance(value, io.BytesIO):
        return value.getbuffer().nbytes
    try:
        return len(pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))
    except Exception:
        return 0


def _iter_large_or_forbidden_keys() -> Iterable[str]:
    max_size_bytes = MAX_SESSION_OBJECT_SIZE_MB * 1024 * 1024
    for key, value in st.session_state.items():
        if key in SESSION_META_KEYS:
            continue

        if isinstance(value, pd.DataFrame):
            yield key
            continue

        if isinstance(value, (bytes, bytearray, io.BytesIO)) and _estimate_size_bytes(value) > max_size_bytes:
            yield key
            continue

        if _estimate_size_bytes(value) > max_size_bytes:
            yield key


def _iter_oversized_upload_keys() -> Iterable[str]:
    max_size_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    for key, value in st.session_state.items():
        file_size = getattr(value, "size", None)
        if isinstance(file_size, int) and file_size > max_size_bytes:
            yield key


def enforce_upload_size_limit(uploaded_file) -> bool:
    if uploaded_file is None:
        return True

    max_size_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if uploaded_file.size > max_size_bytes:
        st.error(
            f"El archivo supera el límite de {MAX_UPLOAD_SIZE_MB} MB. "
            "Reduce el tamaño e intenta nuevamente."
        )
        return False
    return True


def apply_session_guardrails() -> None:
    now = time.time()
    if "_session_created_at" not in st.session_state:
        st.session_state["_session_created_at"] = now
    last_activity = st.session_state.get("_session_last_activity_at", now)
    st.session_state["_session_last_activity_at"] = now

    is_idle = (now - last_activity) > SESSION_IDLE_TIMEOUT_SECONDS
    over_runtime = (now - st.session_state["_session_created_at"]) > SESSION_MAX_RUNTIME_SECONDS

    removed = []
    for key in list(dict.fromkeys([*_iter_large_or_forbidden_keys(), *_iter_oversized_upload_keys()])):
        st.session_state.pop(key, None)
        removed.append(key)

    if is_idle or over_runtime:
        preserve = set(SESSION_META_KEYS)
        preserve.update({"origin_default", "dest_default", "selected_vars", "base_selected_vars"})
        for key in list(st.session_state.keys()):
            if key not in preserve and not key.startswith("cats_") and not key.startswith("base_cats_"):
                st.session_state.pop(key, None)
                removed.append(key)
        st.session_state["_session_created_at"] = now

    if removed:
        st.session_state["_session_cleanup_notice"] = (
            "Se limpiaron objetos pesados/inactivos de la sesión para reducir uso de memoria."
        )


def maybe_show_cleanup_notice() -> None:
    notice = st.session_state.pop("_session_cleanup_notice", None)
    if notice:
        st.info(notice)
