import hashlib
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from threading import Lock

from diagnosis_worker import compute_diagnosis
from state_backend import get_state, put_state

_JOB_TTL_S = int(os.getenv("DIAG_JOB_TTL_S", "86400"))
_JOB_TIMEOUT_S = int(os.getenv("DIAG_JOB_TIMEOUT_S", "120"))
_JOB_RETRIES = int(os.getenv("DIAG_JOB_RETRIES", "2"))
_MAX_QUEUED_JOBS = int(os.getenv("MAX_QUEUED_JOBS", "32"))

_FUTURES: dict[str, object] = {}
_FUTURE_LOCK = Lock()
_METRICS_LOCK = Lock()
_METRICS = {
    "rejected_busy": 0,
    "failed": 0,
    "timeout": 0,
}


def _parse_cpu_limit(raw: str | None) -> float | None:
    if not raw:
        return None
    value = raw.strip().lower()
    if value.endswith("m"):
        return float(value[:-1]) / 1000.0
    return float(value)


def _resolve_max_workers() -> int:
    cpu_limit_raw = os.getenv("K8S_CPU_LIMIT") or os.getenv("RESOURCES_LIMITS_CPU")
    cpu_limit = _parse_cpu_limit(cpu_limit_raw) if cpu_limit_raw else None

    node_type = os.getenv("DIAG_NODE_TYPE", "default").strip().upper().replace("-", "_")
    env_candidates = [f"DIAG_WORKERS_{node_type}"]

    if cpu_limit is not None:
        cpu_tier = max(1, int(cpu_limit))
        env_candidates.append(f"DIAG_WORKERS_CPU_{cpu_tier}")

    env_candidates.append("DIAG_WORKERS")

    workers = None
    for key in env_candidates:
        value = os.getenv(key)
        if value:
            workers = int(value)
            break

    if workers is None:
        workers = 2

    if cpu_limit is not None:
        allowed_workers = max(1, int(cpu_limit))
        if workers > allowed_workers:
            raise ValueError(
                f"DIAG_WORKERS inválido ({workers}). resources.limits.cpu={cpu_limit_raw} "
                f"permite máximo {allowed_workers} workers."
            )

    return workers


_EXECUTOR = ProcessPoolExecutor(max_workers=_resolve_max_workers())


def _job_fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _result_cache_key(fingerprint: str) -> str:
    return f"diag:cache:{fingerprint}"


def _job_meta_key(fingerprint: str) -> str:
    return f"diag:job:{fingerprint}"


def _increment_metric(name: str, by: int = 1) -> None:
    with _METRICS_LOCK:
        _METRICS[name] = _METRICS.get(name, 0) + by


def _active_jobs_count_locked() -> int:
    return sum(1 for future in _FUTURES.values() if not future.done())


def _cleanup_stale_futures() -> None:
    now = time.time()
    expired_jobs: list[str] = []

    with _FUTURE_LOCK:
        for job_id, future in list(_FUTURES.items()):
            if future.done():
                _FUTURES.pop(job_id, None)
                continue

            meta = get_state(_job_meta_key(job_id)) or {}
            created_at = float(meta.get("created_at", now))
            timeout_s = int(meta.get("timeout_s", _JOB_TIMEOUT_S))
            if now - created_at <= timeout_s:
                continue

            future.cancel()
            expired_jobs.append(job_id)
            _FUTURES.pop(job_id, None)

    for job_id in expired_jobs:
        put_state(_job_meta_key(job_id), {"status": "timeout", "expired_at": now}, ttl_s=_JOB_TTL_S)
        _increment_metric("timeout")


def enqueue_diagnosis(payload: dict) -> dict:
    _cleanup_stale_futures()

    fingerprint = _job_fingerprint(payload)
    cached = get_state(_result_cache_key(fingerprint))
    if cached:
        return {"job_id": fingerprint, "status": "completed", "cached": True}

    meta_key = _job_meta_key(fingerprint)
    meta = get_state(meta_key)
    if meta and meta.get("status") in {"queued", "running"}:
        return {"job_id": fingerprint, "status": meta.get("status"), "cached": False}

    with _FUTURE_LOCK:
        if _active_jobs_count_locked() >= _MAX_QUEUED_JOBS:
            _increment_metric("rejected_busy")
            put_state(meta_key, {"status": "busy", "created_at": time.time()}, ttl_s=min(60, _JOB_TTL_S))
            return {"job_id": fingerprint, "status": "busy", "cached": False}

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
    _increment_metric("failed")
    raise RuntimeError(last_error or "unknown job failure")


def get_queue_metrics() -> dict:
    _cleanup_stale_futures()

    queued = 0
    running = 0
    with _FUTURE_LOCK:
        tracked_ids = list(_FUTURES.keys())

    for job_id in tracked_ids:
        meta = get_state(_job_meta_key(job_id)) or {}
        status = meta.get("status")
        if status == "queued":
            queued += 1
        elif status == "running":
            running += 1

    with _METRICS_LOCK:
        totals = dict(_METRICS)

    return {
        "queued": queued,
        "running": running,
        "failed": totals.get("failed", 0),
        "timeout": totals.get("timeout", 0),
        "rejected_busy": totals.get("rejected_busy", 0),
        "max_queued_jobs": _MAX_QUEUED_JOBS,
    }


def poll_diagnosis(job_id: str) -> dict:
    _cleanup_stale_futures()

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
