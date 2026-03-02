# index-retriever-mcp-server — IT1.16
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Delegation boundary check: parser/OCR/table internals executed via cloud_dog_vdb.

from tests.live_runtime import LiveIndexRuntime


def test_delegation_boundary_via_cloud_dog_vdb_pipeline(live_service: LiveIndexRuntime) -> None:
    preview = live_service.ingest_preview(
        text="column_a|column_b\n1|2\n3|4",
        source_uri="file://integration/table-doc.txt",
        parser_chain=["internal"],
        ocr_mode="auto",
        table_policy="table_as_json",
    )
    assert preview["parser_provider"] == "internal"
    assert preview["table_policy"] == "table_as_json"
    assert preview["chunk_count"] >= 1
    assert any(step["stage"] == "parse" for step in preview["checkpoints"])

    extract = live_service.extract_only(
        text="Delegated extract payload for parser boundary verification",
        source_uri="file://integration/extract-doc.txt",
        parser_chain=["internal"],
    )
    assert extract["parser_provider"] == "internal"
    assert extract["chunk_count"] >= 1

    tables = live_service.table_extract(
        text="col1|col2\nleft|right",
        source_uri="file://integration/table-only.txt",
        parser_chain=["internal"],
        table_policy="table_as_json",
    )
    assert tables["parser_provider"] == "internal"
    assert tables["table_count"] >= 1
