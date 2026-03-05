import hashlib
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, TimeoutError
from threading import Lock
from typing import Callable

from data_worker import build_mobility_dataset_payload
from diagnosis_worker import compute_diagnosis
from model_worker import run_class_inference
from state_backend import get_state, put_state

_JOB_TTL_S = int(os.getenv("ASYNC_JOB_TTL_S", "86400"))
_JOB_TIMEOUT_S = int(os.getenv("ASYNC_JOB_TIMEOUT_S", "120"))
_JOB_RETRIES = int(os.getenv("ASYNC_JOB_RETRIES", "2"))

_EXECUTOR = ProcessPoolExecutor(max_workers=int(os.getenv("ASYNC_WORKERS", "2")))
_FUTURES = {}
_FUTURE_LOCK = Lock()


def _job_fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _result_cache_key(job_type: str, fingerprint: str) -> str:
    return f"async:cache:{job_type}:{fingerprint}"


def _job_meta_key(job_type: str, fingerprint: str) -> str:
    return f"async:job:{job_type}:{fingerprint}"


def _run_job_with_timeout(job_runner: Callable[[str], dict], payload: dict, timeout_s: int):
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    with ThreadPoolExecutor(max_workers=1) as inner_executor:
        future = inner_executor.submit(job_runner, payload_json)
        return future.result(timeout=timeout_s)


def _run_with_retry(job_type: str, payload: dict, retries: int, timeout_s: int, job_runner: Callable[[str], dict]):
    fingerprint = _job_fingerprint(payload)
    meta_key = _job_meta_key(job_type, fingerprint)
    attempts = retries + 1
    last_error = None

    for attempt in range(1, attempts + 1):
        put_state(
            meta_key,
            {
                "status": "running",
                "attempt": attempt,
                "timeout_s": timeout_s,
                "retries": retries,
                "updated_at": time.time(),
            },
            ttl_s=_JOB_TTL_S,
        )
        try:
            result = _run_job_with_timeout(job_runner, payload, timeout_s)
            put_state(_result_cache_key(job_type, fingerprint), result, ttl_s=_JOB_TTL_S)
            put_state(meta_key, {"status": "completed", "attempt": attempt, "updated_at": time.time()}, ttl_s=_JOB_TTL_S)
            return result
        except TimeoutError:
            last_error = f"timeout after {timeout_s}s"
        except Exception as exc:
            last_error = str(exc)

        status = "retrying" if attempt < attempts else "failed"
        put_state(
            meta_key,
            {"status": status, "attempt": attempt, "error": last_error, "updated_at": time.time()},
            ttl_s=_JOB_TTL_S,
        )
        if attempt < attempts:
            time.sleep(min(2**attempt, 8))

    raise RuntimeError(last_error or "unknown job failure")


def _enqueue_job(job_type: str, payload: dict, job_runner: Callable[[str], dict]) -> dict:
    fingerprint = _job_fingerprint(payload)
    cached = get_state(_result_cache_key(job_type, fingerprint))
    if cached:
        return {"job_id": fingerprint, "status": "completed", "cached": True}

    meta_key = _job_meta_key(job_type, fingerprint)
    meta = get_state(meta_key)
    if meta and meta.get("status") in {"queued", "running", "retrying"}:
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
        _FUTURES[(job_type, fingerprint)] = _EXECUTOR.submit(
            _run_with_retry,
            job_type,
            payload,
            _JOB_RETRIES,
            _JOB_TIMEOUT_S,
            job_runner,
        )

    return {"job_id": fingerprint, "status": "queued", "cached": False}


def _poll_job(job_type: str, job_id: str) -> dict:
    cached = get_state(_result_cache_key(job_type, job_id))
    if cached:
        return {"status": "completed", "result": cached}

    meta = get_state(_job_meta_key(job_type, job_id)) or {"status": "unknown"}

    with _FUTURE_LOCK:
        future = _FUTURES.get((job_type, job_id))

    if future is not None and future.done():
        try:
            result = future.result(timeout=0)
            return {"status": "completed", "result": result}
        except Exception as exc:
            return {"status": "failed", "error": str(exc), "meta": meta}

    return {"status": meta.get("status", "queued"), "meta": meta}


def enqueue_diagnosis(payload: dict) -> dict:
    return _enqueue_job("diagnosis", payload, compute_diagnosis)


def poll_diagnosis(job_id: str) -> dict:
    return _poll_job("diagnosis", job_id)


def enqueue_data_prep() -> dict:
    payload = {"task": "mobility_dataset", "version": 1}
    return _enqueue_job("data_prep", payload, build_mobility_dataset_payload)


def poll_data_prep(job_id: str) -> dict:
    return _poll_job("data_prep", job_id)


def enqueue_class_inference(payload: dict) -> dict:
    return _enqueue_job("class_inference", payload, run_class_inference)


def poll_class_inference(job_id: str) -> dict:
    return _poll_job("class_inference", job_id)
