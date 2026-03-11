# index-retriever-mcp-server — W23A Helpers
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Shared helpers for W23A multi-backend, parser, and embedding test matrices.

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from cloud_dog_vdb import CollectionSpec, Record, SearchRequest, get_vdb_client
from cloud_dog_vdb.ingestion import ParserIngestionOptions, build_parser_registry, ingest_document

from tests.live_runtime import load_vault_dev_config

VDB_PROVIDER_IDS: tuple[str, ...] = ("chroma", "qdrant", "opensearch", "pgvector", "weaviate", "infinity")
PARSER_PROVIDER_IDS: tuple[str, ...] = ("deepdoc", "docling", "mineru", "marker_mcp", "transformers", "internal")
EMBEDDING_MODELS: tuple[str, ...] = ("bge-m3:567m", "nomic-embed-text", "granite-embedding:278m")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKING_DIR = PROJECT_ROOT / "working"
PLATFORM_VDB_TEST_DATA = (
    PROJECT_ROOT.parent
    / "cloud-dog-ai-platform-standards"
    / "packages"
    / "backend"
    / "platform-vdb"
    / "test-data"
)


def _is_true(raw: Any) -> bool:
    return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}


def _clean_text(raw: Any) -> str:
    return str(raw or "").strip().strip('"').strip("'")


@lru_cache(maxsize=1)
def vault_dev_config() -> dict[str, Any]:
    payload = load_vault_dev_config(required=False)
    return payload if isinstance(payload, dict) else {}


@lru_cache(maxsize=1)
def vault_vdbs() -> dict[str, dict[str, Any]]:
    raw = vault_dev_config().get("vdbs", {})
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for key, value in raw.items():
        if isinstance(value, dict):
            out[str(key).strip().lower()] = dict(value)
    return out


def _service_alias(services: dict[str, Any], aliases: tuple[str, ...]) -> dict[str, Any]:
    for alias in aliases:
        cfg = services.get(alias)
        if isinstance(cfg, dict) and cfg:
            return dict(cfg)
    return {}


@lru_cache(maxsize=1)
def parser_services_config() -> dict[str, dict[str, Any]]:
    services_raw = vault_dev_config().get("services", {})
    services = services_raw if isinstance(services_raw, dict) else {}

    mineru = _service_alias(services, ("mineru",))
    marker = _service_alias(services, ("marker_mcp", "markermcp", "marker-mcp", "marker"))
    deepdoc = _service_alias(services, ("deepdoc",))
    docling = _service_alias(services, ("docling",))
    transformers = _service_alias(services, ("transformers", "transformer_parser", "pdf_transformers"))

    # Env overlays for parser providers.
    mineru.setdefault("base_url", _clean_text(os.getenv("MINERU_BASE_URL")))
    mineru.setdefault("api_key", _clean_text(os.getenv("MINERU_API_KEY")))
    mineru.setdefault("enabled", _is_true(os.getenv("MINERU_ENABLED")) or bool(_clean_text(mineru.get("base_url"))))

    marker.setdefault("base_url", _clean_text(os.getenv("MARKER_MCP_BASE_URL")))
    marker.setdefault("auth_token", _clean_text(os.getenv("MARKER_MCP_AUTH_TOKEN")))
    marker.setdefault(
        "enabled",
        _is_true(os.getenv("MARKER_MCP_ENABLED")) or bool(_clean_text(marker.get("base_url"))),
    )
    marker.setdefault(
        "busy_retry_max_delay_seconds", _parse_float(os.getenv("MARKER_MCP_BUSY_RETRY_MAX_DELAY_SECONDS"), 60.0)
    )

    deepdoc_command = _clean_text(os.getenv("DEEPDOC_COMMAND"))
    if deepdoc_command and "command" not in deepdoc:
        deepdoc["command"] = deepdoc_command.split()
    deepdoc.setdefault("enabled", _is_true(os.getenv("DEEPDOC_ENABLED")) or bool(deepdoc.get("command")))

    docling_command = _clean_text(os.getenv("DOCLING_COMMAND"))
    if docling_command and "command" not in docling:
        docling["command"] = docling_command.split()
    docling.setdefault("enabled", _is_true(os.getenv("DOCLING_ENABLED")) or bool(docling.get("command")))

    transformers_command = _clean_text(os.getenv("TRANSFORMERS_COMMAND"))
    transformers_base_url = _clean_text(os.getenv("TRANSFORMERS_BASE_URL"))
    if transformers_command and "command" not in transformers:
        transformers["command"] = transformers_command.split()
    if transformers_base_url and not transformers.get("base_url"):
        transformers["base_url"] = transformers_base_url
    transformers.setdefault(
        "enabled",
        _is_true(os.getenv("TRANSFORMERS_ENABLED"))
        or bool(transformers.get("command"))
        or bool(_clean_text(transformers.get("base_url"))),
    )

    return {
        "mineru": mineru,
        "marker_mcp": marker,
        "deepdoc": deepdoc,
        "docling": docling,
        "transformers": transformers,
    }


