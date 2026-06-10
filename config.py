"""
Configuration management for RAG Research Intelligence System
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Literal, Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = "RAG Research Intelligence System"
    environment: Literal["development", "staging", "production"] = "production"
    debug: bool = False
    log_level: str = "INFO"
    allowed_origins: str = "*"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, validation_alias="PORT")
    api_workers: int = 4
    
    # Upstash Redis (Optional)
    upstash_redis_url: Optional[str] = None
    upstash_redis_token: Optional[str] = None
    
    # Database (PostgreSQL)
    database_type: Literal["postgresql", "sqlite"] = "postgresql"
    database_host: Optional[str] = None
    database_name: Optional[str] = None
    database_username: Optional[str] = None
    database_password: Optional[str] = None
    database_port: int = 5432
    database_ssl_mode: str = "prefer"
    # Full connection string (alternative to individual params)
    database_connection_string: Optional[str] = None
    
    # LLM Providers
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # LLM Configuration
    llm_provider: Literal["openai", "anthropic"] = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4000
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    
    # Object Storage
    storage_type: Literal["s3", "local", "minio"] = "local"
    storage_path: str = "./storage"  # For local storage
    # AWS S3 (optional)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "rag-research-documents"
    
    # Ingestion
    ingestion_schedule_cron: str = "0 0 * * 0"
    max_document_size_mb: int = 50
    allowed_file_types: str = "pdf,html,txt,md,docx"
    parse_timeout_seconds: int = 300
    max_brief_upload_size_mb: int = 20
    
    # Claim Extraction
    claim_extraction_model: str = "gpt-4o-mini"
    claim_extraction_temperature: float = 0.0
    claim_extraction_max_retries: int = 3
    min_claim_confidence: float = 0.6
    human_validation_required: bool = True
    human_validation_sample_rate: float = 0.1
    
    # Source Credibility
    tier_1_boost: int = 10
    tier_2_boost: int = 5
    tier_3_boost: int = 0
    min_citation_count: int = 10
    min_author_h_index: int = 20

    # Multi-source data ingestion API keys
    semantic_scholar_api_key: Optional[str] = None
    openalex_contact_email: str = "research@example.com"
    gnews_api_key: Optional[str] = None
    newsapi_key: Optional[str] = None
    github_token: Optional[str] = None
    apify_api_token: Optional[str] = None
    huggingface_token: Optional[str] = None
    aminer_api_key: Optional[str] = None
    
    # Research-grade news APIs
    mediacloud_api_key: Optional[str] = None
    guardian_api_key: Optional[str] = None
    nytimes_api_key: Optional[str] = None
    
    # Web search and discovery
    exa_api_key: Optional[str] = None

    # Multi-source data ingestion configuration
    max_papers_per_source: int = 50
    max_news_articles_per_source: int = 100
    max_github_repos: int = 30
    fetch_interval_hours: int = 6
    research_fetch_hour: int = 2
    developer_fetch_hour: int = 3
    min_publication_year: int = 2022
    news_lookback_days: int = 30
    apify_timeout_secs: int = 300
    apify_max_requests_per_crawl: int = 100
    rss_feeds: List[str] = Field(
        default_factory=lambda: [
            "https://huggingface.co/blog/feed.xml",
            "https://openai.com/blog/rss.xml",
            "https://www.anthropic.com/news/rss.xml",
            "https://blog.langchain.dev/rss/",
            "https://www.pinecone.io/blog/rss.xml",
            "https://weaviate.io/blog/rss.xml",
            "https://paperswithcode.com/latest/rss",
        ]
    )
    github_topics: List[str] = Field(
        default_factory=lambda: [
            "rag",
            "retrieval-augmented-generation",
            "vector-search",
            "llm",
            "embeddings",
            "semantic-search",
        ]
    )
    github_awesome_lists: List[str] = Field(
        default_factory=lambda: [
            "Hannibal046/Awesome-LLM",
            "kyrolabs/awesome-langchain",
            "e2b-dev/awesome-ai-agents",
            "eugeneyan/applied-ml",
            "steven2358/awesome-generative-ai",
        ]
    )
    papers_with_code_topics: List[str] = Field(
        default_factory=lambda: [
            "natural-language-processing",
            "computer-vision",
            "methodology",
            "miscellaneous",
        ]
    )
    news_keywords: List[str] = Field(
        default_factory=lambda: [
            "RAG",
            "retrieval augmented generation",
            "vector database",
            "LLM",
            "large language model",
            "embeddings",
        ]
    )

    # Daily intelligence email
    daily_intelligence_enabled: bool = False
    daily_intelligence_send_hour: int = 8
    daily_intelligence_send_minute: int = 0
    daily_intelligence_timezone: str = "UTC"
    daily_intelligence_topics: List[str] = Field(
        default_factory=lambda: [
            "AI",
            "LLM",
            "RAG",
            "agentic AI",
            "automation",
            "developer tools",
            "AI security",
        ]
    )

    # Email delivery providers. Secrets are read only from environment variables.
    email_provider: Literal["smtp", "sendgrid", "resend", "disabled"] = "disabled"
    email_from: str = "research-intelligence@example.com"
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    sendgrid_api_key: Optional[str] = None
    resend_api_key: Optional[str] = None
    
    # Retrieval
    default_top_k: int = 20
    rerank_top_k: int = 10
    vector_search_weight: float = 0.7
    keyword_search_weight: float = 0.3
    recency_decay_days: int = 180
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    
    # Security
    secret_key: str = "change-this-in-production"
    allowed_origins: str = "*"  # Configure in production with specific domains
    
    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse comma-separated origins into list"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    @property
    def allowed_file_types_list(self) -> list[str]:
        return [ft.strip() for ft in self.allowed_file_types.split(",")]

    @field_validator("debug", mode="before")
    @classmethod
    def coerce_debug(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod", "0", "false", "no", "off"}:
                return False
            if normalized in {"development", "dev", "1", "true", "yes", "on"}:
                return True
        return value


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Source tier definitions
SOURCE_TIERS = {
    "tier_1": {
        "name": "High Authority",
        "boost": 10,
        "sources": [
            "arxiv.org",
            "semanticscholar.org",
            "openalex.org",
            "openreview.net",
            "proceedings.neurips.cc",
            "aclanthology.org",
            "jmlr.org",
            "openai.com/research",
            "openai.com/blog",
            "deepmind.google",
            "anthropic.com/research",
            "anthropic.com/news",
            "research.google",
            "ai.meta.com/research",
            "microsoft.com/research",
            "research.ibm.com",
        ]
    },
    "tier_2": {
        "name": "Industry Validated",
        "boost": 5,
        "sources": [
            "huggingface.co",
            "github.com",
            "paperswithcode.com",
            "gradientscience.org",
            "techcrunch.com",
            "theverge.com",
            "arstechnica.com",
            "wired.com",
            "technologyreview.com",
            "venturebeat.com",
            "blog.langchain.dev",
            "docs.llamaindex.ai",
            "pinecone.io",
            "weaviate.io",
            "qdrant.tech",
            "towardsdatascience.com",
            "machinelearningmastery.com",
        ]
    },
    "tier_3": {
        "name": "Monitor, Lower Weight",
        "boost": 0,
        "sources": [
            "news.ycombinator.com",
            "reddit.com",
            "medium.com",
            "dev.to",
            "hackernoon.com",
        ]
    }
}

# Excluded sources
EXCLUDED_SOURCES = [
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "pinterest.com",
    "quora.com",
    "twitter.com",
    "x.com",
]
