# index-retriever-mcp-server — UT1.30
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests pipeline progress event emission order.

from index_tools.pipeline.ingest import IngestPipeline


def test_pipeline_progress_events() -> None:
    upserts: list[tuple[str, list[str], list[list[float]]]] = []

    def upsert(doc_id: str, chunks: list[str], vectors: list[list[float]]) -> None:
        upserts.append((doc_id, chunks, vectors))

    pipeline = IngestPipeline(
        fetch_content=lambda _: b"hello world",
        convert_content=lambda b: b.decode("utf-8"),
        chunk_content=lambda t: [t],
        embed_chunks=lambda chunks: [[0.1, 0.2] for _ in chunks],
        upsert_vectors=upsert,
    )

    result, progress = pipeline.run(source="x", doc_id="doc1")
    assert result.doc_id == "doc1"
    assert progress == ["fetched", "converted", "chunked", "embedded", "upserted"]
    assert upserts[0][0] == "doc1"