def _provider_env_config(provider_id: str) -> dict[str, Any]:
    provider = provider_id.strip().lower()
    if provider == "chroma":
        return {
            "base_url": _clean_text(os.getenv("CLOUD_DOG__INDEX__VDB__CHROMA_URL") or os.getenv("CHROMA_URL")),
            "auth_token": _clean_text(
                os.getenv("CLOUD_DOG__INDEX__VDB__CHROMA_AUTH_TOKEN") or os.getenv("CHROMA_AUTH_TOKEN")
            ),
        }
    if provider == "qdrant":
        host = _clean_text(os.getenv("CLOUD_DOG__INDEX__VDB__HOST") or os.getenv("QDRANT_HOST"))
        port = _clean_text(os.getenv("CLOUD_DOG__INDEX__VDB__PORT") or os.getenv("QDRANT_PORT"))
        url = _clean_text(os.getenv("CLOUD_DOG__INDEX__VDB__QDRANT_URL") or os.getenv("QDRANT_URL"))
        if not url and host:
            url = f"http://{host}:{port or '6333'}"
        return {
            "base_url": url,
            "api_key": _clean_text(
                os.getenv("CLOUD_DOG__INDEX__VDB__QDRANT_API_KEY")
                or os.getenv("CLOUD_DOG__INDEX__VDB__API_KEY")
                or os.getenv("QDRANT_API_KEY")
            ),
        }
    if provider == "opensearch":
        host = _clean_text(os.getenv("CLOUD_DOG__INDEX__VDB__OPENSEARCH_HOST") or os.getenv("OPENSEARCH_HOST"))
        port = _clean_text(os.getenv("CLOUD_DOG__INDEX__VDB__OPENSEARCH_PORT") or os.getenv("OPENSEARCH_PORT"))
        url = _clean_text(
            os.getenv("CLOUD_DOG__INDEX__VDB__OPENSEARCH_URL")
            or os.getenv("CLOUD_DOG__INDEX__VDB__OPENSEARCH_BASE_URL")
            or os.getenv("OPENSEARCH_URL")
        )
        if not url and host:
            url = f"http://{host}:{port or '9200'}"
        return {
            "base_url": url,
            "username": _clean_text(
                os.getenv("CLOUD_DOG__INDEX__VDB__OPENSEARCH_USERNAME") or os.getenv("OPENSEARCH_USERNAME")
            ),
            "password": _clean_text(
                os.getenv("CLOUD_DOG__INDEX__VDB__OPENSEARCH_PASSWORD") or os.getenv("OPENSEARCH_PASSWORD")
            ),
        }
    if provider == "pgvector":
        return {
            "database_uri": _clean_text(
                os.getenv("CLOUD_DOG__INDEX__VDB__PGVECTOR_DATABASE_URI")
                or os.getenv("PGVECTOR_DATABASE_URI")
                or os.getenv("CLOUD_DOG__INDEX__VDB__PGVECTOR_URL")
            )
        }
    if provider == "weaviate":
        return {
            "base_url": _clean_text(os.getenv("CLOUD_DOG__INDEX__VDB__WEAVIATE_URL") or os.getenv("WEAVIATE_URL")),
            "api_key": _clean_text(
                os.getenv("CLOUD_DOG__INDEX__VDB__WEAVIATE_API_KEY") or os.getenv("WEAVIATE_API_KEY")
            ),
        }
    if provider == "infinity":
        host = _clean_text(os.getenv("CLOUD_DOG__INDEX__VDB__INFINITY_HOST") or os.getenv("INFINITY_HOST"))
        port = _clean_text(os.getenv("CLOUD_DOG__INDEX__VDB__INFINITY_PORT") or os.getenv("INFINITY_PORT"))
        url = _clean_text(os.getenv("CLOUD_DOG__INDEX__VDB__INFINITY_URL") or os.getenv("INFINITY_URL"))
        if not url and host:
            url = f"http://{host}:{port or '8080'}"
        return {
            "base_url": url,
            "api_key": _clean_text(os.getenv("CLOUD_DOG__INDEX__VDB__INFINITY_API_KEY") or os.getenv("INFINITY_API_KEY")),
        }
    return {}


