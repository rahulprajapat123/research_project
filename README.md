# Universal Research Intelligence System

A dynamic, continuously updating intelligence system that ingests high-quality research from **any domain**, structures knowledge into decision-grade insights, and produces context-aware, research-backed recommendations for applied system design.

🌍 **Works for ANY project domain** - AI/ML, Healthcare, Finance, Social Media, Climate Tech, and more!

## 🎯 What This System Does

Given **any project brief** (RAG systems, healthcare AI, social listening, fintech, etc.), this system:

1. **Extracts key topics** from your brief using LLM analysis
2. **Searches 20+ academic sources** for relevant research papers
3. **Generates recommendations** backed by real citations
4. **Answers critical questions:**
   - **"What proven techniques should we apply for this exact scenario?"**
   - **"What does recent research suggest we should avoid?"**
   - **"What implementations already exist?"**

✨ **Domain-Agnostic**: Works for RAG systems, social media analytics, healthcare AI, climate modeling, fraud detection, and any technical project.

All outputs are **cited**, **contextual**, and **actionable**.

## 🌟 Key Features

- **20 Data Sources**: Comprehensive ingestion from academic papers (arXiv, Semantic Scholar, OpenAlex, Hugging Face Papers, Papers with Code, Aminer, **Exa.ai**), industry blogs (via RSS), news sources (Guardian, NYTimes, GDELT), and developer platforms (GitHub repos, Awesome Lists, Hacker News)
- **Domain-Agnostic Intelligence**: Works for ANY technical domain - just configure your research topics
- **Automated Knowledge Extraction**: LLM-powered extraction with evidence linking and confidence scoring
- **Credibility Scoring**: 3-tier source classification with citation-based scoring
- **Human-in-the-Loop Validation**: Configurable validation queue for claim verification  
- **Hybrid Search**: Vector + keyword retrieval with recency-weighted re-ranking
- **Research-Backed Recommendations**: Context-aware suggestions with full citations
- **Project Brief Upload**: Upload PDF, TXT, MD, or DOCX briefs and get citation-backed recommendations
- **Daily Intelligence Email**: Automated digest with source links, impact scores, and recommended actions
- **Technology Radar Dashboard**: Evidence-based Adopt/Trial/Assess/Hold views

📚 **[View Complete Data Sources Documentation](DATA_SOURCES.md)** - Detailed guide to all 20 integrated sources

---

## 🎨 Domain Examples

### Example 1: RAG Systems (Default)
```env
RESEARCH_TOPICS=retrieval augmented generation,vector search,semantic search,embedding models
```
**System finds:** Papers on chunking strategies, vector databases, embedding techniques

### Example 2: Healthcare AI  
```env
RESEARCH_TOPICS=clinical decision support,EHR analysis,medical NLP,patient outcome prediction
```
**System finds:** Papers on clinical ML, medical record analysis, healthcare AI

### Example 3: Social Listening
```env
RESEARCH_TOPICS=sentiment analysis,social media monitoring,multilingual NLP,brand perception
```
**System finds:** Papers on social computing, sentiment classification, online behavior analysis

### Example 4: Climate Tech
```env
RESEARCH_TOPICS=satellite imagery analysis,crop yield prediction,climate modeling,remote sensing
```
**System finds:** Papers on agricultural AI, climate forecasting, computer vision for Earth observation

### Example 5: Fraud Detection
```env
RESEARCH_TOPICS=anomaly detection,transaction monitoring,behavioral analysis,financial ML
```
**System finds:** Papers on fraud detection algorithms, pattern recognition, financial security

**To change domains:** Update `RESEARCH_TOPICS` in your `.env` file!

---

## Research + Market Intelligence Dashboard

The main dashboard is served from `/` and includes:

- Overview: source totals, ingestion counts, latest papers, latest news, system health, and email status.
- Upload Brief: drag-and-drop brief upload, parsing status, extracted topics, cited recommendations, and Markdown/PDF export.
- Research Feed: filterable source feed from the existing research intelligence database.
- Technology Radar: technology matrix grouped into Adopt Now, Trial, Assess, and Hold.
- Daily Intelligence: team email settings, report preview, Send Now, and delivery history.
- Source Management: API key status, fetch logs, and manual latest-source fetch.

