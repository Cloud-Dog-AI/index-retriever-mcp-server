# index-retriever-mcp-server — Config Models
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Pydantic models for service configuration.

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HttpServerConfig(BaseModel):
    """HttpServerConfig definition."""

    host: str = "0.0.0.0"
    port: int = 8686


class McpServerConfig(BaseModel):
    """McpServerConfig definition."""

    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8687


class ServerConfig(BaseModel):
    """ServerConfig definition."""

    http: HttpServerConfig = Field(default_factory=HttpServerConfig)
    mcp: McpServerConfig = Field(default_factory=McpServerConfig)


class JwtConfig(BaseModel):
    """JwtConfig definition."""

    issuer: str
    audience: str
    public_keys_url: str


class AuthConfig(BaseModel):
    """AuthConfig definition."""

    mode: str = "apikey+jwt"
    jwt: JwtConfig


class DbConfig(BaseModel):
    """DbConfig definition."""

    url: str


class AuditStorageConfig(BaseModel):
    """AuditStorageConfig definition."""

    path: str


class StorageConfig(BaseModel):
    """StorageConfig definition."""

    db: DbConfig
    audit: AuditStorageConfig


class RetryConfig(BaseModel):
    """RetryConfig definition."""

    max_attempts: int = 3
    backoff_seconds: int = 5


class RedisConfig(BaseModel):
    """RedisConfig definition."""

    enabled: bool = False
    url: str = ""


class QueueConfig(BaseModel):
    """QueueConfig definition."""

    max_concurrency: int = 8
    per_profile_concurrency: int = 2
    default_timeout_seconds: int = 1800
    retry: RetryConfig = Field(default_factory=RetryConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)


class ChromaBackendConfig(BaseModel):
    """ChromaBackendConfig definition."""

    mode: str = "local"
    path: str
    collection: str = "default"


class VdbConfig(BaseModel):
    """VdbConfig definition."""

    type: str
    chroma: ChromaBackendConfig | None = None


class OpenAiCompatConfig(BaseModel):
    """OpenAiCompatConfig definition."""

    base_url: str
    api_key: str
    model: str
    timeout_seconds: int = 60


class EmbeddingsConfig(BaseModel):
    """EmbeddingsConfig definition."""

    provider: str
    openai_compat: OpenAiCompatConfig | None = None


class DedupeConfig(BaseModel):
    """DedupeConfig definition."""

    mode: str = "hash"
    policy: str = "skip"


class FileSystemIngestionConfig(BaseModel):
    """FileSystemIngestionConfig definition."""

    roots: list[str] = Field(default_factory=list)
    deny_globs: list[str] = Field(default_factory=list)


class IngestionConfig(BaseModel):
    """IngestionConfig definition."""

    allowed_sources: list[str] = Field(default_factory=lambda: ["upload", "text"])
    filesystem: FileSystemIngestionConfig = Field(default_factory=FileSystemIngestionConfig)
    max_file_mb: int = 50
    dedupe: DedupeConfig = Field(default_factory=DedupeConfig)


class ChunkingConfig(BaseModel):
    """ChunkingConfig definition."""

    strategy: str = "token"
    chunk_size: int = 800
    chunk_overlap: int = 100


class SearchConfig(BaseModel):
    """SearchConfig definition."""

    top_k_default: int = 10
    score_threshold: float = 0.0


class ProfileConfig(BaseModel):
    """ProfileConfig definition."""

    enabled: bool = True
    vdb: VdbConfig
    embeddings: EmbeddingsConfig
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)


class RbacConfig(BaseModel):
    """RbacConfig definition."""

    enabled: bool = True
    default_deny: bool = True
    roles: dict[str, list[str]] = Field(default_factory=dict)


class GlobalConfig(BaseModel):
    """GlobalConfig definition."""

    server: ServerConfig
    auth: AuthConfig
    storage: StorageConfig
    queue: QueueConfig = Field(default_factory=QueueConfig)
    profiles: dict[str, ProfileConfig]
    rbac: RbacConfig = Field(default_factory=RbacConfig)

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> GlobalConfig:
        """Execute from mapping."""
        return cls.model_validate(value)
