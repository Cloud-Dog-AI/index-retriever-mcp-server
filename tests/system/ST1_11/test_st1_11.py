# index-retriever-mcp-server — ST1.11
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Live cloud_dog_jobs enqueue and retrieval.

from tests.live_runtime import LiveIndexRuntime


def test_job_enqueue_execute(live_service: LiveIndexRuntime) -> None:
    rec = live_service.ingest_text("default", "st_jobs", "job payload", "api://jobs", actor="system")
    job = live_service.job_get(rec.job_id)
    assert job is not None
    assert str(job.job_type) == "ingest_text"
