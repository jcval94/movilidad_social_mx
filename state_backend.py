import json
import logging
import os
import time
from typing import Any

_STORE: dict[str, tuple[float, str]] = {}
LOGGER = logging.getLogger(__name__)


class StateBackendUnavailableError(RuntimeError):
    """El backend de estado compartido no está disponible."""


def _as_bool(raw: str | None) -> bool:
    return (raw or "").strip().lower() in {"1", "true", "yes", "on"}


def is_redis_required() -> bool:
    env_name = (os.getenv("ENV") or "").strip().lower()
    return env_name == "production" or _as_bool(os.getenv("REDIS_REQUIRED"))


def _raise_redis_unavailable(detail: str) -> None:
    raise StateBackendUnavailableError(
        "Redis no disponible para estado compartido. "
        f"Detalle: {detail}. "
        "Configure REDIS_URL accesible o desactive REDIS_REQUIRED fuera de producción."
    )


def _get_redis_client():
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        if is_redis_required():
            _raise_redis_unavailable("REDIS_URL no está definido")
        return None
    try:
        import redis  # type: ignore

        return redis.from_url(redis_url, decode_responses=True)
    except Exception as exc:
        LOGGER.exception("No se pudo inicializar cliente Redis")
        if is_redis_required():
            _raise_redis_unavailable(str(exc))
        return None


def assert_redis_ready() -> None:
    redis_client = _get_redis_client()
    if redis_client is None:
        if is_redis_required():
            _raise_redis_unavailable("cliente Redis no inicializado")
        return
    try:
        redis_client.ping()
    except Exception as exc:
        LOGGER.exception("Fallo ping de Redis")
        _raise_redis_unavailable(str(exc))


def put_state(key: str, value: Any, ttl_s: int = 3600) -> None:
    payload = json.dumps(value, ensure_ascii=False)
    redis_client = _get_redis_client()
    if redis_client is not None:
        try:
            redis_client.setex(key, ttl_s, payload)
            return
        except Exception as exc:
            LOGGER.exception("Error escribiendo estado en Redis para key=%s", key)
            _raise_redis_unavailable(str(exc))

    if is_redis_required():
        _raise_redis_unavailable("escritura sin cliente Redis")

    _STORE[key] = (time.time() + ttl_s, payload)


def get_state(key: str):
    redis_client = _get_redis_client()
    if redis_client is not None:
        try:
            payload = redis_client.get(key)
            return json.loads(payload) if payload else None
        except Exception as exc:
            LOGGER.exception("Error leyendo estado en Redis para key=%s", key)
            _raise_redis_unavailable(str(exc))

    if is_redis_required():
        _raise_redis_unavailable("lectura sin cliente Redis")

    item = _STORE.get(key)
    if not item:
        return None
    expires_at, payload = item
    if time.time() > expires_at:
        _STORE.pop(key, None)
        return None
    return json.loads(payload)