New API routes:

```text
POST /api/v1/briefs/upload
GET  /api/v1/briefs/{brief_id}
POST /api/v1/briefs/{brief_id}/analyze
GET  /api/v1/briefs/{brief_id}/recommendations
GET  /api/v1/technology-radar
GET  /api/v1/intelligence/daily
POST /api/v1/intelligence/send-now
GET  /api/v1/intelligence/email-history
POST /api/v1/settings/team-email
GET  /api/v1/settings/team-email
POST /api/v1/sources/fetch-latest
GET  /api/v1/dashboard/overview
```

Run `database/schema.sql` against Postgres to create the added tables for uploaded briefs, extracted topics, brief recommendations, technologies, daily reports, sent email logs, team email settings, and source fetch logs. If Postgres is unavailable, the new dashboard features fall back to `STORAGE_PATH/intelligence_store.json` so local development still works.

### Brief Intelligence

The upload flow validates extension and size, sanitizes parsed text, extracts domain/goals/constraints/users/stack/risks/topics, fetches relevant evidence from existing sources and live source connectors, then ranks recommendations with:

```text
final_score =
0.30 * semantic_relevance +
0.20 * source_credibility +
0.15 * recency_score +
0.15 * adoption_signal +
0.10 * citation_count +
0.10 * implementation_availability -
conflict_penalty -
hype_penalty
```

Recommendations are emitted only when they have source citations.

### Daily Email Configuration

Set these environment variables as needed:

```env
DAILY_INTELLIGENCE_ENABLED=false
DAILY_INTELLIGENCE_SEND_HOUR=8
DAILY_INTELLIGENCE_SEND_MINUTE=0
DAILY_INTELLIGENCE_TIMEZONE=UTC

EMAIL_PROVIDER=disabled # disabled, smtp, sendgrid, resend
EMAIL_FROM=research-intelligence@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_smtp_username
SMTP_PASSWORD=your_smtp_app_password
SMTP_USE_TLS=true
SENDGRID_API_KEY=your_sendgrid_api_key
RESEND_API_KEY=your_resend_api_key
```

Provider secrets stay server-side and are never exposed to the frontend. The dashboard stores only team email settings such as recipient, send time, timezone, topics, enabled flag, and provider selection.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Ingestion Layer (n8n orchestrated)                         │
│  - Fetch from whitelisted sources (arXiv, blogs, etc.)      │
│  - Download PDFs/HTML → Store in S3/Blob                    │
│  - POST to /api/v1/ingest                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Normalization Layer (The Critical 60%)                     │
│  - Parse documents (PDF/HTML → text)                        │
│  - LLM-based claim extraction (structured prompts)          │
│  - Evidence linking & confidence scoring                    │
│  - Human-in-the-loop validation (100% initially, then 10%)  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Knowledge Store (Postgres + pgvector)                      │
│  - Structured claims with embeddings                        │
│  - Source credibility tracking                              │
│  - Conflict detection & resolution                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Recommendation Engine                                       │
│  - Hybrid vector + keyword retrieval                        │
│  - Re-rank: credibility × applicability × recency           │
│  - LLM generates recommendations with citations             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Azure Database** (PostgreSQL, SQL Database, or Cosmos DB)
- **Upstash Redis account**
- **OpenAI/Anthropic/Azure OpenAI API key**
- **Azure account** (for Blob Storage)

### 1. Clone and Setup Environment

```bash
cd "c:\Users\praja\Desktop\research agent brief"

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy example env file
copy .env.example .env

# Edit .env with your credentials
notepad .env
```

