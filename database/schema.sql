-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Sources table: tracks research sources and their credibility
CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL UNIQUE,
    title TEXT,
    authors TEXT[],
    publication_date DATE,
    source_type VARCHAR(50) NOT NULL, -- arxiv, blog, benchmark, vendor_announcement
    domain VARCHAR(255) NOT NULL,
    tier VARCHAR(10) NOT NULL, -- tier_1, tier_2, tier_3
    credibility_score INTEGER DEFAULT 0,
    citation_count INTEGER DEFAULT 0,
    author_h_index INTEGER,
    raw_file_url TEXT, -- S3/Blob storage URL
    raw_file_size_bytes BIGINT,
    parsed_text TEXT,
    metadata JSONB DEFAULT '{}',
    ingestion_status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed, needs_manual
    ingestion_error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sources_url ON sources(url);
CREATE INDEX idx_sources_domain ON sources(domain);
CREATE INDEX idx_sources_tier ON sources(tier);
CREATE INDEX idx_sources_status ON sources(ingestion_status);
CREATE INDEX idx_sources_publication_date ON sources(publication_date DESC);
CREATE INDEX idx_sources_credibility ON sources(credibility_score DESC);
CREATE INDEX IF NOT EXISTS idx_sources_source_type ON sources(source_type);
CREATE INDEX IF NOT EXISTS idx_sources_created_at ON sources(created_at DESC);

-- Claims table: structured knowledge units extracted from sources
CREATE TABLE IF NOT EXISTS claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    claim_text TEXT NOT NULL,
    evidence_type VARCHAR(50) NOT NULL, -- experiment, benchmark, case_study, theoretical, anecdotal
    evidence_location TEXT, -- section/figure/table reference
    metrics JSONB, -- quantitative results
    conditions TEXT, -- under what conditions
    limitations TEXT, -- caveats and constraints
    rag_applicability VARCHAR(50) NOT NULL, -- retrieval, chunking, embedding, reranking, generation, evaluation, other
    confidence_score FLOAT NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    embedding vector(1536), -- OpenAI text-embedding-3-small default
    
    -- Validation tracking
    extraction_method VARCHAR(50) DEFAULT 'llm_auto', -- llm_auto, human_validated, human_edited
    validated_by VARCHAR(255),
    validated_at TIMESTAMP,
    validation_notes TEXT,
    
    -- Conflict tracking
    has_conflict BOOLEAN DEFAULT false,
    conflict_with_claim_ids UUID[],
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_claims_source_id ON claims(source_id);
CREATE INDEX idx_claims_evidence_type ON claims(evidence_type);
CREATE INDEX idx_claims_rag_applicability ON claims(rag_applicability);
CREATE INDEX idx_claims_confidence ON claims(confidence_score DESC);
CREATE INDEX idx_claims_extraction_method ON claims(extraction_method);
CREATE INDEX idx_claims_has_conflict ON claims(has_conflict) WHERE has_conflict = true;

-- Vector similarity search index (HNSW for performance)
CREATE INDEX idx_claims_embedding ON claims USING hnsw (embedding vector_cosine_ops);

-- Validation queue: tracks claims requiring human review
CREATE TABLE IF NOT EXISTS validation_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    priority INTEGER DEFAULT 0, -- higher = more urgent
    reason VARCHAR(255), -- sampling, low_confidence, conflict, malformed
    assigned_to VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending', -- pending, in_review, approved, rejected, edited
    reviewer_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    reviewed_at TIMESTAMP
);

CREATE INDEX idx_validation_queue_status ON validation_queue(status);
CREATE INDEX idx_validation_queue_priority ON validation_queue(priority DESC);
CREATE INDEX idx_validation_queue_assigned ON validation_queue(assigned_to);

-- Recommendation logs: track what was recommended and why
CREATE TABLE IF NOT EXISTS recommendation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_context JSONB NOT NULL,
    retrieved_claim_ids UUID[] NOT NULL,
    reranked_claim_ids UUID[] NOT NULL,
    final_recommendation TEXT NOT NULL,
    reasoning TEXT,
    citations JSONB,
    retrieval_metrics JSONB, -- top-k scores, vector/keyword weights
    llm_model VARCHAR(100),
    llm_tokens_used INTEGER,
    response_time_ms INTEGER,
    user_feedback VARCHAR(50), -- helpful, not_helpful, partially_helpful
    user_feedback_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_recommendation_logs_created_at ON recommendation_logs(created_at DESC);