def backend_config(provider_id: str) -> dict[str, Any]:
    provider = provider_id.strip().lower()
    vault_cfg = dict(vault_vdbs().get(provider, {}))
    env_cfg = _provider_env_config(provider)
    merged = dict(vault_cfg)
    for key, value in env_cfg.items():
        if value in ("", None):
            continue
        merged[key] = value

    if provider == "qdrant":
        if not merged.get("base_url") and merged.get("url"):
            merged["base_url"] = merged.get("url")
    if provider == "opensearch":
        if not merged.get("base_url") and merged.get("url"):
            merged["base_url"] = merged.get("url")
    if provider == "pgvector":
        if not merged.get("database_uri") and merged.get("url"):
            merged["database_uri"] = merged.get("url")
    if provider == "weaviate":
        if not merged.get("base_url") and merged.get("url"):
            merged["base_url"] = merged.get("url")
    if provider == "infinity":
        if not merged.get("base_url") and merged.get("url"):
            merged["base_url"] = merged.get("url")

    return merged


def backend_available(provider_id: str) -> bool:
    cfg = backend_config(provider_id)
    provider = provider_id.strip().lower()
    if provider == "pgvector":
        return bool(_clean_text(cfg.get("database_uri")))
    return bool(_clean_text(cfg.get("base_url")) or (_clean_text(cfg.get("host")) and cfg.get("port")))


def backend_skip_reason(provider_id: str) -> str | None:
    if backend_available(provider_id):
        return None
    return f"{provider_id} backend not configured via env/Vault"


def runtime_backend_store(provider_id: str, timeout_seconds: int = 120) -> dict[str, Any]:
    cfg = backend_config(provider_id)
    out: dict[str, Any] = {"enabled": True, "local_mode": False, "timeout_seconds": int(timeout_seconds)}
    for key in (
        "base_url",
        "url",
        "api_key",
        "auth_token",
        "host",
        "port",
        "username",
        "password",
        "database",
        "database_uri",
        "tls",
        "ssl",
    ):
        value = cfg.get(key)
        if value in ("", None):
            continue
        out[key] = value
    return out


def build_vdb_client(provider_id: str, timeout_seconds: int = 120):
    runtime_config = {
        "vector_stores": {
            "default_backend": provider_id,
            provider_id: runtime_backend_store(provider_id, timeout_seconds=timeout_seconds),
        }
    }
    return get_vdb_client(runtime_config)


def parser_registry_from_services() -> Any:
    return build_parser_registry(parser_services_config())


def parser_available(provider_id: str) -> bool:
    if provider_id == "internal":
        return True
    cfg = parser_services_config().get(provider_id, {})
    if not isinstance(cfg, dict):
        return False
    if _is_true(cfg.get("enabled")):
        return True
    command = cfg.get("command")
    if isinstance(command, list) and command:
        return True
    return bool(_clean_text(cfg.get("base_url")))


def parser_skip_reason(provider_id: str) -> str | None:
    if parser_available(provider_id):
        return None
    return f"{provider_id} parser provider not configured via env/Vault"


def corpus_file(*preferred: str) -> Path:
    candidates = list(preferred) if preferred else [
        "Examples.pdf",
        "Z83-example.pdf",
        "ITEM_COD-0012-0001-_-089.pdf",
        "IBRD-Financial-Statements-June-2025.pdf",
    ]
    for name in candidates:
        path = PLATFORM_VDB_TEST_DATA / name
        if path.is_file():
            return path
    fallback = sorted(PLATFORM_VDB_TEST_DATA.glob("*.pdf"))
    if fallback:
        return fallback[0]
    raise FileNotFoundError(f"No corpus PDF files found in {PLATFORM_VDB_TEST_DATA}")