**Required variables:**
```ini
# Azure Database (PostgreSQL/SQL/Cosmos)
AZURE_DB_CONNECTION_STRING=postgresql://username:password@your-server.postgres.database.azure.com:5432/your-database?sslmode=require
# OR use individual parameters:
AZURE_DB_SERVER=your-server.postgres.database.azure.com
AZURE_DB_NAME=your-database
AZURE_DB_USERNAME=your-username
AZURE_DB_PASSWORD=your-password

# Upstash Redis
UPSTASH_REDIS_URL=https://your-redis.upstash.io
UPSTASH_REDIS_TOKEN=your-token

# LLM Provider (choose one)
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...
# OR
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=gpt-4

# Storage (Azure Blob Storage)
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=your-account;AccountKey=your-key;EndpointSuffix=core.windows.net
AZURE_STORAGE_CONTAINER_NAME=rag-research-documents

# Data Source API Keys (Optional - system will skip sources without keys)
SEMANTIC_SCHOLAR_API_KEY=your_key              # Optional: Higher rate limits
HUGGINGFACE_TOKEN=hf_your_token                # Optional: Access HF papers/datasets  
AMINER_API_KEY=your_aminer_key                 # Required for Aminer source
GITHUB_TOKEN=ghp_your_token                    # Optional: 60/hr → 5000/hr rate limit
GNEWS_API_KEY=your_gnews_key                   # Required for GNews
NEWSAPI_KEY=your_newsapi_key                   # Required for NewsAPI
APIFY_API_TOKEN=your_apify_token               # Optional: For Apify scrapers
OPENALEX_CONTACT_EMAIL=you@example.com         # Required: Polite API usage
```

### 3. Initialize Database

```bash
# For Azure PostgreSQL, enable pgvector extension:
# Azure Portal → Your PostgreSQL Server → Extensions → Enable "vector"

# Run schema setup
python -c "from database.connection import execute_schema_file; execute_schema_file('database/schema.sql')"
```

### 4. Run the API

```bash
# Development mode (with auto-reload)
python main.py

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at: **http://localhost:8000**

API Documentation: **http://localhost:8000/docs**

---

## 📡 API Usage

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### Ingest a Document

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://arxiv.org/abs/2401.12345",
    "title": "Advanced RAG Techniques",
    "authors": ["John Doe"],
    "publication_date": "2024-01-15",
    "source_type": "arxiv",
    "citation_count": 45
  }'
```

### Get Recommendations

```bash
curl -X POST http://localhost:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "Customer Support RAG",
    "use_case": "customer_support",
    "data_characteristics": {
      "document_types": ["pdf", "html"],
      "avg_document_length": 2000,
      "domain": "technical_documentation"
    },
    "constraints": {
      "latency_requirements": "< 2 seconds",
      "scale": "100k documents"
    },
    "rag_components_of_interest": ["chunking", "retrieval", "reranking"]
  }'
```

### View Validation Queue

```bash
curl http://localhost:8000/api/v1/validation/queue?limit=10
```

---

## 🔧 n8n Integration Setup

### Install n8n

```bash
# Install n8n globally
npm install n8n -g

# Or use Docker
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

### Import Workflow

1. Access n8n at **http://localhost:5678**
2. Create new workflow
3. Import from file: `n8n_workflows/ingestion_pipeline.json`
4. Configure webhook URL in `.env`: `N8N_WEBHOOK_URL=http://localhost:5678/webhook/ingest`

### Workflow Features

- **Scheduled Ingestion**: Cron trigger for weekly/daily runs
- **RSS/Atom Feed Monitoring**: Auto-fetch new arXiv papers, blog posts
- **Human Review Queue**: Sends Slack notifications for validation
- **Error Handling**: Routes failed documents to manual review

---

## 📊 Database Schema

### Core Tables

- **`sources`**: Research documents with credibility scoring
- **`claims`**: Structured knowledge units with embeddings
- **`validation_queue`**: Human-in-the-loop review queue
- **`recommendation_logs`**: Track what was recommended and user feedback

### Vector Search

Uses **pgvector** with HNSW index for fast similarity search:
```sql
CREATE INDEX idx_claims_embedding ON claims 
USING hnsw (embedding vector_cosine_ops);
```

---

## 🎨 Source Tier System

### Tier 1: High Authority (+10 credibility boost)
- arXiv cs.IR, cs.CL (filtered: citation count >10 or h-index >20)
- Google AI Blog, DeepMind Blog
- Anthropic Research, Meta AI Research

