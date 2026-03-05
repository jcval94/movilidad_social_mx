import json
import os
import time
from typing import Any

_STORE: dict[str, tuple[float, str]] = {}


def _get_redis_client():
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None
    try:
        import redis  # type: ignore

        return redis.from_url(redis_url, decode_responses=True)
    except Exception:
        return None


def put_state(key: str, value: Any, ttl_s: int = 3600) -> None:
    payload = json.dumps(value, ensure_ascii=False)
    redis_client = _get_redis_client()
    if redis_client is not None:
        try:
            redis_client.setex(key, ttl_s, payload)
            return
        except Exception:
            pass

    _STORE[key] = (time.time() + ttl_s, payload)


def get_state(key: str):
    redis_client = _get_redis_client()
    if redis_client is not None:
        try:
            payload = redis_client.get(key)
            return json.loads(payload) if payload else None
        except Exception:
            pass

    item = _STORE.get(key)
    if not item:
        return None
    expires_at, payload = item
    if time.time() > expires_at:
        _STORE.pop(key, None)
        return None
    return json.loads(payload)
