"""Central configuration for Trialibre.

Layered config: code defaults → YAML file → environment variables.
Environment variables use CTM_ prefix with __ for nesting.
Example: CTM_LLM__PROVIDER=anthropic CTM_LLM__API_KEY=sk-...
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProviderType(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"
    OPENAI_COMPAT = "openai_compat"


class EmbeddingProviderType(str, Enum):
    SENTENCE_TRANSFORMER = "sentence_transformer"
    OLLAMA = "ollama"
    MEDCPT = "medcpt"


class DatabaseBackend(str, Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


class PrivacyLevel(str, Enum):
    MAXIMUM = "maximum"  # Delete after match, no logs
    STANDARD = "standard"  # Retain locally, logs enabled
    CUSTOM = "custom"  # User-configured


class DeIdMode(str, Enum):
    AUTO = "auto"  # On for cloud, off for local
    ALWAYS = "always"
    NEVER = "never"


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    provider: LLMProviderType = LLMProviderType.ANTHROPIC
    model: str = "claude-sonnet-4-20250514"
    api_key: str | None = None
    base_url: str | None = None
    max_retries: int = 5
    timeout: float = 120.0
    temperature: float = 0.0
    max_tokens: int = 16384


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""

    provider: EmbeddingProviderType = EmbeddingProviderType.SENTENCE_TRANSFORMER
    model: str = "pritamdeka/PubMedBERT-mnli-snli-scinli-scitail-mednli-stsb"
    device: Literal["cpu", "cuda", "mps", "auto"] = "auto"
    batch_size: int = 32
    max_length: int = 512


class RetrievalConfig(BaseModel):
    """Retrieval pipeline configuration."""

    top_n: int = 2000
    fusion_k: int = 20
    max_keywords: int = 32
    enable_bm25: bool = True
    enable_dense: bool = False  # Optional, off by default for memory
    bm25_title_weight: float = 3.0
    bm25_condition_weight: float = 2.0
    bm25_text_weight: float = 1.0


class MatchingConfig(BaseModel):
    """Matching pipeline configuration."""

    max_patient_tokens: int = 6000
    max_criteria_per_prompt: int = 15  # Batch criteria per LLM call
    append_consent_sentence: bool = False
    consent_sentence: str = (
        "The patient will provide informed consent, "
        "and will comply with the trial protocol without any practical issues."
    )
    concurrency: int = 5  # Concurrent trial evaluations


class RankingConfig(BaseModel):
    """Ranking configuration."""

    matching_weight: float = 0.5
    aggregation_weight: float = 0.5
    normalize_scores: bool = True
    score_range: tuple[float, float] = (0.0, 1.0)
    strong_match_threshold: float = 0.7
    possible_match_threshold: float = 0.4


class PrivacyConfig(BaseModel):
    """Privacy and security configuration."""

    level: PrivacyLevel = PrivacyLevel.MAXIMUM
    deid_mode: DeIdMode = DeIdMode.AUTO
    delete_after_match: bool = True
    retain_match_logs: bool = False
    allow_local_storage: bool = False
    data_retention_days: int | None = None  # None = delete immediately


class DatabaseConfig(BaseModel):
    """Database configuration."""

    backend: DatabaseBackend = DatabaseBackend.SQLITE
    sqlite_path: str = "trialibre.db"
    postgresql_url: str | None = None
    echo: bool = False  # SQL logging


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = True
    path: str = ".trialibre_cache/cache.db"
    ttl_hours: int = 168  # 7 days


class APIConfig(BaseModel):
    """API server configuration."""

    host: str = "127.0.0.1"
    port: int = 0  # 0 = auto-select available port
    cors_origins: list[str] = ["*"]
    serve_frontend: bool = True
    frontend_build_path: str = "../frontend/dist"


class AuditConfig(BaseModel):
    """Audit trail configuration."""

    enabled: bool = True
    crypto_chain: bool = True  # Cryptographic hash chaining
    log_prompts: bool = True  # Log prompt versions


class SandboxConfig(BaseModel):
    """Sandbox mode configuration."""

    enabled: bool = False
    data_path: str = "sandbox"
    show_banner: bool = True


class Settings(BaseSettings):
    """Root settings for Trialibre."""

    model_config = SettingsConfigDict(
        env_prefix="CTM_",
        env_nested_delimiter="__",
        yaml_file="config/settings.yaml",
        yaml_file_encoding="utf-8",
        extra="ignore",
    )

    # Sub-configurations
    llm: LLMConfig = Field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    matching: MatchingConfig = Field(default_factory=MatchingConfig)
    ranking: RankingConfig = Field(default_factory=RankingConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)

    # Global settings
    language: str = "en"
    log_level: str = "INFO"
    data_dir: Path = Path(".trialibre_data")

    @property
    def is_cloud_llm(self) -> bool:
        """Check if the configured LLM sends data externally."""
        return self.llm.provider in (LLMProviderType.ANTHROPIC, LLMProviderType.OPENAI)

    @property
    def should_deid(self) -> bool:
        """Determine if de-identification should be active."""
        if self.privacy.deid_mode == DeIdMode.ALWAYS:
            return True
        if self.privacy.deid_mode == DeIdMode.NEVER:
            return False
        # AUTO: de-ID for cloud providers, skip for local
        return self.is_cloud_llm


def load_settings(config_path: str | None = None) -> Settings:
    """Load settings from YAML + environment variables."""
    if config_path:
        return Settings(_yaml_file=config_path)
    return Settings()
