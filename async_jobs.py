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
_MAX_QUEUED_JOBS = int(os.getenv("MAX_QUEUED_JOBS", "64"))
_FUTURE_RETENTION_S = int(os.getenv("DIAG_FUTURE_RETENTION_S", str(_JOB_TTL_S)))


def _parse_cpu_to_cores(raw_cpu: str | None) -> float | None:
    if not raw_cpu:
        return None
    value = raw_cpu.strip().lower()
    if not value:
        return None
    try:
        if value.endswith("m"):
            return float(value[:-1]) / 1000
        return float(value)
    except ValueError:
        return None


def _resolve_cpu_limit_cores() -> float:
    explicit_cpu_limit = _parse_cpu_to_cores(os.getenv("RESOURCES_LIMITS_CPU") or os.getenv("DIAG_CPU_LIMIT"))
    if explicit_cpu_limit and explicit_cpu_limit > 0:
        return explicit_cpu_limit
    return float(os.cpu_count() or 1)


def _resolve_diag_workers() -> int:
    cpu_count = os.cpu_count() or 1
    node_type = (os.getenv("DIAG_NODE_TYPE") or "").strip().upper().replace("-", "_")
    worker_candidates = []
    if node_type:
        worker_candidates.append(os.getenv(f"DIAG_WORKERS_{node_type}"))
    worker_candidates.extend(
        [
            os.getenv(f"DIAG_WORKERS_CPU_{cpu_count}"),
            os.getenv("DIAG_WORKERS"),
            "2",
        ]
    )

    configured = next((v for v in worker_candidates if v), "2")
    requested_workers = max(1, int(configured))
    cpu_limit = _resolve_cpu_limit_cores()
    max_workers_by_limit = max(1, int(cpu_limit))
    return min(requested_workers, max_workers_by_limit)

_EXECUTOR = ProcessPoolExecutor(max_workers=_resolve_diag_workers())
_FUTURES = {}
_FUTURE_LOCK = Lock()
_METRICS = {"failed": 0, "timeout": 0, "busy_rejected": 0}
_METRICS_KEY = "diag:metrics:queue"


def _job_fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _result_cache_key(fingerprint: str) -> str:
    return f"diag:cache:{fingerprint}"


def _job_meta_key(fingerprint: str) -> str:
    return f"diag:job:{fingerprint}"


def _publish_metrics(queued: int, running: int) -> None:
    snapshot = {
        "queued": queued,
        "running": running,
        "failed": _METRICS["failed"],
        "timeout": _METRICS["timeout"],
        "busy_rejected": _METRICS["busy_rejected"],
        "updated_at": time.time(),
    }
    put_state(_METRICS_KEY, snapshot, ttl_s=_JOB_TTL_S)


def _reap_futures() -> tuple[int, int]:
    now = time.time()
    queued = 0
    running = 0
    completed_jobs = []

    with _FUTURE_LOCK:
        for job_id, job_data in list(_FUTURES.items()):
            future = job_data["future"]
            meta_key = _job_meta_key(job_id)
            deadline_ts = job_data["deadline_ts"]
            if deadline_ts <= now and not future.done():
                future.cancel()
                _METRICS["timeout"] += 1
                put_state(meta_key, {"status": "timeout", "error": "job timeout exceeded", "timeout_s": _JOB_TIMEOUT_S}, ttl_s=_JOB_TTL_S)
                completed_jobs.append(job_id)
                continue

            if future.done():
                try:
                    future.result(timeout=0)
                except TimeoutError:
                    _METRICS["timeout"] += 1
                    put_state(meta_key, {"status": "timeout", "error": "job timeout exceeded", "timeout_s": _JOB_TIMEOUT_S}, ttl_s=_JOB_TTL_S)
                except Exception as exc:
                    _METRICS["failed"] += 1
                    put_state(meta_key, {"status": "failed", "error": str(exc)}, ttl_s=_JOB_TTL_S)
                completed_jobs.append(job_id)
                continue

            meta = get_state(meta_key) or {}
            status = meta.get("status")
            if status == "running":
                running += 1
            else:
                queued += 1

            if now - job_data["created_at"] > _FUTURE_RETENTION_S:
                future.cancel()
                put_state(meta_key, {"status": "expired", "error": "future expired before completion"}, ttl_s=_JOB_TTL_S)
                completed_jobs.append(job_id)

        for job_id in completed_jobs:
            _FUTURES.pop(job_id, None)

    _publish_metrics(queued, running)
    return queued, running


def get_queue_metrics() -> dict:
    queued, running = _reap_futures()
    return {
        "queued": queued,
        "running": running,
        "failed": _METRICS["failed"],
        "timeout": _METRICS["timeout"],
        "busy_rejected": _METRICS["busy_rejected"],
    }


def enqueue_diagnosis(payload: dict) -> dict:
    queued, _ = _reap_futures()
    if queued >= _MAX_QUEUED_JOBS:
        _METRICS["busy_rejected"] += 1
        _publish_metrics(queued, 0)
        return {
            "job_id": None,
            "status": "busy",
            "cached": False,
            "reason": f"queue_limit_exceeded:{_MAX_QUEUED_JOBS}",
        }

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
        _FUTURES[fingerprint] = {
            "future": _EXECUTOR.submit(_run_with_retry, payload, _JOB_RETRIES, _JOB_TIMEOUT_S),
            "created_at": time.time(),
            "deadline_ts": time.time() + _JOB_TIMEOUT_S,
        }

    _publish_metrics(queued + 1, 0)

    return {"job_id": fingerprint, "status": "queued", "cached": False}


def _run_with_retry(payload: dict, retries: int, timeout_s: int) -> dict:
    fingerprint = _job_fingerprint(payload)
    meta_key = _job_meta_key(fingerprint)
    attempts = retries + 1
    last_error = None
    started_at = time.time()

    for attempt in range(1, attempts + 1):
        if time.time() - started_at > timeout_s:
            put_state(meta_key, {"status": "timeout", "attempt": attempt, "timeout_s": timeout_s}, ttl_s=_JOB_TTL_S)
            raise TimeoutError("job timeout exceeded")
        put_state(meta_key, {"status": "running", "attempt": attempt, "timeout_s": _JOB_TIMEOUT_S, "retries": retries}, ttl_s=_JOB_TTL_S)
        try:
            result = compute_diagnosis(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            if time.time() - started_at > timeout_s:
                put_state(meta_key, {"status": "timeout", "attempt": attempt, "timeout_s": timeout_s}, ttl_s=_JOB_TTL_S)
                raise TimeoutError("job timeout exceeded")
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
    _reap_futures()
    cached = get_state(_result_cache_key(job_id))
    if cached:
        return {"status": "completed", "result": cached}

    meta = get_state(_job_meta_key(job_id)) or {"status": "unknown"}

    with _FUTURE_LOCK:
        future_info = _FUTURES.get(job_id)

    future = future_info["future"] if future_info else None

    if future is not None and future.done():
        try:
            result = future.result(timeout=0)
            return {"status": "completed", "result": result}
        except Exception as exc:
            _METRICS["failed"] += 1
            put_state(_job_meta_key(job_id), {"status": "failed", "error": str(exc)}, ttl_s=_JOB_TTL_S)
            return {"status": "failed", "error": str(exc)}

    return {"status": meta.get("status", "queued"), "meta": meta}
