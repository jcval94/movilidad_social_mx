import hashlib
import json
import logging
import os
import socket
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from threading import Lock

from state_backend import get_state, put_state
from diagnosis_worker import compute_diagnosis

_LOGGER = logging.getLogger(__name__)

_JOB_TTL_S = int(os.getenv("DIAG_JOB_TTL_S", "86400"))
_JOB_TIMEOUT_S = int(os.getenv("DIAG_JOB_TIMEOUT_S", "120"))
_JOB_RETRIES = int(os.getenv("DIAG_JOB_RETRIES", "2"))
_MAX_QUEUED_JOBS = int(os.getenv("MAX_QUEUED_JOBS", "64"))
_FUTURE_RETENTION_S = int(os.getenv("DIAG_FUTURE_RETENTION_S", str(_JOB_TTL_S)))
_ORPHAN_REQUEUE_AFTER_S = int(os.getenv("DIAG_ORPHAN_REQUEUE_AFTER_S", "8"))
_MAX_REQUEUE_ATTEMPTS = int(os.getenv("DIAG_MAX_REQUEUE_ATTEMPTS", "1"))
_QUEUE_STUCK_GRACE_S = int(os.getenv("DIAG_QUEUE_STUCK_GRACE_S", "15"))


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

_EXECUTOR: ProcessPoolExecutor | ThreadPoolExecutor | None = None
_EXECUTOR_PID: int | None = None
_EXECUTOR_LOCK = Lock()
_FUTURES = {}
_FUTURE_LOCK = Lock()
_METRICS = {"failed": 0, "timeout": 0, "busy_rejected": 0}
_METRICS_KEY = "diag:metrics:queue"


def _resolve_executor_kind() -> str:
    """
    Selecciona el tipo de ejecutor.

    Por estabilidad usamos hilos por defecto; ProcessPool sólo con opt-in explícito
    porque en algunos despliegues WSGI/multiproceso los jobs quedan en queued.
    """
    raw_kind = (os.getenv("DIAG_EXECUTOR_KIND") or "thread").strip().lower()
    if raw_kind in {"process", "proc", "multiprocess"}:
        return "process"
    return "thread"


def _get_executor() -> ProcessPoolExecutor | ThreadPoolExecutor:
    global _EXECUTOR, _EXECUTOR_PID

    current_pid = os.getpid()
    with _EXECUTOR_LOCK:
        if _EXECUTOR is None or _EXECUTOR_PID != current_pid:
            if _EXECUTOR is not None:
                _EXECUTOR.shutdown(wait=False, cancel_futures=True)
            executor_kind = _resolve_executor_kind()
            workers = _resolve_diag_workers()
            executor_cls = ProcessPoolExecutor if executor_kind == "process" else ThreadPoolExecutor
            _EXECUTOR = executor_cls(max_workers=workers)
            _LOGGER.info("diag_executor_initialized | kind=%s workers=%s pid=%s", executor_kind, workers, current_pid)
            _EXECUTOR_PID = current_pid
    return _EXECUTOR


def _job_fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _result_cache_key(fingerprint: str) -> str:
    return f"diag:cache:{fingerprint}"


def _job_meta_key(fingerprint: str) -> str:
    return f"diag:job:{fingerprint}"


def _job_payload_key(fingerprint: str) -> str:
    return f"diag:payload:{fingerprint}"




def _log_job_event(event: str, job_id: str, **extra: object) -> None:
    details = " ".join([f"{k}={extra[k]}" for k in sorted(extra) if extra[k] is not None])
    message = f"{event} | job_id={job_id}"
    if details:
        message = f"{message} {details}"
    _LOGGER.info(message)

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


def _submit_job(job_id: str, payload: dict, timeout_s: int, retries: int) -> bool:
    try:
        future = _get_executor().submit(_run_with_retry, payload, retries, timeout_s)
    except Exception as exc:
        _log_job_event("submit_failed", job_id, error=exc, timeout_s=timeout_s, retries=retries)
        return False

    with _FUTURE_LOCK:
        _FUTURES[job_id] = {
            "future": future,
            "created_at": time.time(),
            "deadline_ts": time.time() + timeout_s,
        }

    _log_job_event("submitted", job_id, timeout_s=timeout_s, retries=retries)
    return True