-- Fetch logs: track scheduled and manual multi-source ingestion runs
CREATE TABLE IF NOT EXISTS fetch_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type VARCHAR(50) NOT NULL,
    fetch_timestamp TIMESTAMP DEFAULT NOW(),
    items_fetched INTEGER DEFAULT 0,
    items_new INTEGER DEFAULT 0,
    items_duplicate INTEGER DEFAULT 0,
    fetch_duration_seconds FLOAT DEFAULT 0,
    status VARCHAR(50) DEFAULT 'success',
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    keywords TEXT[]
);

CREATE INDEX IF NOT EXISTS idx_fetch_logs_source ON fetch_logs(source_type);
CREATE INDEX IF NOT EXISTS idx_fetch_logs_timestamp ON fetch_logs(fetch_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_fetch_logs_status ON fetch_logs(status);

-- Source quality metrics: track source reliability over time
CREATE TABLE IF NOT EXISTS source_quality_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    metric_date DATE NOT NULL DEFAULT CURRENT_DATE,
    claims_extracted INTEGER DEFAULT 0,
    claims_validated INTEGER DEFAULT 0,
    claims_rejected INTEGER DEFAULT 0,
    average_claim_confidence FLOAT,
    times_cited_in_recommendations INTEGER DEFAULT 0,
    user_feedback_positive INTEGER DEFAULT 0,
    user_feedback_negative INTEGER DEFAULT 0,
    UNIQUE(source_id, metric_date)
);

CREATE INDEX idx_source_quality_source_id ON source_quality_metrics(source_id);
CREATE INDEX idx_source_quality_date ON source_quality_metrics(metric_date DESC);

-- Uploaded project briefs and brief-derived intelligence
CREATE TABLE IF NOT EXISTS uploaded_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_name TEXT NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    content_text TEXT NOT NULL,
    parsed_summary TEXT,
    metadata JSONB DEFAULT '{}',
    processing_status VARCHAR(50) DEFAULT 'pending',
    processing_error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_uploaded_briefs_status ON uploaded_briefs(processing_status);
CREATE INDEX IF NOT EXISTS idx_uploaded_briefs_created_at ON uploaded_briefs(created_at DESC);

