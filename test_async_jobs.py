import unittest
from unittest.mock import patch

import async_jobs


class AsyncJobsPollingTests(unittest.TestCase):
    def setUp(self):
        async_jobs._FUTURES.clear()
        async_jobs._METRICS = {"failed": 0, "timeout": 0, "busy_rejected": 0}

    def test_poll_queued_timeout_uses_created_at(self):
        job_id = "job-timeout"
        now = 1_000.0
        stored_meta = {
            "status": "queued",
            "attempt": 0,
            "created_at": now - 200,
            "timeout_s": 120,
            "retries": 2,
        }
        writes = {}

        def fake_get_state(key):
            if key == async_jobs._result_cache_key(job_id):
                return None
            if key == async_jobs._job_meta_key(job_id):
                return writes.get(key, stored_meta)
            if key == async_jobs._job_payload_key(job_id):
                return None
            return None

        def fake_put_state(key, value, ttl_s=3600):
            writes[key] = value

        with patch("async_jobs._reap_futures", return_value=(0, 0)), \
             patch("async_jobs.time.time", return_value=now), \
             patch("async_jobs.get_state", side_effect=fake_get_state), \
             patch("async_jobs.put_state", side_effect=fake_put_state):
            result = async_jobs.poll_diagnosis(job_id)

        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["meta"]["status"], "timeout")
        self.assertIn("job exceeded max queue wait", result["error"])
        self.assertEqual(async_jobs._METRICS["timeout"], 1)

    def test_merge_job_meta_preserves_existing_fields(self):
        job_id = "job-meta"
        existing = {
            "status": "queued",
            "created_at": 900.0,
            "retries": 2,
        }
        writes = {}

        def fake_get_state(key):
            if key == async_jobs._job_meta_key(job_id):
                return existing
            return None

        def fake_put_state(key, value, ttl_s=3600):
            writes[key] = value

        with patch("async_jobs.get_state", side_effect=fake_get_state), \
             patch("async_jobs.put_state", side_effect=fake_put_state), \
             patch("async_jobs.time.time", return_value=1000.0):
            merged = async_jobs._merge_job_meta(job_id, {"status": "running", "attempt": 1})

        self.assertEqual(merged["created_at"], 900.0)
        self.assertEqual(merged["status"], "running")
        self.assertEqual(merged["attempt"], 1)
        self.assertIn("updated_at", merged)
        self.assertEqual(writes[async_jobs._job_meta_key(job_id)]["created_at"], 900.0)


if __name__ == "__main__":
    unittest.main()
