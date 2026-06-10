"""Evidence ranking and technology recommendation scoring."""
from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any, Dict, Iterable, List, Tuple


HYPE_WORDS = {
    "breakthrough",
    "revolutionary",
    "game-changing",
    "disruptive",
    "magic",
    "guaranteed",
    "ultimate",
}

TECHNOLOGY_CATALOG = {
    # AI/LLM Model Providers
    "OpenAI": {"category": "model provider", "aliases": ["openai", "gpt-4", "gpt-4o", "o3", "o4", "chatgpt"]},
    "Anthropic Claude": {"category": "model provider", "aliases": ["anthropic", "claude", "claude-3", "claude-sonnet"]},
    "Google Gemini": {"category": "model provider", "aliases": ["gemini", "google deepmind", "gemini-pro"]},
    "Meta Llama": {"category": "open model", "aliases": ["llama", "meta ai", "llama-3", "llama-4"]},
    "Mistral": {"category": "open model", "aliases": ["mistral", "mixtral", "mistral-7b"]},
    "Cohere": {"category": "model provider", "aliases": ["cohere", "command r", "command-r"]},
    "Hugging Face": {"category": "model and dataset hub", "aliases": ["hugging face", "huggingface", "transformers"]},
    "Groq": {"category": "model provider", "aliases": ["groq", "groq api"]},
    "Together AI": {"category": "model provider", "aliases": ["together ai", "together.ai"]},
    "Replicate": {"category": "model provider", "aliases": ["replicate"]},
    
    # RAG & AI Application Frameworks
    "LangChain": {"category": "application framework", "aliases": ["langchain"]},
    "LangGraph": {"category": "agent framework", "aliases": ["langgraph", "stateful agent"]},
    "LlamaIndex": {"category": "RAG framework", "aliases": ["llamaindex", "llama index", "gpt index"]},
    "DSPy": {"category": "optimization framework", "aliases": ["dspy", "declarative self-improving"]},
    "Haystack": {"category": "RAG framework", "aliases": ["haystack", "deepset"]},
    "Semantic Kernel": {"category": "AI framework", "aliases": ["semantic kernel", "microsoft semantic kernel"]},
    "AutoGPT": {"category": "agent framework", "aliases": ["autogpt", "auto-gpt"]},
    "CrewAI": {"category": "agent framework", "aliases": ["crewai", "crew ai"]},
    "RAGAS": {"category": "evaluation", "aliases": ["ragas", "rag evaluation"]},
    "LangSmith": {"category": "observability", "aliases": ["langsmith", "tracing"]},
    
    # Vector Databases & Search
    "pgvector": {"category": "vector database", "aliases": ["pgvector", "postgres vector"]},
    "Qdrant": {"category": "vector database", "aliases": ["qdrant"]},
    "Pinecone": {"category": "vector database", "aliases": ["pinecone"]},
    "Weaviate": {"category": "vector database", "aliases": ["weaviate"]},
    "Milvus": {"category": "vector database", "aliases": ["milvus"]},
    "Chroma": {"category": "vector database", "aliases": ["chromadb", "chroma"]},
    "FAISS": {"category": "vector index", "aliases": ["faiss", "facebook ai similarity search"]},
    "Elasticsearch": {"category": "search engine", "aliases": ["elasticsearch", "elastic"]},
    "OpenSearch": {"category": "search engine", "aliases": ["opensearch"]},
    "Typesense": {"category": "search engine", "aliases": ["typesense"]},
    "Algolia": {"category": "search engine", "aliases": ["algolia"]},
    "Meilisearch": {"category": "search engine", "aliases": ["meilisearch"]},
    
    # Frontend Frameworks
    "React": {"category": "frontend framework", "aliases": ["react", "reactjs", "react.js"]},
    "Next.js": {"category": "frontend framework", "aliases": ["next.js", "nextjs", "next"]},
    "Vue": {"category": "frontend framework", "aliases": ["vue", "vue.js", "vuejs", "vue-3"]},
    "Nuxt": {"category": "frontend framework", "aliases": ["nuxt", "nuxt.js", "nuxtjs"]},
    "Angular": {"category": "frontend framework", "aliases": ["angular", "angular-2", "angular-18"]},
    "Svelte": {"category": "frontend framework", "aliases": ["svelte", "sveltekit"]},
    "Solid": {"category": "frontend framework", "aliases": ["solidjs", "solid.js"]},
    "Qwik": {"category": "frontend framework", "aliases": ["qwik", "qwik city"]},
    "Astro": {"category": "frontend framework", "aliases": ["astro", "astro.build"]},
    "Remix": {"category": "frontend framework", "aliases": ["remix", "remix.run"]},
    "Tailwind CSS": {"category": "css framework", "aliases": ["tailwind", "tailwindcss"]},
    "shadcn/ui": {"category": "ui library", "aliases": ["shadcn", "shadcn/ui", "shadcn-ui"]},
    
    # Backend Frameworks
    "FastAPI": {"category": "backend framework", "aliases": ["fastapi"]},
    "Django": {"category": "backend framework", "aliases": ["django", "django rest framework", "drf"]},
    "Flask": {"category": "backend framework", "aliases": ["flask"]},
    "Express": {"category": "backend framework", "aliases": ["express", "express.js", "expressjs"]},
    "NestJS": {"category": "backend framework", "aliases": ["nestjs", "nest.js", "nest"]},
    "Spring Boot": {"category": "backend framework", "aliases": ["spring boot", "spring", "springboot"]},
    "ASP.NET Core": {"category": "backend framework", "aliases": ["asp.net core", "aspnet", "dotnet"]},
    "Go Gin": {"category": "backend framework", "aliases": ["gin", "gin-gonic"]},
    "Actix": {"category": "backend framework", "aliases": ["actix", "actix-web"]},
    "Axum": {"category": "backend framework", "aliases": ["axum", "tokio axum"]},
    "Ruby on Rails": {"category": "backend framework", "aliases": ["rails", "ruby on rails", "ror"]},
    "Laravel": {"category": "backend framework", "aliases": ["laravel"]},
    "Fiber": {"category": "backend framework", "aliases": ["fiber", "gofiber"]},
    
    # Mobile Development
    "React Native": {"category": "mobile framework", "aliases": ["react native", "react-native"]},
    "Flutter": {"category": "mobile framework", "aliases": ["flutter", "dart flutter"]},
    "Swift": {"category": "mobile language", "aliases": ["swift", "swiftui"]},
    "Kotlin": {"category": "mobile language", "aliases": ["kotlin", "kotlin multiplatform"]},
    "Expo": {"category": "mobile framework", "aliases": ["expo", "expo sdk"]},
    "Ionic": {"category": "mobile framework", "aliases": ["ionic", "ionic framework"]},
    "Capacitor": {"category": "mobile framework", "aliases": ["capacitor", "capacitorjs"]},
    
    # Databases
    "PostgreSQL": {"category": "database", "aliases": ["postgresql", "postgres"]},
    "MySQL": {"category": "database", "aliases": ["mysql"]},
    "MongoDB": {"category": "database", "aliases": ["mongodb", "mongo"]},
    "Redis": {"category": "cache and database", "aliases": ["redis", "redis stack"]},
    "SQLite": {"category": "database", "aliases": ["sqlite", "sqlite3"]},
    "Cassandra": {"category": "database", "aliases": ["cassandra", "apache cassandra"]},
    "DynamoDB": {"category": "database", "aliases": ["dynamodb", "amazon dynamodb"]},
    "CockroachDB": {"category": "database", "aliases": ["cockroachdb", "cockroach"]},
    "Supabase": {"category": "database platform", "aliases": ["supabase"]},
    "Firebase": {"category": "database platform", "aliases": ["firebase", "firestore"]},
    "PlanetScale": {"category": "database platform", "aliases": ["planetscale"]},
    "Neon": {"category": "database platform", "aliases": ["neon", "neon serverless"]},
    "TiDB": {"category": "database", "aliases": ["tidb"]},
    "ClickHouse": {"category": "database", "aliases": ["clickhouse"]},
    "TimescaleDB": {"category": "database", "aliases": ["timescaledb", "timescale"]},
    "InfluxDB": {"category": "database", "aliases": ["influxdb"]},
    "Neo4j": {"category": "graph database", "aliases": ["neo4j"]},
    "ArangoDB": {"category": "database", "aliases": ["arangodb"]},
    
    # Cloud Platforms
    "AWS": {"category": "cloud platform", "aliases": ["aws", "amazon web services"]},
    "Azure": {"category": "cloud platform", "aliases": ["azure", "microsoft azure"]},
    "Google Cloud": {"category": "cloud platform", "aliases": ["gcp", "google cloud", "google cloud platform"]},
    "Vercel": {"category": "cloud platform", "aliases": ["vercel"]},
    "Netlify": {"category": "cloud platform", "aliases": ["netlify"]},
    "Cloudflare": {"category": "cloud platform", "aliases": ["cloudflare", "cloudflare workers", "workers"]},
    "Railway": {"category": "cloud platform", "aliases": ["railway", "railway.app"]},
    "Render": {"category": "cloud platform", "aliases": ["render", "render.com"]},
    "Fly.io": {"category": "cloud platform", "aliases": ["fly.io", "flyio"]},
    "DigitalOcean": {"category": "cloud platform", "aliases": ["digitalocean", "digital ocean"]},
    "Heroku": {"category": "cloud platform", "aliases": ["heroku"]},
    
    # Container & Orchestration
    "Docker": {"category": "containerization", "aliases": ["docker", "dockerfile"]},
    "Kubernetes": {"category": "orchestration", "aliases": ["kubernetes", "k8s"]},
    "Podman": {"category": "containerization", "aliases": ["podman"]},
    "Nomad": {"category": "orchestration", "aliases": ["nomad", "hashicorp nomad"]},
    "Docker Swarm": {"category": "orchestration", "aliases": ["docker swarm", "swarm"]},
    "Helm": {"category": "package manager", "aliases": ["helm", "helm charts"]},
    
    # CI/CD & DevOps
    "GitHub Actions": {"category": "ci/cd", "aliases": ["github actions", "gh actions"]},
    "GitLab CI": {"category": "ci/cd", "aliases": ["gitlab ci", "gitlab"]},
    "Jenkins": {"category": "ci/cd", "aliases": ["jenkins"]},
    "CircleCI": {"category": "ci/cd", "aliases": ["circleci", "circle ci"]},
    "Travis CI": {"category": "ci/cd", "aliases": ["travis ci", "travis"]},
    "ArgoCD": {"category": "cd", "aliases": ["argocd", "argo cd"]},
    "Terraform": {"category": "infrastructure as code", "aliases": ["terraform"]},
    "Ansible": {"category": "configuration management", "aliases": ["ansible"]},
    "Pulumi": {"category": "infrastructure as code", "aliases": ["pulumi"]},
    
    # Message Queues & Streaming
    "Kafka": {"category": "message queue", "aliases": ["kafka", "apache kafka"]},
    "RabbitMQ": {"category": "message queue", "aliases": ["rabbitmq", "rabbit mq"]},
    "NATS": {"category": "message queue", "aliases": ["nats", "nats.io"]},
    "Apache Pulsar": {"category": "message queue", "aliases": ["pulsar", "apache pulsar"]},
    "Celery": {"category": "job queue", "aliases": ["celery"]},
    "BullMQ": {"category": "job queue", "aliases": ["bullmq", "bull"]},
    "Temporal": {"category": "workflow engine", "aliases": ["temporal", "temporal.io"]},
    "APScheduler": {"category": "scheduler", "aliases": ["apscheduler"]},
    "Airflow": {"category": "scheduler", "aliases": ["airflow", "apache airflow"]},
    
    # Monitoring & Observability
    "Prometheus": {"category": "monitoring", "aliases": ["prometheus"]},
    "Grafana": {"category": "monitoring", "aliases": ["grafana"]},
    "Datadog": {"category": "monitoring", "aliases": ["datadog"]},
    "New Relic": {"category": "monitoring", "aliases": ["new relic", "newrelic"]},
    "Sentry": {"category": "error tracking", "aliases": ["sentry", "sentry.io"]},
    "Jaeger": {"category": "tracing", "aliases": ["jaeger", "jaeger tracing"]},
    "OpenTelemetry": {"category": "observability", "aliases": ["opentelemetry", "otel"]},
    "Elastic APM": {"category": "monitoring", "aliases": ["elastic apm", "apm"]},
    
    # Testing
    "Jest": {"category": "testing", "aliases": ["jest"]},
    "Pytest": {"category": "testing", "aliases": ["pytest"]},
    "Playwright": {"category": "testing", "aliases": ["playwright"]},
    "Cypress": {"category": "testing", "aliases": ["cypress"]},
    "Selenium": {"category": "testing", "aliases": ["selenium"]},
    "Vitest": {"category": "testing", "aliases": ["vitest"]},
    "Testing Library": {"category": "testing", "aliases": ["testing library", "react testing library"]},
    
    # API & GraphQL
    "GraphQL": {"category": "api", "aliases": ["graphql"]},
    "Apollo": {"category": "graphql", "aliases": ["apollo", "apollo server", "apollo client"]},
    "tRPC": {"category": "api", "aliases": ["trpc"]},
    "gRPC": {"category": "api", "aliases": ["grpc"]},
    "REST": {"category": "api", "aliases": ["rest api", "restful"]},
    "Hasura": {"category": "graphql", "aliases": ["hasura"]},
    "Postman": {"category": "api testing", "aliases": ["postman"]},
    
    # Data Processing & ETL
    "Apache Spark": {"category": "data processing", "aliases": ["spark", "apache spark", "pyspark"]},
    "Pandas": {"category": "data processing", "aliases": ["pandas"]},
    "Polars": {"category": "data processing", "aliases": ["polars"]},
    "DuckDB": {"category": "database", "aliases": ["duckdb"]},
    "Apache Flink": {"category": "data processing", "aliases": ["flink", "apache flink"]},
    "dbt": {"category": "data transformation", "aliases": ["dbt", "data build tool"]},
    "Dagster": {"category": "data orchestration", "aliases": ["dagster"]},
    "Prefect": {"category": "workflow orchestration", "aliases": ["prefect"]},
    
    # Machine Learning & AI Tools
    "PyTorch": {"category": "ml framework", "aliases": ["pytorch", "torch"]},
    "TensorFlow": {"category": "ml framework", "aliases": ["tensorflow"]},
    "Scikit-learn": {"category": "ml library", "aliases": ["scikit-learn", "sklearn"]},
    "XGBoost": {"category": "ml library", "aliases": ["xgboost"]},
    "LightGBM": {"category": "ml library", "aliases": ["lightgbm"]},
    "Keras": {"category": "ml framework", "aliases": ["keras"]},
    "JAX": {"category": "ml framework", "aliases": ["jax", "google jax"]},
    "MLflow": {"category": "ml ops", "aliases": ["mlflow"]},
    "Weights & Biases": {"category": "ml ops", "aliases": ["wandb", "weights and biases"]},
    "Ray": {"category": "distributed computing", "aliases": ["ray", "ray.io"]},
    
    # Web3 & Blockchain
    "Ethereum": {"category": "blockchain", "aliases": ["ethereum", "eth"]},
    "Solidity": {"category": "smart contracts", "aliases": ["solidity"]},
    "Hardhat": {"category": "blockchain dev", "aliases": ["hardhat"]},
    "Foundry": {"category": "blockchain dev", "aliases": ["foundry"]},
    "ethers.js": {"category": "web3 library", "aliases": ["ethers", "ethers.js"]},
    "web3.js": {"category": "web3 library", "aliases": ["web3.js", "web3js"]},
    "IPFS": {"category": "storage", "aliases": ["ipfs", "interplanetary file system"]},
    
    # Game Development
    "Unity": {"category": "game engine", "aliases": ["unity", "unity3d"]},
    "Unreal Engine": {"category": "game engine", "aliases": ["unreal", "unreal engine", "ue5"]},
    "Godot": {"category": "game engine", "aliases": ["godot", "godot engine"]},
    
    # Real-time & WebSockets
    "Socket.io": {"category": "real-time", "aliases": ["socket.io", "socketio"]},
    "WebSockets": {"category": "real-time", "aliases": ["websocket", "websockets"]},
    "Pusher": {"category": "real-time", "aliases": ["pusher"]},
    "Ably": {"category": "real-time", "aliases": ["ably"]},
    
    # Authentication & Security
    "Auth0": {"category": "authentication", "aliases": ["auth0"]},
    "Clerk": {"category": "authentication", "aliases": ["clerk"]},
    "NextAuth": {"category": "authentication", "aliases": ["nextauth", "next-auth"]},
    "Keycloak": {"category": "authentication", "aliases": ["keycloak"]},
    "OAuth": {"category": "authentication", "aliases": ["oauth", "oauth2"]},
    
    # Content Management
    "Strapi": {"category": "cms", "aliases": ["strapi"]},
    "Contentful": {"category": "cms", "aliases": ["contentful"]},
    "Sanity": {"category": "cms", "aliases": ["sanity", "sanity.io"]},
    "WordPress": {"category": "cms", "aliases": ["wordpress"]},
    
    # Programming Languages
    "Python": {"category": "language", "aliases": ["python", "python3"]},
    "TypeScript": {"category": "language", "aliases": ["typescript", "ts"]},
    "JavaScript": {"category": "language", "aliases": ["javascript", "js"]},
    "Rust": {"category": "language", "aliases": ["rust", "rustlang"]},
    "Go": {"category": "language", "aliases": ["go", "golang"]},
    "Java": {"category": "language", "aliases": ["java", "openjdk"]},
    "C#": {"category": "language", "aliases": ["c#", "csharp"]},
    "Ruby": {"category": "language", "aliases": ["ruby"]},
    "PHP": {"category": "language", "aliases": ["php"]},
    "Elixir": {"category": "language", "aliases": ["elixir", "phoenix"]},
    "Zig": {"category": "language", "aliases": ["zig", "ziglang"]},
}


