# index-retriever-mcp-server — Config Models
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Pydantic models for service configuration.

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HttpServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8686


class McpServerConfig(BaseModel):
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8687


class ServerConfig(BaseModel):
    http: HttpServerConfig = Field(default_factory=HttpServerConfig)
    mcp: McpServerConfig = Field(default_factory=McpServerConfig)


class JwtConfig(BaseModel):
    issuer: str
    audience: str
    public_keys_url: str


class AuthConfig(BaseModel):
    mode: str = "apikey+jwt"
    jwt: JwtConfig


class DbConfig(BaseModel):
    url: str


class AuditStorageConfig(BaseModel):
    path: str


class StorageConfig(BaseModel):
    db: DbConfig
    audit: AuditStorageConfig


class RetryConfig(BaseModel):
    max_attempts: int = 3
    backoff_seconds: int = 5


class RedisConfig(BaseModel):
    enabled: bool = False
    url: str = ""


class QueueConfig(BaseModel):
    max_concurrency: int = 8
    per_profile_concurrency: int = 2
    default_timeout_seconds: int = 1800
    retry: RetryConfig = Field(default_factory=RetryConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)


class ChromaBackendConfig(BaseModel):
    mode: str = "local"
    path: str
    collection: str = "default"


class VdbConfig(BaseModel):
    type: str
    chroma: ChromaBackendConfig | None = None


class OpenAiCompatConfig(BaseModel):
    base_url: str
    api_key: str
    model: str
    timeout_seconds: int = 60


class EmbeddingsConfig(BaseModel):
    provider: str
    openai_compat: OpenAiCompatConfig | None = None


class DedupeConfig(BaseModel):
    mode: str = "hash"
    policy: str = "skip"


class FileSystemIngestionConfig(BaseModel):
    roots: list[str] = Field(default_factory=list)
    deny_globs: list[str] = Field(default_factory=list)


class IngestionConfig(BaseModel):
    allowed_sources: list[str] = Field(default_factory=lambda: ["upload", "text"])
    filesystem: FileSystemIngestionConfig = Field(default_factory=FileSystemIngestionConfig)
    max_file_mb: int = 50
    dedupe: DedupeConfig = Field(default_factory=DedupeConfig)


class ChunkingConfig(BaseModel):
    strategy: str = "token"
    chunk_size: int = 800
    chunk_overlap: int = 100


class SearchConfig(BaseModel):
    top_k_default: int = 10
    score_threshold: float = 0.0


class ProfileConfig(BaseModel):
    enabled: bool = True
    vdb: VdbConfig
    embeddings: EmbeddingsConfig
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)


class RbacConfig(BaseModel):
    enabled: bool = True
    default_deny: bool = True
    roles: dict[str, list[str]] = Field(default_factory=dict)


class GlobalConfig(BaseModel):
    server: ServerConfig
    auth: AuthConfig
    storage: StorageConfig
    queue: QueueConfig = Field(default_factory=QueueConfig)
    profiles: dict[str, ProfileConfig]
    rbac: RbacConfig = Field(default_factory=RbacConfig)

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> GlobalConfig:
        return cls.model_validate(value)
