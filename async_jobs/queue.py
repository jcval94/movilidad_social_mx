import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

from async_jobs.store import get_cached_result, init_store, upsert_result

DEFAULT_QUEUE_NAME = os.getenv("JOB_QUEUE_NAME", "diagnostics")


@dataclass
class JobConfig:
    timeout_s: int = int(os.getenv("JOB_TIMEOUT_SECONDS", "90"))
    retries: int = int(os.getenv("JOB_RETRIES", "2"))
    retry_intervals: list[int] = None

    def __post_init__(self):
        if self.retry_intervals is None:
            self.retry_intervals = [5, 20]


def compute_idempotency_key(payload: dict[str, Any]) -> str:
    stable = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def get_queue():
    from redis import Redis
    from rq import Queue

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    conn = Redis.from_url(redis_url)
    return Queue(DEFAULT_QUEUE_NAME, connection=conn)


def enqueue_section4_job(payload: dict[str, Any], job_config: JobConfig | None = None) -> dict[str, str]:
    from rq import Retry

    init_store()
    job_config = job_config or JobConfig()

    idempotency_key = compute_idempotency_key(payload)
    cached = get_cached_result(idempotency_key)
    if cached and cached.get("status") == "finished":
        return {"job_id": f"cached:{idempotency_key}", "idempotency_key": idempotency_key, "status": "cached"}

    payload_with_key = {**payload, "idempotency_key": idempotency_key}
    upsert_result(idempotency_key=idempotency_key, status="queued")

    queue = get_queue()
    job = queue.enqueue(
        "async_jobs.tasks.run_section4_diagnostic_job",
        payload_with_key,
        job_id=idempotency_key,
        job_timeout=job_config.timeout_s,
        retry=Retry(max=job_config.retries, interval=job_config.retry_intervals),
    )
    return {"job_id": job.id, "idempotency_key": idempotency_key, "status": "queued"}


def fetch_section4_job_status(idempotency_key: str) -> dict[str, Any]:
    init_store()
    cached = get_cached_result(idempotency_key)
    if cached:
        return cached

    return {"status": "unknown"}