def rank_source_documents(
    documents: List[Dict[str, Any]],
    query_terms: List[str],
    now: datetime | None = None,
) -> List[Dict[str, Any]]:
    """Apply the requested weighted evidence formula to source documents."""
    ranked = []
    for document in documents:
        scored = dict(document)
        breakdown = score_source_document(scored, query_terms=query_terms, now=now)
        scored["final_score"] = breakdown["final_score"]
        scored["scoring_breakdown"] = breakdown
        ranked.append(scored)
    ranked.sort(key=lambda item: item.get("final_score", 0), reverse=True)
    return ranked


def score_source_document(
    document: Dict[str, Any],
    query_terms: List[str],
    now: datetime | None = None,
) -> Dict[str, float]:
    """Score one source using relevance, authority, recency, adoption, and penalties."""
    text = _document_text(document)
    metadata = document.get("metadata") or {}

    semantic_relevance = keyword_similarity(query_terms, text)
    source_credibility = _normalize_credibility(document)
    recency_score = _recency_score(document.get("publication_date"), now=now)
    adoption_signal = _adoption_signal(metadata)
    citation_count = _citation_score(metadata)
    implementation_availability = _implementation_availability(document, text)
    conflict_penalty = _conflict_penalty(document)
    hype_penalty = _hype_penalty(document, text)

    final_score = (
        0.30 * semantic_relevance
        + 0.20 * source_credibility
        + 0.15 * recency_score
        + 0.15 * adoption_signal
        + 0.10 * citation_count
        + 0.10 * implementation_availability
        - conflict_penalty
        - hype_penalty
    )

    return {
        "semantic_relevance": round(semantic_relevance, 4),
        "source_credibility": round(source_credibility, 4),
        "recency_score": round(recency_score, 4),
        "adoption_signal": round(adoption_signal, 4),
        "citation_count": round(citation_count, 4),
        "implementation_availability": round(implementation_availability, 4),
        "conflict_penalty": round(conflict_penalty, 4),
        "hype_penalty": round(hype_penalty, 4),
        "final_score": round(max(0.0, min(final_score, 1.0)), 4),
    }