### Tier 2: Industry Validated (+5 boost)
- LangChain blog (technical posts)
- LlamaIndex docs
- Pinecone/Weaviate/Qdrant benchmarks

### Tier 3: Monitor, Lower Weight (0 boost)
- Medium/Towards Data Science (verified authors only)

### Excluded
- LinkedIn posts, Twitter/X threads, unverified tutorials

---

## 🧠 Claim Extraction Process

### 1. Document Parsing
- **PDFs**: pdfplumber → pypdf fallback
- **HTML**: BeautifulSoup with content extraction
- **Text**: Plain text processing

### 2. LLM-Based Extraction
Uses structured prompt with strict JSON schema:
```python
{
  "claim_text": "Specific assertion",
  "evidence_type": "experiment | benchmark | case_study | theoretical | anecdotal",
  "evidence_location": "Section/Figure/Table reference",
  "metrics": {"recall_improvement": "+18%"},
  "conditions": "Under what conditions?",
  "limitations": "What caveats?",
  "rag_applicability": "chunking | retrieval | embedding | reranking | generation",
  "confidence_score": 0.85
}
```

### 3. Validation Rules
- **First 100 claims**: 100% human validation required
- **After 100**: 10% sampling (configurable)
- **Low confidence (<0.6)**: Always validate
- **Conflicts detected**: Always validate

### 4. Retry Logic
- Max 3 retries for malformed JSON
- Stricter prompts on retry
- Falls back to manual processing if all retries fail

---

## 🔍 Recommendation Algorithm

### Step 1: Hybrid Retrieval
- **Vector search** (70% weight): Semantic similarity using embeddings
- **Keyword search** (30% weight): Postgres full-text search
- Top-K: 20 claims retrieved

### Step 2: Re-ranking
Composite score from:
- **Source credibility** (30%): Tier-based + citation count
- **Claim confidence** (25%): LLM-assigned confidence
- **Recency** (15%): Exponential decay (180-day half-life)
- **Validation status** (15%): Human-validated boost
- **Evidence strength** (10%): Experiment > Benchmark > Case Study
- **Vector similarity** (5%): Original retrieval score

Top-K after rerank: 10 claims

### Step 3: LLM Generation
Structured prompt with:
- Project context (use case, constraints, challenges)
- Top-ranked claims with citations
- Output schema enforced (techniques, rationale, trade-offs)

---

## 🛠️ Development & Testing

### Run Tests
```bash
pytest
```

### Code Formatting
```bash
black .
flake8 .
```

### Database Migrations
```bash
# Test connection
python -c "from database.connection import test_connection; test_connection()"

# Apply schema
python -c "from database.connection import execute_schema_file; execute_schema_file('database/schema.sql')"
```

### View Logs
```bash
# Logs stored in logs/ directory
tail -f logs/api_*.log
```

---

## 📈 Monitoring & Metrics

### System Status Endpoint
```bash
curl http://localhost:8000/api/v1/status
```

Returns:
- Total sources & claims
- Pending validations
- Last ingestion run timestamp
- Configuration details

### Validation Stats
```bash
curl http://localhost:8000/api/v1/validation/stats
```

### Recommendation Feedback
```bash
curl -X POST http://localhost:8000/api/v1/recommendations/{id}/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "feedback": "helpful",
    "notes": "Implemented semantic chunking, saw +12% improvement"
  }'
```

---

## 🔐 Security & Rate Limiting

### Rate Limits (Redis-based)
- **Per minute**: 60 requests
- **Per hour**: 1000 requests

### CORS Configuration
Edit `ALLOWED_ORIGINS` in `.env` for your frontend domains.

### API Key Protection
Add authentication middleware for production deployments.

---

## 🚢 Production Deployment

### Environment Setup
```bash
# Set production environment
ENVIRONMENT=production
DEBUG=false

# Use production LLM endpoints
LLM_PROVIDER=azure
AZURE_OPENAI_DEPLOYMENT=gpt-4

# Increase workers
API_WORKERS=8
```