CREATE TABLE IF NOT EXISTS brief_extracted_topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brief_id UUID NOT NULL REFERENCES uploaded_briefs(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    category VARCHAR(80) DEFAULT 'technical',
    confidence_score FLOAT DEFAULT 0.0 CHECK (confidence_score >= 0 AND confidence_score <= 1),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_brief_topics_brief_id ON brief_extracted_topics(brief_id);
CREATE INDEX IF NOT EXISTS idx_brief_topics_topic ON brief_extracted_topics(topic);

CREATE TABLE IF NOT EXISTS brief_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brief_id UUID NOT NULL REFERENCES uploaded_briefs(id) ON DELETE CASCADE,
    technology_name TEXT NOT NULL,
    category VARCHAR(100) DEFAULT 'technology',
    summary TEXT,
    recommendation TEXT,
    confidence_score FLOAT DEFAULT 0.0 CHECK (confidence_score >= 0 AND confidence_score <= 1),
    implementation_difficulty VARCHAR(50),
    final_score FLOAT DEFAULT 0.0,
    alternatives TEXT[] DEFAULT ARRAY[]::TEXT[],
    risks_tradeoffs TEXT[] DEFAULT ARRAY[]::TEXT[],
    suggested_architecture TEXT,
    next_steps TEXT[] DEFAULT ARRAY[]::TEXT[],
    citations JSONB DEFAULT '[]',
    scoring_breakdown JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_brief_recommendations_brief_id ON brief_recommendations(brief_id);
CREATE INDEX IF NOT EXISTS idx_brief_recommendations_score ON brief_recommendations(final_score DESC);
CREATE INDEX IF NOT EXISTS idx_brief_recommendations_technology ON brief_recommendations(technology_name);

-- Technology radar and supporting source links
CREATE TABLE IF NOT EXISTS technologies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    category VARCHAR(100),
    description TEXT,
    evidence_score FLOAT DEFAULT 0.0,
    recency_score FLOAT DEFAULT 0.0,
    adoption_signal FLOAT DEFAULT 0.0,
    source_count INTEGER DEFAULT 0,
    radar_stage VARCHAR(50) DEFAULT 'Assess',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_technologies_stage ON technologies(radar_stage);
CREATE INDEX IF NOT EXISTS idx_technologies_score ON technologies(evidence_score DESC);

CREATE TABLE IF NOT EXISTS technology_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    technology_id UUID NOT NULL REFERENCES technologies(id) ON DELETE CASCADE,
    source_id UUID REFERENCES sources(id) ON DELETE SET NULL,
    source_url TEXT,
    source_title TEXT,
    relevance_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_technology_sources_technology_id ON technology_sources(technology_id);
CREATE INDEX IF NOT EXISTS idx_technology_sources_source_id ON technology_sources(source_id);

-- Daily team intelligence reports and email delivery logs
CREATE TABLE IF NOT EXISTS daily_intelligence_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_date DATE NOT NULL DEFAULT CURRENT_DATE,
    subject TEXT NOT NULL,
    summary TEXT,
    top_updates JSONB DEFAULT '[]',
    worth_exploring JSONB DEFAULT '[]',
    emerging_signals JSONB DEFAULT '[]',
    ignore_for_now JSONB DEFAULT '[]',
    html_body TEXT,
    markdown_body TEXT,
    citations JSONB DEFAULT '[]',
    processing_status VARCHAR(50) DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_daily_reports_date ON daily_intelligence_reports(report_date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_reports_created_at ON daily_intelligence_reports(created_at DESC);

CREATE TABLE IF NOT EXISTS sent_email_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID REFERENCES daily_intelligence_reports(id) ON DELETE SET NULL,
    recipient_email TEXT,
    provider VARCHAR(50),
    subject TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sent_email_logs_report_id ON sent_email_logs(report_id);
CREATE INDEX IF NOT EXISTS idx_sent_email_logs_created_at ON sent_email_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sent_email_logs_status ON sent_email_logs(status);

CREATE TABLE IF NOT EXISTS team_email_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_email TEXT,
    send_time VARCHAR(5) DEFAULT '08:00',
    timezone VARCHAR(100) DEFAULT 'UTC',
    topics TEXT[] DEFAULT ARRAY[]::TEXT[],
    enabled BOOLEAN DEFAULT false,
    provider VARCHAR(50) DEFAULT 'disabled',
    updated_by TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS source_fetch_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT,
    source_name TEXT,
    enabled BOOLEAN DEFAULT true,
    api_key_status VARCHAR(50),
    rate_limit_status VARCHAR(100),
    last_fetch_time TIMESTAMP,
    status VARCHAR(50),
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_source_fetch_logs_source_id ON source_fetch_logs(source_id);
CREATE INDEX IF NOT EXISTS idx_source_fetch_logs_last_fetch ON source_fetch_logs(last_fetch_time DESC);

-- System metadata: track ingestion runs and system state
CREATE TABLE IF NOT EXISTS system_metadata (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert initial system metadata
INSERT INTO system_metadata (key, value) VALUES 
    ('last_ingestion_run', '{"status": "never", "timestamp": null}'),
    ('total_sources', '{"count": 0}'),
    ('total_claims', '{"count": 0}'),
    ('validation_stats', '{"pending": 0, "completed": 0}')
ON CONFLICT (key) DO NOTHING;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_sources_updated_at BEFORE UPDATE ON sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_claims_updated_at BEFORE UPDATE ON claims
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_uploaded_briefs_updated_at ON uploaded_briefs;
CREATE TRIGGER update_uploaded_briefs_updated_at BEFORE UPDATE ON uploaded_briefs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_brief_extracted_topics_updated_at ON brief_extracted_topics;
CREATE TRIGGER update_brief_extracted_topics_updated_at BEFORE UPDATE ON brief_extracted_topics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_brief_recommendations_updated_at ON brief_recommendations;
CREATE TRIGGER update_brief_recommendations_updated_at BEFORE UPDATE ON brief_recommendations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_technologies_updated_at ON technologies;
CREATE TRIGGER update_technologies_updated_at BEFORE UPDATE ON technologies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_daily_reports_updated_at ON daily_intelligence_reports;
CREATE TRIGGER update_daily_reports_updated_at BEFORE UPDATE ON daily_intelligence_reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_sent_email_logs_updated_at ON sent_email_logs;
CREATE TRIGGER update_sent_email_logs_updated_at BEFORE UPDATE ON sent_email_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_team_email_settings_updated_at ON team_email_settings;
CREATE TRIGGER update_team_email_settings_updated_at BEFORE UPDATE ON team_email_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_source_fetch_logs_updated_at ON source_fetch_logs;
CREATE TRIGGER update_source_fetch_logs_updated_at BEFORE UPDATE ON source_fetch_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