def _persist_completed_job(job_id: str, result: dict) -> None:
    meta_key = _job_meta_key(job_id)
    put_state(_result_cache_key(job_id), result, ttl_s=_JOB_TTL_S)
    existing_meta = get_state(meta_key) or {}
    put_state(
        meta_key,
        {
            **existing_meta,
            "status": "completed",
            "completed_at": time.time(),
        },
        ttl_s=_JOB_TTL_S,
    )


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
                _log_job_event("timeout_reap", job_id, reason="deadline_exceeded")
                _METRICS["timeout"] += 1
                put_state(meta_key, {"status": "timeout", "error": "job timeout exceeded", "timeout_s": _JOB_TIMEOUT_S}, ttl_s=_JOB_TTL_S)
                completed_jobs.append(job_id)
                continue

            if future.done():
                try:
                    result = future.result(timeout=0)
                    _persist_completed_job(job_id, result)
                except TimeoutError:
                    _log_job_event("timeout_result", job_id, reason="future_timeout")
                    _METRICS["timeout"] += 1
                    put_state(meta_key, {"status": "timeout", "error": "job timeout exceeded", "timeout_s": _JOB_TIMEOUT_S}, ttl_s=_JOB_TTL_S)
                except Exception as exc:
                    _log_job_event("failed_result", job_id, error=exc)
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
                _log_job_event("expired_future", job_id, retention_s=_FUTURE_RETENTION_S)
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
        _log_job_event("cache_hit", fingerprint)
        return {"job_id": fingerprint, "status": "completed", "cached": True}

    meta_key = _job_meta_key(fingerprint)
    meta = get_state(meta_key)
    if meta and meta.get("status") in {"queued", "running"}:
        _log_job_event("deduplicated_active", fingerprint, status=meta.get("status"))
        return {"job_id": fingerprint, "status": meta.get("status"), "cached": False}

    now = time.time()
    put_state(
        meta_key,
        {
            "status": "queued",
            "attempt": 0,
            "created_at": now,
            "timeout_s": _JOB_TIMEOUT_S,
            "retries": _JOB_RETRIES,
        },
        ttl_s=_JOB_TTL_S,
    )
    put_state(_job_payload_key(fingerprint), payload, ttl_s=_JOB_TTL_S)

    if not _submit_job(fingerprint, payload, _JOB_TIMEOUT_S, _JOB_RETRIES):
        put_state(meta_key, {"status": "failed", "error": "worker queue unavailable"}, ttl_s=_JOB_TTL_S)
        _METRICS["failed"] += 1
        return {"job_id": fingerprint, "status": "failed", "cached": False, "error": "worker queue unavailable"}

    _log_job_event("enqueued", fingerprint, timeout_s=_JOB_TIMEOUT_S, retries=_JOB_RETRIES)
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
            _persist_completed_job(job_id, result)
            return {"status": "completed", "result": result}
        except Exception as exc:
            _METRICS["failed"] += 1
            put_state(_job_meta_key(job_id), {"status": "failed", "error": str(exc)}, ttl_s=_JOB_TTL_S)
            _log_job_event("failed_poll", job_id, error=exc)
            return {"status": "failed", "error": str(exc)}

    meta_status = meta.get("status")
    created_at = float(meta.get("created_at") or 0)
    timeout_s = int(meta.get("timeout_s") or _JOB_TIMEOUT_S)
    age_s = time.time() - created_at if created_at else 0

    if meta_status in {"queued", "running", "retrying"} and created_at:
        max_wait_s = timeout_s + _QUEUE_STUCK_GRACE_S
        if age_s >= max_wait_s:
            _METRICS["timeout"] += 1
            timeout_meta = {
                **meta,
                "status": "timeout",
                "error": "job exceeded max queue wait",
                "age_s": round(age_s, 2),
                "timeout_s": timeout_s,
            }
            put_state(_job_meta_key(job_id), timeout_meta, ttl_s=_JOB_TTL_S)
            _log_job_event("timeout_poll", job_id, status=meta_status, age_s=round(age_s,2), timeout_s=timeout_s)
            return {"status": "timeout", "meta": timeout_meta, "error": timeout_meta["error"]}

    if future is None and meta_status == "queued":
        if created_at and age_s >= _ORPHAN_REQUEUE_AFTER_S:
            requeue_count = int(meta.get("requeue_count") or 0)
            if requeue_count >= _MAX_REQUEUE_ATTEMPTS:
                timeout_meta = {
                    **meta,
                    "status": "timeout",
                    "error": "job orphaned without available worker",
                    "age_s": round(age_s, 2),
                    "timeout_s": timeout_s,
                }
                put_state(_job_meta_key(job_id), timeout_meta, ttl_s=_JOB_TTL_S)
                _log_job_event("orphan_requeue_limit", job_id, requeue_count=requeue_count, age_s=round(age_s,2))
                return {"status": "timeout", "meta": timeout_meta, "error": timeout_meta["error"]}

            payload = get_state(_job_payload_key(job_id))
            if payload:
                put_state(
                    _job_meta_key(job_id),
                    {
                        **meta,
                        "status": "queued",
                        "requeue_count": requeue_count + 1,
                        "recovered_at": time.time(),
                        "recovered_by": f"{socket.gethostname()}:{os.getpid()}",
                    },
                    ttl_s=_JOB_TTL_S,
                )
                submitted = _submit_job(
                    job_id,
                    payload,
                    int(meta.get("timeout_s") or _JOB_TIMEOUT_S),
                    int(meta.get("retries") or _JOB_RETRIES),
                )
                if not submitted:
                    failed_meta = {
                        **meta,
                        "status": "failed",
                        "error": "worker queue unavailable during recovery",
                        "age_s": round(age_s, 2),
                    }
                    put_state(_job_meta_key(job_id), failed_meta, ttl_s=_JOB_TTL_S)
                    _METRICS["failed"] += 1
                    return {"status": "failed", "meta": failed_meta, "error": failed_meta["error"]}

                _log_job_event("orphan_requeued", job_id, requeue_count=requeue_count + 1, age_s=round(age_s,2))
                return {"status": "queued", "meta": get_state(_job_meta_key(job_id))}
            _log_job_event("orphan_payload_missing", job_id, age_s=round(age_s,2))
            missing_payload_meta = {
                **meta,
                "status": "failed",
                "error": "job payload missing for orphan recovery",
                "age_s": round(age_s, 2),
            }
            put_state(_job_meta_key(job_id), missing_payload_meta, ttl_s=_JOB_TTL_S)
            _METRICS["failed"] += 1
            return {"status": "failed", "meta": missing_payload_meta, "error": missing_payload_meta["error"]}

    return {"status": meta.get("status", "queued"), "meta": meta}
