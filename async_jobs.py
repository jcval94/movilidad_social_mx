import hashlib
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from threading import Lock

from state_backend import get_state, put_state
from diagnosis_worker import compute_diagnosis

_JOB_TTL_S = int(os.getenv("DIAG_JOB_TTL_S", "86400"))
_JOB_TIMEOUT_S = int(os.getenv("DIAG_JOB_TIMEOUT_S", "120"))
_JOB_RETRIES = int(os.getenv("DIAG_JOB_RETRIES", "2"))

_EXECUTOR = ProcessPoolExecutor(max_workers=int(os.getenv("DIAG_WORKERS", "2")))
_FUTURES = {}
_FUTURE_LOCK = Lock()


def _job_fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _result_cache_key(fingerprint: str) -> str:
    return f"diag:cache:{fingerprint}"


def _job_meta_key(fingerprint: str) -> str:
    return f"diag:job:{fingerprint}"


def enqueue_diagnosis(payload: dict) -> dict:
    fingerprint = _job_fingerprint(payload)
    cached = get_state(_result_cache_key(fingerprint))
    if cached:
        return {"job_id": fingerprint, "status": "completed", "cached": True}

    meta_key = _job_meta_key(fingerprint)
    meta = get_state(meta_key)
    if meta and meta.get("status") in {"queued", "running"}:
        return {"job_id": fingerprint, "status": meta.get("status"), "cached": False}

    put_state(
        meta_key,
        {
            "status": "queued",
            "attempt": 0,
            "created_at": time.time(),
            "timeout_s": _JOB_TIMEOUT_S,
            "retries": _JOB_RETRIES,
        },
        ttl_s=_JOB_TTL_S,
    )

    with _FUTURE_LOCK:
        _FUTURES[fingerprint] = _EXECUTOR.submit(_run_with_retry, payload, _JOB_RETRIES)

    return {"job_id": fingerprint, "status": "queued", "cached": False}


def _run_with_retry(payload: dict, retries: int) -> dict:
    fingerprint = _job_fingerprint(payload)
    meta_key = _job_meta_key(fingerprint)
    attempts = retries + 1
    last_error = None

    for attempt in range(1, attempts + 1):
        put_state(meta_key, {"status": "running", "attempt": attempt, "timeout_s": _JOB_TIMEOUT_S, "retries": retries}, ttl_s=_JOB_TTL_S)
        try:
            result = compute_diagnosis(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            put_state(_result_cache_key(fingerprint), result, ttl_s=_JOB_TTL_S)
            put_state(meta_key, {"status": "completed", "attempt": attempt}, ttl_s=_JOB_TTL_S)
            return result
        except Exception as exc:
            last_error = str(exc)
            put_state(meta_key, {"status": "retrying", "attempt": attempt, "error": last_error}, ttl_s=_JOB_TTL_S)
            time.sleep(min(2**attempt, 8))

    put_state(meta_key, {"status": "failed", "error": last_error}, ttl_s=_JOB_TTL_S)
    raise RuntimeError(last_error or "unknown job failure")


def poll_diagnosis(job_id: str) -> dict:
    cached = get_state(_result_cache_key(job_id))
    if cached:
        return {"status": "completed", "result": cached}

    meta = get_state(_job_meta_key(job_id)) or {"status": "unknown"}

    with _FUTURE_LOCK:
        future = _FUTURES.get(job_id)

    if future is not None and future.done():
        try:
            result = future.result(timeout=0)
            return {"status": "completed", "result": result}
        except Exception as exc:
            return {"status": "failed", "error": str(exc)}

    return {"status": meta.get("status", "queued"), "meta": meta}