### Recommended Stack
- **Compute**: Azure App Service / Azure Container Instances
- **Database**: Azure Database for PostgreSQL (with pgvector extension)
- **Cache**: Upstash Redis (serverless)
- **Storage**: Azure Blob Storage
- **Orchestration**: n8n Cloud or self-hosted

### Scaling Considerations
- **Database**: Connection pooling (configured in `database/connection.py`)
- **LLM**: Batch processing for embeddings
- **Storage**: Azure CDN for frequently accessed documents
- **Redis**: Use for caching embeddings and rate limiting

---

## 📚 Project Structure

```
research agent brief/
├── api/
│   └── routers/
│       ├── health.py           # Health checks
│       ├── ingestion.py        # Document ingestion
│       ├── recommendations.py  # Recommendation generation
│       └── validation.py       # Human validation
├── database/
│   ├── connection.py           # DB connection & session
│   └── schema.sql              # Complete DB schema
├── ingestion/
│   ├── coordinator.py          # Pipeline orchestration
│   ├── parser.py               # PDF/HTML parsing
│   └── source_classifier.py   # Tier classification
├── normalization/
│   ├── claim_extractor.py      # LLM-based extraction
│   └── validation_queue.py     # HITL queue management
├── prompts/
│   └── extraction_prompts.py   # All LLM prompts
├── recommendations/
│   ├── retriever.py            # Hybrid search
│   ├── reranker.py             # Multi-signal reranking
│   └── generator.py            # LLM recommendation generation
├── utils/
│   ├── embedding_client.py     # OpenAI embeddings
│   ├── llm_client.py           # Multi-provider LLM
│   ├── redis_client.py         # Cache & rate limiting
│   └── storage_client.py       # S3/Blob storage
├── n8n_workflows/              # (to be added)
│   └── ingestion_pipeline.json
├── main.py                     # FastAPI app
├── config.py                   # Configuration management
├── requirements.txt            # Dependencies
├── .env.example                # Environment template
└── README.md                   # This file
```

---

## 🤝 Contributing

### Adding New Sources
1. Update `SOURCE_TIERS` in `config.py`
2. Add parsing logic in `ingestion/parser.py` if needed
3. Update n8n workflow to fetch from new source

### Improving Claim Extraction
1. Edit prompts in `prompts/extraction_prompts.py`
2. Test with sample documents
3. Adjust confidence thresholds in `.env`

### Customizing Reranking
1. Modify scoring weights in `recommendations/reranker.py`
2. Add new signals (e.g., user feedback, domain-specific scores)

---

## 🐛 Troubleshooting

### Database Connection Fails
```bash
# Check Azure database connection
python -c "from database.connection import test_connection; test_connection()"

# Verify pgvector extension is enabled
# Azure Portal → Your PostgreSQL Server → Extensions → Enable "vector"
```

### PDF Parsing Fails
- Check `parse_timeout_seconds` in `.env`
- Increase timeout for large documents
- Fallback to manual processing via validation queue

### LLM Returns Malformed JSON
- Check prompt in `prompts/extraction_prompts.py`
- Increase `CLAIM_EXTRACTION_MAX_RETRIES` in `.env`
- Review logs in `logs/api_*.log`

### No Claims Extracted
- Verify document has empirical evidence (not purely theoretical)
- Lower `MIN_CLAIM_CONFIDENCE` temporarily for testing
- Check document parsing output in logs

---

## 📞 Support & Questions

- **Issues**: Open an issue in your repository
- **Documentation**: See `/docs` endpoint when API is running
- **Logs**: Check `logs/api_*.log` for detailed error traces

---

## 📄 License

Proprietary - Internal BridgeAI use only

---

## 🎯 Roadmap

- [ ] n8n workflow templates (ingestion, validation, monitoring)
- [ ] Conflict detection and resolution UI
- [ ] Multi-language support (beyond English)
- [ ] Fine-tuned embedding models for RAG domain
- [ ] Real-time update notifications
- [ ] Benchmark tracking dashboard
- [ ] A/B testing framework for recommendations

---

**Built for BridgeAI** | **Decision-Support for RAG System Design**