def build_technology_recommendations(
    documents: List[Dict[str, Any]],
    brief_insights: Dict[str, Any],
    query_terms: List[str],
    max_recommendations: int = 8,
) -> List[Dict[str, Any]]:
    """Convert ranked, cited source evidence into technology recommendations."""
    ranked_docs = rank_source_documents(documents, query_terms=query_terms)
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for document in ranked_docs:
        for tech_name in find_technologies(_document_text(document)):
            grouped[tech_name].append(document)

    recommendations: List[Dict[str, Any]] = []
    for tech_name, sources in grouped.items():
        if not sources:
            continue
        top_sources = sources[:5]
        average_score = sum(source.get("final_score", 0) for source in top_sources) / len(top_sources)
        source_count_score = min(len(sources) / 5, 1.0)
        evidence_score = min(1.0, (average_score * 0.8) + (source_count_score * 0.2))
        category = TECHNOLOGY_CATALOG.get(tech_name, {}).get("category", "technology")
        radar_stage = radar_stage_for_score(evidence_score, source_count=len(sources))
        citations = [_citation_from_document(source) for source in top_sources if source.get("url")]
        if not citations:
            continue

        recommendation = {
            "technology_name": tech_name,
            "category": category,
            "description": _technology_description(tech_name, category, brief_insights),
            "why_relevant": _why_relevant(tech_name, category, brief_insights, top_sources),
            "confidence_score": round(evidence_score, 3),
            "implementation_difficulty": _implementation_difficulty(tech_name, category),
            "alternatives": _alternatives_for(tech_name, category),
            "risks_tradeoffs": _risks_for(tech_name, category),
            "suggested_architecture": _suggested_architecture(tech_name, category, brief_insights),
            "next_steps": _next_steps_for(tech_name, category),
            "citations": citations,
            "source_count": len(sources),
            "evidence_score": round(evidence_score, 3),
            "recency_score": round(
                sum(source.get("scoring_breakdown", {}).get("recency_score", 0.3) for source in top_sources)
                / len(top_sources),
                3,
            ),
            "adoption_signal": round(
                sum(source.get("scoring_breakdown", {}).get("adoption_signal", 0) for source in top_sources)
                / len(top_sources),
                3,
            ),
            "radar_stage": radar_stage,
            "scoring_breakdown": _merge_breakdowns(top_sources),
        }
        recommendations.append(recommendation)

    recommendations.sort(key=lambda item: (item["confidence_score"], item["source_count"]), reverse=True)
    return recommendations[:max_recommendations]