@lru_cache(maxsize=1)
def embedding_matrix() -> list[dict[str, str]]:
    models_raw = vault_dev_config().get("models", {})
    models = models_raw if isinstance(models_raw, dict) else {}

    def _from_vault(match_token: str, model_name: str) -> dict[str, str]:
        for key, value in models.items():
            if match_token not in str(key):
                continue
            if not isinstance(value, dict):
                continue
            base_url = _clean_text(value.get("base_url"))
            api_key = _clean_text(value.get("api_key"))
            model = _clean_text(value.get("model")) or model_name
            if base_url:
                return {"model": model, "base_url": base_url, "api_key": api_key}
        return {}

    default_base_url = _clean_text(
        os.getenv("CLOUD_DOG__INDEX__EMBEDDING__BASE_URL") or os.getenv("EMBED_BASE_URL")
    )
    default_api_key = _clean_text(os.getenv("CLOUD_DOG__INDEX__EMBEDDING__API_KEY") or os.getenv("EMBED_API_KEY"))

    matrix: list[dict[str, str]] = []
    for token, model_name in (
        ("bge_m3_567m", "bge-m3:567m"),
        ("nomic_embed_text", "nomic-embed-text"),
        ("granite_embedding_278m", "granite-embedding:278m"),
    ):
        cfg = _from_vault(token, model_name)
        if not cfg:
            cfg = {
                "model": model_name,
                "base_url": default_base_url,
                "api_key": default_api_key,
            }
        if cfg.get("base_url"):
            matrix.append(cfg)
    return matrix


def write_artifact_json(name: str, payload: dict[str, Any]) -> Path:
    WORKING_DIR.mkdir(parents=True, exist_ok=True)
    out = WORKING_DIR / name
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return out


async def run_backend_contract(provider_id: str) -> dict[str, Any]:
    client = build_vdb_client(provider_id)
    collection = f"w23a_it2_{provider_id}_contract"
    created = False
    try:
        await client.delete_collection(collection, provider_id=provider_id)
    except Exception:
        pass

    try:
        await client.create_collection(CollectionSpec(name=collection, embedding_dim=8), provider_id=provider_id)
        created = True
        record_id = f"w23a-{provider_id}-r1"
        await client.upsert_records(
            collection,
            [
                Record(
                    record_id=record_id,
                    content=f"w23a contract payload for {provider_id}",
                    metadata={
                        "tenant_id": "w23a",
                        "provider": provider_id,
                        "document_id": f"W23A-{provider_id}",
                        "source_uri": f"api://w23a/it2/{provider_id}",
                        "source_type": "api",
                    },
                )
            ],
            provider_id=provider_id,
        )
        result = await client.search(
            collection,
            SearchRequest(query_text="contract payload", top_k=5, filters={"tenant_id": "w23a"}),
            provider_id=provider_id,
        )
        deleted = await client.delete_record(collection, record_id, provider_id=provider_id)
        count_after = await client.count_documents(collection, provider_id=provider_id)
        return {
            "provider": provider_id,
            "results": len(result.results),
            "deleted": bool(deleted),
            "count_after": int(count_after),
        }
    finally:
        if created:
            try:
                await client.delete_collection(collection, provider_id=provider_id)
            except Exception:
                pass


async def run_backend_parser_pipeline(
    provider_id: str,
    *,
    parser_chain: list[str],
    parser_services: dict[str, dict[str, Any]] | None = None,
    source_path: Path | None = None,
) -> dict[str, Any]:
    client = build_vdb_client(provider_id)
    collection = f"w23a_at2_{provider_id}_pipeline"
    created = False
    source = source_path or corpus_file("Examples.pdf")

    try:
        await client.delete_collection(collection, provider_id=provider_id)
    except Exception:
        pass

    try:
        await client.create_collection(CollectionSpec(name=collection, embedding_dim=8), provider_id=provider_id)
        created = True
        ids = await ingest_document(
            client,
            collection,
            source.read_bytes(),
            source_uri=f"file://{source.name}",
            options=ParserIngestionOptions(
                parser_chain=list(parser_chain),
                parser_options={},
                ocr_mode="disabled",
                table_policy="table_as_markdown",
                chunk_size=700,
                chunk_overlap=100,
            ),
            parser_services=parser_services or parser_services_config(),
            metadata={"tenant_id": "w23a", "source_type": "file", "stage": "at2.5"},
        )
        rows = await client.search(
            collection,
            SearchRequest(query_text="form", top_k=5, filters={"tenant_id": "w23a"}),
            provider_id=provider_id,
        )
        retrieved = None
        if rows.results:
            retrieved = await client.get_record(collection, str(rows.results[0].id), provider_id=provider_id)
        return {
            "provider": provider_id,
            "record_ids": [str(item) for item in ids],
            "search_hits": len(rows.results),
            "retrieved": bool(retrieved),
        }
    finally:
        if created:
            try:
                await client.delete_collection(collection, provider_id=provider_id)
            except Exception:
                pass
