# index-retriever-mcp-server — ST1.11
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Local cloud_dog_jobs enqueue and retrieval.

from tests.local_runtime import LocalIndexRuntime


def test_job_enqueue_execute(local_service: LocalIndexRuntime) -> None:
    rec = local_service.ingest_text("default", "st_jobs", "job payload", "api://jobs", actor="system")
    job = local_service.job_get(rec.job_id)
    assert job is not None
    assert str(job.job_type) == "ingest_text"