def build_technology_radar(recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build radar entries from recommendations."""
    return [
        {
            "name": rec["technology_name"],
            "category": rec.get("category", "technology"),
            "description": rec.get("description", ""),
            "evidence_score": rec.get("evidence_score", rec.get("confidence_score", 0)),
            "recency_score": rec.get("recency_score", 0),
            "adoption_signal": rec.get("adoption_signal", 0),
            "source_count": rec.get("source_count", 0),
            "radar_stage": rec.get("radar_stage", radar_stage_for_score(rec.get("confidence_score", 0), rec.get("source_count", 0))),
            "sources": rec.get("citations", []),
        }
        for rec in recommendations
    ]


def find_technologies(text: str) -> List[str]:
    """Find known technology mentions in source text."""
    text_lower = text.lower()
    found = []
    for tech_name, details in TECHNOLOGY_CATALOG.items():
        aliases = details.get("aliases", [])
        if any(re.search(rf"(?<![A-Za-z0-9]){re.escape(alias.lower())}(?![A-Za-z0-9])", text_lower) for alias in aliases):
            found.append(tech_name)
    return found


def keyword_similarity(query_terms: Iterable[str], text: str) -> float:
    """Lightweight lexical semantic relevance fallback."""
    terms = list(query_terms)
    text_lower = text.lower()
    query_tokens = set()
    phrase_hits = 0
    for term in terms:
        term_lower = str(term).lower().strip()
        if not term_lower:
            continue
        if term_lower in text_lower:
            phrase_hits += 1
        query_tokens.update(token for token in re.findall(r"[a-z0-9][a-z0-9+-]{2,}", term_lower) if token not in STOPWORDS)

    if not query_tokens:
        return 0.0
    text_tokens = set(token for token in re.findall(r"[a-z0-9][a-z0-9+-]{2,}", text_lower) if token not in STOPWORDS)
    overlap = len(query_tokens & text_tokens) / len(query_tokens)
    phrase_score = min(phrase_hits / max(len(terms), 1), 1.0)
    return min((0.7 * overlap) + (0.3 * phrase_score), 1.0)


def radar_stage_for_score(score: float, source_count: int) -> str:
    if score >= 0.74 and source_count >= 2:
        return "Adopt Now"
    if score >= 0.58:
        return "Trial"
    if score >= 0.38:
        return "Assess"
    return "Hold"


def _document_text(document: Dict[str, Any]) -> str:
    return " ".join(
        str(part or "")
        for part in [
            document.get("title"),
            document.get("content"),
            document.get("abstract"),
            document.get("parsed_text"),
            document.get("metadata"),
        ]
    )


def _normalize_credibility(document: Dict[str, Any]) -> float:
    score = document.get("credibility_score")
    if score is None:
        tier = str(document.get("tier", "")).lower()
        score = {"tier_1": 90, "tier_2": 70, "tier_3": 45}.get(tier, 40)
    try:
        numeric = float(score)
    except (TypeError, ValueError):
        numeric = 40
    if numeric <= 10:
        numeric *= 10
    return max(0.0, min(numeric / 100.0, 1.0))


def _recency_score(value: Any, now: datetime | None = None) -> float:
    parsed = _parse_date(value)
    if parsed is None:
        return 0.35
    reference = now or datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    days_old = max((reference - parsed).days, 0)
    return math.exp(-days_old / 365.0)


def _parse_date(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    for candidate in (text, text[:10], text[:7], text[:4]):
        try:
            if len(candidate) == 10:
                return datetime.strptime(candidate, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if len(candidate) == 7:
                return datetime.strptime(candidate, "%Y-%m").replace(tzinfo=timezone.utc)
            if len(candidate) == 4:
                return datetime.strptime(candidate, "%Y").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _adoption_signal(metadata: Dict[str, Any]) -> float:
    numeric_fields = [
        ("stars", 20_000),
        ("forks", 4_000),
        ("downloads", 1_000_000),
        ("likes", 10_000),
        ("upvotes", 1_000),
        ("points", 1_000),
        ("citation_count", 1_000),
        ("influential_citation_count", 200),
    ]
    signals = []
    for field, cap in numeric_fields:
        value = metadata.get(field)
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        signals.append(min(math.log10(numeric + 1) / math.log10(cap + 1), 1.0))
    return max(signals) if signals else 0.25


def _citation_score(metadata: Dict[str, Any]) -> float:
    value = metadata.get("citation_count") or metadata.get("cited_by_count") or metadata.get("influential_citation_count")
    try:
        numeric = float(value or 0)
    except (TypeError, ValueError):
        numeric = 0
    return min(math.log10(numeric + 1) / math.log10(1001), 1.0)


def _implementation_availability(document: Dict[str, Any], text: str) -> float:
    source_type = str(document.get("source_type", "")).lower()
    if "github" in source_type:
        return 1.0
    text_lower = text.lower()
    signals = ["github", "code", "implementation", "api", "library", "sdk", "benchmark", "tutorial", "docs"]
    hits = sum(1 for signal in signals if signal in text_lower)
    return min(hits / 4, 1.0)


def _conflict_penalty(document: Dict[str, Any]) -> float:
    if document.get("has_conflict"):
        return 0.15
    metadata = document.get("metadata") or {}
    return 0.08 if metadata.get("conflicting_sources") else 0.0


def _hype_penalty(document: Dict[str, Any], text: str) -> float:
    text_lower = text.lower()
    hype_hits = sum(1 for word in HYPE_WORDS if word in text_lower)
    if hype_hits == 0:
        return 0.0
    metadata = document.get("metadata") or {}
    has_support = (metadata.get("citation_count") or 0) or (metadata.get("stars") or 0) or "github" in text_lower
    return 0.04 if has_support else min(0.2, 0.06 * hype_hits)


def _citation_from_document(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": document.get("title") or "Untitled source",
        "url": document.get("url"),
        "source_type": document.get("source_type", "unknown"),
        "publication_date": str(document.get("publication_date") or ""),
        "credibility_score": document.get("credibility_score", 0),
        "evidence_score": round(document.get("final_score", 0), 3),
    }


def _technology_description(tech_name: str, category: str, brief_insights: Dict[str, Any]) -> str:
    domain = brief_insights.get("domain", "the project")
    return f"{tech_name} is a {category} candidate for {domain} requirements."


def _why_relevant(
    tech_name: str,
    category: str,
    brief_insights: Dict[str, Any],
    sources: List[Dict[str, Any]],
) -> str:
    topic = ", ".join((brief_insights.get("key_topics") or [])[:3]) or "the extracted project topics"
    source_titles = "; ".join((source.get("title") or "source")[:90] for source in sources[:2])
    return (
        f"{tech_name} matches {topic} and is supported by {len(sources)} cited source(s)"
        f" including {source_titles}."
    )


def _implementation_difficulty(tech_name: str, category: str) -> str:
    category_lower = category.lower()
    if category_lower in {"model provider", "frontend framework", "backend framework", "cache and queue"}:
        return "Low"
    if "vector" in category_lower or "rag" in category_lower or "observability" in category_lower:
        return "Medium"
    if "agent" in category_lower or "optimization" in category_lower:
        return "High"
    if tech_name in {"Kubernetes", "Airflow"}:
        return "High"
    return "Medium"


def _alternatives_for(tech_name: str, category: str) -> List[str]:
    peers = [
        name
        for name, details in TECHNOLOGY_CATALOG.items()
        if details.get("category") == category and name != tech_name
    ]
    return peers[:4] or ["Re-evaluate after collecting more evidence"]


def _risks_for(tech_name: str, category: str) -> List[str]:
    category_lower = category.lower()
    risks = []
    if "model" in category_lower:
        risks.extend(["Provider lock-in", "Token cost volatility", "Latency variance"])
    if "vector" in category_lower:
        risks.extend(["Index tuning complexity", "Recall degradation without evaluation"])
    if "agent" in category_lower:
        risks.extend(["Workflow unpredictability", "Requires strong tool permission boundaries"])
    if "framework" in category_lower:
        risks.extend(["Abstraction churn", "Version compatibility"])
    return risks[:4] or ["Evidence should be rechecked before production rollout"]


def _suggested_architecture(tech_name: str, category: str, brief_insights: Dict[str, Any]) -> str:
    category_lower = category.lower()
    if "vector" in category_lower:
        return f"Use {tech_name} behind a retrieval service with hybrid keyword/vector search and citation logging."
    if "model" in category_lower:
        return f"Use {tech_name} through a provider abstraction with eval gates, caching, and fallback routing."
    if "agent" in category_lower:
        return f"Use {tech_name} only for bounded workflows with explicit tools, audit logs, and retry limits."
    if "evaluation" in category_lower or "observability" in category_lower:
        return f"Use {tech_name} in the CI and runtime feedback loop for regression and quality tracking."
    return f"Introduce {tech_name} as a replaceable module with configuration-driven rollout."


def _next_steps_for(tech_name: str, category: str) -> List[str]:
    return [
        f"Create a small proof of concept for {tech_name}",
        "Define success metrics before rollout",
        "Compare against at least one cited alternative",
        "Add operational logging and rollback criteria",
    ]


def _merge_breakdowns(sources: List[Dict[str, Any]]) -> Dict[str, float]:
    keys = [
        "semantic_relevance",
        "source_credibility",
        "recency_score",
        "adoption_signal",
        "citation_count",
        "implementation_availability",
        "conflict_penalty",
        "hype_penalty",
        "final_score",
    ]
    merged = {}
    for key in keys:
        values = [source.get("scoring_breakdown", {}).get(key, 0) for source in sources]
        merged[key] = round(sum(values) / len(values), 4) if values else 0
    return merged


STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "into",
    "using",
    "use",
    "will",
    "should",
    "must",
    "need",
    "needs",
    "system",
    "project",
    "user",
    "users",
}
