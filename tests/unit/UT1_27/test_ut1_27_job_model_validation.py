# index-retriever-mcp-server — UT1.27
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests job model validation.

from index_tools.queue.models import JobRecord


def test_job_model_validation() -> None:
    job = JobRecord(job_id="j1", profile="default", collection="kb", job_type="ingest")
    assert job.status.value == "queued"
