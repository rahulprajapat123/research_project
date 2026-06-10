"""
Project Research Copilot - Backend API

Pipeline Flow:
1. Accept project name + document brief from developer
2. Extract topics/keywords from document brief
3. Search research papers on arXiv and other sources
4. Analyze architecture (LLM vs RAG vs Hybrid vs Fine-tuning) from latest research papers
5. Return comprehensive analysis with 12 sections
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
import asyncio
import re
from loguru import logger

from utils.llm_client import LLMClient

router = APIRouter()
llm_client = LLMClient()

# ============================================================================
# MODELS
# ============================================================================

class CopilotRequest(BaseModel):
    """Input: Project name + document brief"""
    project_name: str = Field(..., description="Name of the project")
    project_brief: str = Field(..., description="Document brief from developer")

class ResearchPaper(BaseModel):
    """Research paper metadata"""
    title: str
    authors: List[str]
    year: int
    url: str
    abstract: str
    source: str  # arxiv, openreview, huggingface, etc.
    relevance_score: float = 0.0  # Ranking score for project relevance

class CopilotResponse(BaseModel):
    """Complete 12-section analysis output"""
    project_name: str
    arxiv_papers: List[ResearchPaper] = Field(default_factory=list, description="Papers downloaded from arXiv")
    project_understanding: List[str]
    assumptions: List[str]
    user_personas_and_use_cases: List[str]
    functional_requirements: Dict[str, List[str]]
    non_functional_requirements: Dict[str, str]
    architecture_decision: Dict[str, str]
    system_design: Dict[str, Any]
    research_digest: Dict[str, Any]
    tech_stack: Dict[str, List[str]]
    milestones: Dict[str, str]
    risks_and_mitigations: List[Dict[str, str]]
    next_steps: List[str]

# ============================================================================
# STEP 1: EXTRACT KEYWORDS/TOPICS FROM BRIEF
# ============================================================================

async def extract_keywords_and_topics(document_brief: str) -> Dict[str, Any]:
    """Extract PROJECT-SPECIFIC keywords, topics, and search terms from document brief"""
    
    prompt = f"""Analyze this SPECIFIC project brief and extract UNIQUE search terms for finding relevant research papers.

CRITICAL: Extract terms that are SPECIFIC to this project's requirements, NOT generic AI/ML terms.

Project Brief:
{document_brief}

Extract:
1. **Core Topics** (3-5 SPECIFIC main technical challenges/areas for THIS project)
   - NOT generic like "AI" or "machine learning"
   - Examples: "multi-document retrieval", "long-context reasoning", "real-time embedding generation"

2. **Research Keywords** (10-15 SPECIFIC technical terms for arXiv search)
   - Focus on techniques, methods, architectures mentioned or implied
   - Include domain-specific terminology
   - Examples: "dense retrieval", "ColBERT", "retrieval-augmented generation", "semantic chunking"

3. **Technical Requirements** (5-8 specific technical needs)
   - What technologies/methods does THIS project need?
   - Examples: "vector similarity search", "streaming responses", "document parsing"

4. **Problem Domain** (specific application domain)
   - Healthcare, Legal, Finance, Education, E-commerce, Customer Support, etc.

5. **Use Case Type** (specific use case category)
   - QA system, chatbot, knowledge base, document analysis, recommendation engine, etc.

Return ONLY valid JSON (no markdown):
{{
  "core_topics": ["specific topic 1", "specific topic 2", ...],
  "keywords": ["specific keyword 1", "specific keyword 2", ...],
  "technical_requirements": ["requirement 1", "requirement 2", ...],
  "technical_domains": ["domain1", "domain2"],
  "problem_domain": "specific domain",
  "use_case_type": "specific use case",
  "project_hash": "generate a unique 8-char identifier from key terms"
}}

Focus on UNIQUENESS - different projects should have DIFFERENT keywords!"""

    try:
        response = await llm_client.complete(
            prompt=prompt,
            temperature=0.4,  # Slightly higher for more varied extraction
            max_tokens=1000
        )
        
        import json
        import hashlib
        
        # Try to parse as JSON
        try:
            # Remove markdown code blocks if present
            clean_response = response.strip()
            if clean_response.startswith("```"):
                clean_response = clean_response.split("```")[1]
                if clean_response.startswith("json"):
                    clean_response = clean_response[4:]
            
            extracted = json.loads(clean_response)
            
            # Generate project hash from brief for cache differentiation
            brief_hash = hashlib.md5(document_brief.encode()).hexdigest()
            extracted["project_hash"] = brief_hash
            
        except json.JSONDecodeError:
            # LLM returned text instead of JSON - intelligent extraction
            logger.warning("LLM returned non-JSON, performing intelligent extraction")
            
            # Extract meaningful keywords from the brief itself
            brief_lower = document_brief.lower()
            
            # Technical terms to look for
            tech_terms = {
                "retrieval", "embedding", "vector", "semantic", "rag", "llm", "gpt", 
                "claude", "llama", "bert", "transformer", "attention", "fine-tuning",
                "prompt", "chat", "conversation", "agent", "tool", "function calling",
                "knowledge", "document", "search", "query", "ranking", "reranking",
                "chunking", "indexing", "database", "postgres", "vector db",
                "api", "real-time", "streaming", "async", "latency", "scale"
            }
            
            found_keywords = []
            for term in tech_terms:
                if term in brief_lower:
                    found_keywords.append(term)
            
            # Extract domain indicators
            domains = {
                "healthcare": ["medical", "health", "patient", "clinical", "diagnosis"],
                "legal": ["legal", "law", "contract", "compliance", "regulation"],
                "finance": ["financial", "trading", "banking", "investment", "market"],
                "education": ["education", "learning", "student", "course", "teaching"],
                "ecommerce": ["ecommerce", "shopping", "product", "retail", "commerce"],
                "support": ["support", "customer", "help", "ticket", "service"]
            }
            
            problem_domain = "general"
            for domain, indicators in domains.items():
                if any(ind in brief_lower for ind in indicators):
                    problem_domain = domain
                    break
            
            # Generate hash
            brief_hash = hashlib.md5(document_brief.encode()).hexdigest()
            
            extracted = {
                "core_topics": found_keywords[:5] if found_keywords else ["information retrieval", "natural language processing"],
                "keywords": found_keywords[:15] if found_keywords else ["retrieval augmented generation", "language models"],
                "technical_requirements": found_keywords[5:10] if len(found_keywords) > 5 else ["embedding generation", "similarity search"],
                "technical_domains": ["AI/ML", "NLP"],
                "problem_domain": problem_domain,
                "use_case_type": "ai application",
                "project_hash": brief_hash
            }
        
        logger.info(f"✅ Extracted {len(extracted.get('keywords', []))} PROJECT-SPECIFIC keywords")
        logger.info(f"   Project Hash: {extracted.get('project_hash', 'N/A')[:8]}")
        logger.info(f"   Keywords: {', '.join(extracted.get('keywords', [])[:5])}")
        return extracted
        
    except Exception as e:
        logger.error(f"Keyword extraction failed: {e}")
        # Fallback with hash
        import hashlib
        brief_hash = hashlib.md5(document_brief.encode()).hexdigest()
        return {
            "core_topics": ["information retrieval", "language models"],
            "keywords": ["retrieval augmented generation", "large language models", "semantic search"],
            "technical_requirements": ["vector embeddings", "similarity search"],
            "technical_domains": ["AI/ML"],
            "problem_domain": "general",
            "use_case_type": "ai application",
            "project_hash": brief_hash
        }

# ============================================================================
# STEP 2: SEARCH ARXIV API
# ============================================================================

async def search_arxiv(keywords: List[str], max_results: int = 15) -> List[ResearchPaper]:
    """Search arXiv for LATEST papers (2022-2026) matching keywords"""
    
    papers = []
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create search queries from keywords - simplified approach
            queries = []
            
            # Combine keywords for better results
            for i in range(0, len(keywords), 2):
                query_terms = keywords[i:i+2]
                # Simple query without date filtering (we'll filter after)
                query = " AND ".join([f'all:"{term}"' for term in query_terms])
                queries.append(query)
            
            # Search each query
            for query in queries[:5]:  # Increased to get more recent papers
                url = "https://export.arxiv.org/api/query"
                params = {
                    "search_query": query,
                    "start": 0,
                    "max_results": max_results * 2,  # Get more, filter later
                    "sortBy": "submittedDate",  # Sort by submission date
                    "sortOrder": "descending"
                }
                
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                # Parse XML
                root = ET.fromstring(response.content)
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                
                for entry in root.findall("atom:entry", ns):
                    title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
                    
                    authors = []
                    for author in entry.findall("atom:author", ns):
                        name = author.find("atom:name", ns)
                        if name is not None:
                            authors.append(name.text)
                    
                    published = entry.find("atom:published", ns).text
                    year = int(published[:4])
                    
                    # Filter: only keep papers from 2022 onwards
                    if year < 2022:
                        continue
                    
                    url = entry.find("atom:id", ns).text
                    abstract = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
                    
                    papers.append(ResearchPaper(
                        title=title,
                        authors=authors,
                        year=year,
                        url=url,
                        abstract=abstract,
                        source="arxiv"
                    ))
                
                await asyncio.sleep(0.5)  # Rate limiting
        
        # Deduplicate by title
        seen = set()
        unique_papers = []
        for paper in papers:
            title_key = paper.title.lower().strip()
            if title_key not in seen:
                seen.add(title_key)
                unique_papers.append(paper)
        
        # Sort by year (newest first) and limit
        unique_papers.sort(key=lambda p: p.year, reverse=True)
        
        logger.info(f"Found {len(unique_papers[:max_results])} unique papers from arXiv (2022-2026)")
        return unique_papers[:max_results]
        
    except Exception as e:
        logger.error(f"arXiv search failed: {e}")
        return []

# ============================================================================
# STEP 3: SEARCH OPENREVIEW & OTHER AI/ML SITES
# ============================================================================

async def search_ai_ml_sites(keywords: List[str], max_results: int = 5) -> List[ResearchPaper]:
    """
    Search OpenReview and other AI/ML/RAG research sites
    
    Note: This is a placeholder. Real implementation would:
    - Search OpenReview API (requires auth)
    - Search Hugging Face papers
    - Search Papers with Code
    - Search Google Scholar
    """
    
    # For now, we'll note this in the response
    logger.info(f"AI/ML site search requested for: {', '.join(keywords[:3])}")
    
    # Placeholder - in production, integrate with:
    # - OpenReview API: https://api.openreview.net
    # - Papers with Code API: https://paperswithcode.com/api/v1/
    # - Semantic Scholar API: https://api.semanticscholar.org
    
    return []

# ============================================================================
# STEP 3: RANK PAPERS BY RELEVANCE
# ============================================================================

async def rank_papers_by_relevance(
    papers: List[ResearchPaper],
    document_brief: str,
    keywords: List[str]
) -> List[ResearchPaper]:
    """Rank papers by relevance to project brief"""
    
    if not papers:
        return []
    
    # Create concise paper summaries for ranking
    papers_text = "\n\n".join([
        f"Paper {i+1}: {p.title} ({p.year})\nAbstract: {p.abstract[:300]}..."
        for i, p in enumerate(papers[:15])
    ])
    
    keywords_text = ", ".join(keywords)
    
    prompt = f"""Rank these papers by relevance to the project. Consider:
- How well the paper's methods apply to this project
- Recency (favor 2023-2026 papers)
- Practical implementation insights

Project Brief: {document_brief[:500]}
Keywords: {keywords_text}

Papers:
{papers_text}

Output ONLY paper numbers with scores (1-10), format: paper_number,score
Example:
1,9.5
2,7.8
3,8.2"""

    try:
        response = await llm_client.complete(
            prompt=prompt,
            temperature=0.2,
            max_tokens=400
        )
        
        # Parse rankings
        rankings = {}
        for line in response.strip().split("\n"):
            if "," in line:
                try:
                    parts = line.strip().split(",")
                    paper_num = int(parts[0])
                    score = float(parts[1])
                    rankings[paper_num] = score
                except:
                    continue
        
        # Apply scores
        for i, paper in enumerate(papers[:15]):
            paper_idx = i + 1
            if paper_idx in rankings:
                # Store score in the model field
                paper.relevance_score = rankings[paper_idx]
            else:
                # Fallback: use year-based score
                paper.relevance_score = (paper.year - 2015) / 10
        
        # Sort by score
        sorted_papers = sorted(
            papers,
            key=lambda p: (p.relevance_score, p.year),
            reverse=True
        )
        
        return sorted_papers[:12]
        
    except Exception as e:
        logger.error(f"Paper ranking failed: {e}")
        return sorted(papers, key=lambda p: p.year, reverse=True)[:12]

# ============================================================================
# STEP 5: COMPREHENSIVE ANALYSIS (12 SECTIONS)
# ============================================================================

async def generate_comprehensive_analysis(
    project_name: str,
    document_brief: str,
    keywords: Dict[str, Any],
    papers: List[ResearchPaper]
) -> CopilotResponse:
    """Generate all 12 sections of the analysis"""
    
    # Prepare research context with MORE details from papers
    papers_summary = "\n\n".join([
        f"Paper {i+1}: [{p.source.upper()} {p.year}] {p.title}\n"
        f"Abstract: {p.abstract[:400]}...\n"
        f"URL: {p.url}"
        for i, p in enumerate(papers[:12])
    ])
    
    keywords_text = ", ".join(keywords.get("keywords", []))
    topics_text = ", ".join(keywords.get("core_topics", []))
    
    # Master analysis prompt with emphasis on extracting tech from papers
    prompt = f"""You are a Product Research Copilot for developers. Generate a comprehensive build plan based on LATEST research.

CRITICAL: Analyze the research papers below and extract:
- Novel techniques, architectures, and methodologies mentioned
- Specific models, frameworks, and tools referenced
- Latest technologies and implementations from 2023-2026
- Innovative approaches that are state-of-the-art

PROJECT NAME: {project_name}

DOCUMENT BRIEF:
{document_brief}

EXTRACTED TOPICS: {topics_text}
KEYWORDS: {keywords_text}
TECHNICAL DOMAINS: {', '.join(keywords.get('technical_domains', []))}
PROBLEM DOMAIN: {keywords.get('problem_domain', 'general')}

RESEARCH PAPERS FOUND:
{papers_summary}

Generate ALL 12 sections below. Be specific and actionable.

1. PROJECT UNDERSTANDING (2-4 bullets)
- Summarize what this project aims to build

2. ASSUMPTIONS (only if details are missing)
- List assumptions about unclear requirements

3. USER PERSONAS & USE CASES (4-6 bullets)
- Who will use this and for what specific scenarios?

4. FUNCTIONAL REQUIREMENTS
MUST-HAVE (5-8 core features):
SHOULD-HAVE (3-5 nice-to-have features):

5. NON-FUNCTIONAL REQUIREMENTS
Latency: [target response time with justification]
Privacy: [data handling and compliance requirements]
Scale: [expected users/queries per day/month]
Cost: [budget considerations and optimization]

6. ARCHITECTURE DECISION
CHOICE: Choose ONE from [LLM Only | RAG (Embeddings + Retrieval) | Hybrid (RAG + LLM) | Fine-tuning]

REASONING (2-3 sentences):
Why this architecture fits based on:
- Use RAG for: factual grounding, long documents, enterprise knowledge, citation needs, changing information
- Use LLM/Agents for: workflow automation, reasoning over small context, tool-calling, decisioning
- Use Hybrid when: need both structured knowledge AND reasoning/synthesis
- Use Fine-tuning ONLY if: stable repetitive pattern, strict formatting, domain style, AND sufficient data

7. SYSTEM DESIGN
COMPONENTS (5-8 key components):
DATA FLOW (4-6 steps describing how data flows through system):

8. RESEARCH DIGEST
MANDATORY: Analyze ALL papers above and extract:
- Novel techniques and architectures mentioned in papers (be specific)
- Specific models, frameworks, libraries cited (exact names/versions)
- Latest methodologies from 2023-2026 papers
- Implementation insights and code references
- Evaluation metrics and benchmarks used
- Pitfalls and challenges discussed

9. RECOMMENDED TECH STACK
CRITICAL: Base recommendations on research papers above AND latest 2024-2026 technologies.
Extract specific tools/models mentioned in papers. Include versions where relevant.

LLM_LAYER: [Extract from papers: GPT-4o, Claude 3.5 Sonnet, Llama 3.1, Gemini 2.0, Mistral, etc. - use LATEST models from papers]
RETRIEVAL_LAYER: [If RAG: specific embedding models from papers like text-embedding-3-large, BGE, ColBERT; Vector DBs like Qdrant, Weaviate, Pinecone, pgvector]
DATA_STORES: [Modern choices: PostgreSQL with pgvector, MongoDB, Redis Stack, Upstash]
BACKEND: [Modern frameworks: FastAPI + Python 3.12, Node.js + TypeScript, Go]
FRONTEND: [Modern: Next.js 14+, React 18+, Vue 3+, SvelteKit, Tailwind CSS]
TOOLS_LIBRARIES: [Specific libraries from papers: LangChain, LlamaIndex, DSPy, Instructor, etc.]
EVALUATION: [From papers: RAGAS, TruLens, Phoenix, LangSmith, custom eval harnesses]

10. MILESTONES
MVP (Week 1-2): [minimum viable features to validate concept]
V1 (Week 3-4): [core functionality complete]
V2 (Week 5-6): [full feature set with optimization]

11. RISKS & MITIGATIONS
List 4-6 risks with specific mitigations.

12. WHAT TO BUILD NEXT (5 concrete action items)
List exact next steps to start development today.

OUTPUT MUST BE VALID JSON:
{{
  "project_understanding": ["point1", "point2", ...],
  "assumptions": ["assumption1", ...],
  "user_personas_and_use_cases": ["persona1: use case", ...],
  "functional_requirements": {{
    "must_have": ["feature1", ...],
    "should_have": ["feature1", ...]
  }},
  "non_functional_requirements": {{
    "latency": "detailed requirement",
    "privacy": "detailed requirement",
    "scale": "detailed requirement",
    "cost": "detailed requirement"
  }},
  "architecture_decision": {{
    "choice": "Hybrid (RAG + LLM)",
    "reasoning": "detailed reasoning"
  }},
  "system_design": {{
    "components": ["component1", ...],
    "data_flow": ["step1", "step2", ...]
  }},
  "research_digest": {{
    "key_notes": ["insight from paper 1", "technique from paper 2", "finding from paper 3"],
    "novel_techniques": ["specific technique 1", "architecture 2"],
    "specific_models": ["model name 1", "framework 2"],
    "latest_findings": ["2024 finding 1", "2025 technique 2"]
  }},
  "tech_stack": {{
    "llm_layer": ["Specific model from papers with version"],
    "retrieval_layer": ["Embedding model + Vector DB from papers"],
    "data_stores": ["Modern database choices"],
    "backend": ["Framework + Language version"],
    "frontend": ["Modern framework if needed"],
    "tools_libraries": ["Specific libraries from papers"],
    "evaluation": ["Tools mentioned in papers"]
  }},
  "milestones": {{
    "mvp": "description",
    "v1": "description",
    "v2": "description"
  }},
  "risks_and_mitigations": [
    {{"risk": "risk1", "mitigation": "solution1"}},
    ...
  ],
  "next_steps": ["step1", "step2", ...]
}}"""

    try:
        response = await llm_client.complete(
            prompt=prompt,
            temperature=0.8,  # Higher temperature for more creative tech stack suggestions
            max_tokens=4096  # Model maximum
        )
        
        import json
        
        # Try to parse as JSON
        try:
            analysis = json.loads(response)
        except json.JSONDecodeError:
            # If LLM doesn't return JSON, create structured response from text
            logger.warning("LLM returned non-JSON, extracting structured data from papers")
            
            # Extract technologies mentioned in paper abstracts AND titles
            tech_keywords = {
                "models": set(),
                "frameworks": set(),
                "methods": set(),
                "databases": set(),
                "techniques": set(),
                "metrics": set()
            }
            
            paper_insights = []  # Store key insights from each paper
            
            for paper in papers[:12]:
                text_to_analyze = (paper.title + " " + paper.abstract).lower()
                paper_year = paper.year
                
                # Extract paper-specific insights
                insight = {
                    "paper": paper.title[:100],
                    "year": paper_year,
                    "url": paper.url,
                    "key_contribution": "",
                    "technologies": []
                }
                
                # LATEST AI/ML models (prioritize 2024-2026 papers)
                if "gpt-4o" in text_to_analyze or "gpt4o" in text_to_analyze: 
                    tech_keywords["models"].add("GPT-4o (2024)")
                    insight["technologies"].append("GPT-4o")
                elif "gpt-4" in text_to_analyze or "gpt4" in text_to_analyze: 
                    tech_keywords["models"].add("GPT-4 Turbo")
                    insight["technologies"].append("GPT-4")
                elif "gpt-3.5" in text_to_analyze or "gpt3" in text_to_analyze: 
                    tech_keywords["models"].add("GPT-3.5")
                    
                if "claude 3.5" in text_to_analyze or "claude-3.5" in text_to_analyze: 
                    tech_keywords["models"].add("Claude 3.5 Sonnet (2024)")
                    insight["technologies"].append("Claude 3.5")
                elif "claude 3" in text_to_analyze or "claude-3" in text_to_analyze: 
                    tech_keywords["models"].add("Claude 3")
                elif "claude" in text_to_analyze: 
                    tech_keywords["models"].add("Claude (Anthropic)")
                    
                if "llama 3.3" in text_to_analyze or "llama3.3" in text_to_analyze:
                    tech_keywords["models"].add("Llama 3.3 (Meta, 2024)")
                    insight["technologies"].append("Llama 3.3")
                elif "llama 3.1" in text_to_analyze or "llama3.1" in text_to_analyze:
                    tech_keywords["models"].add("Llama 3.1 (Meta)")
                    insight["technologies"].append("Llama 3.1")
                elif "llama 3" in text_to_analyze or "llama3" in text_to_analyze: 
                    tech_keywords["models"].add("Llama 3 (Meta)")
                elif "llama-2" in text_to_analyze or "llama 2" in text_to_analyze:
                    tech_keywords["models"].add("Llama 2")
                    
                if "gemini 2.0" in text_to_analyze or "gemini-2" in text_to_analyze: 
                    tech_keywords["models"].add("Gemini 2.0 (Google, 2024)")
                    insight["technologies"].append("Gemini 2.0")
                elif "gemini 1.5" in text_to_analyze: 
                    tech_keywords["models"].add("Gemini 1.5 Pro")
                elif "gemini" in text_to_analyze: 
                    tech_keywords["models"].add("Gemini (Google)")
                    
                if "mistral" in text_to_analyze: 
                    tech_keywords["models"].add("Mistral Large")
                    insight["technologies"].append("Mistral")
                if "qwen" in text_to_analyze or "qwen2" in text_to_analyze:
                    tech_keywords["models"].add("Qwen 2 (Alibaba)")
                    insight["technologies"].append("Qwen")
                if "deepseek" in text_to_analyze:
                    tech_keywords["models"].add("DeepSeek")
                    insight["technologies"].append("DeepSeek")
                
                # Embedding models
                if "text-embedding-3" in text_to_analyze or "text embedding 3" in text_to_analyze: 
                    tech_keywords["models"].add("text-embedding-3-large (OpenAI)")
                    insight["technologies"].append("text-embedding-3")
                elif "ada-002" in text_to_analyze or "ada 002" in text_to_analyze:
                    tech_keywords["models"].add("text-embedding-ada-002")
                if "bge" in text_to_analyze and "embedding" in text_to_analyze: 
                    tech_keywords["models"].add("BGE embeddings (BAAI)")
                    insight["technologies"].append("BGE")
                if "e5" in text_to_analyze and "embedding" in text_to_analyze:
                    tech_keywords["models"].add("E5 embeddings")
                    insight["technologies"].append("E5")
                if "colbert" in text_to_analyze: 
                    tech_keywords["models"].add("ColBERT v2")
                    tech_keywords["methods"].add("Late interaction retrieval")
                    insight["technologies"].append("ColBERT")
                if "sentence-bert" in text_to_analyze or "sbert" in text_to_analyze:
                    tech_keywords["models"].add("Sentence-BERT")
                    insight["technologies"].append("SBERT")
                
                # RAG and retrieval techniques
                if "rag" in text_to_analyze or "retrieval-augmented" in text_to_analyze: 
                    tech_keywords["methods"].add("RAG (Retrieval-Augmented Generation)")
                if "agentic rag" in text_to_analyze or "multi-hop" in text_to_analyze:
                    tech_keywords["methods"].add("Agentic RAG / Multi-hop retrieval")
                    insight["key_contribution"] = "Multi-hop retrieval approach"
                if "self-rag" in text_to_analyze or "self rag" in text_to_analyze:
                    tech_keywords["methods"].add("Self-RAG (reflective retrieval)")
                    insight["key_contribution"] = "Self-correcting RAG"
                if "crag" in text_to_analyze or "corrective rag" in text_to_analyze:
                    tech_keywords["methods"].add("CRAG (Corrective RAG)")
                if "raptor" in text_to_analyze and "rag" in text_to_analyze:
                    tech_keywords["methods"].add("RAPTOR (Recursive embedding)")
                    insight["key_contribution"] = "Recursive document embedding"
                if "hyde" in text_to_analyze or "hypothetical document" in text_to_analyze:
                    tech_keywords["methods"].add("HyDE (Hypothetical Document Embeddings)")
                    
                # Advanced techniques
                if "semantic chunking" in text_to_analyze or "adaptive chunking" in text_to_analyze:
                    tech_keywords["techniques"].add("Semantic/adaptive chunking")
                    insight["key_contribution"] = "Advanced chunking strategy"
                if "rerank" in text_to_analyze or "re-rank" in text_to_analyze:
                    tech_keywords["techniques"].add("Reranking models")
                if "cohere rerank" in text_to_analyze:
                    tech_keywords["models"].add("Cohere Rerank")
                if "query expansion" in text_to_analyze or "query decomposition" in text_to_analyze:
                    tech_keywords["techniques"].add("Query expansion/decomposition")
                if "hybrid search" in text_to_analyze or "bm25" in text_to_analyze:
                    tech_keywords["techniques"].add("Hybrid search (vector + keyword)")
                    
                # Evaluation metrics
                if "ragas" in text_to_analyze:
                    tech_keywords["frameworks"].add("RAGAS (RAG evaluation)")
                    tech_keywords["metrics"].add("Faithfulness, Relevancy, Context Recall")
                if "rouge" in text_to_analyze:
                    tech_keywords["metrics"].add("ROUGE metrics")
                if "bleu" in text_to_analyze:
                    tech_keywords["metrics"].add("BLEU score")
                if "recall" in text_to_analyze and "precision" in text_to_analyze:
                    tech_keywords["metrics"].add("Precision/Recall")
                if "ndcg" in text_to_analyze or "normalized discounted" in text_to_analyze:
                    tech_keywords["metrics"].add("NDCG (ranking metric)")
                if "hit rate" in text_to_analyze or "mrr" in text_to_analyze:
                    tech_keywords["metrics"].add("Hit Rate / MRR")
                    
                # Frameworks and libraries
                if "langchain" in text_to_analyze: 
                    tech_keywords["frameworks"].add("LangChain")
                    insight["technologies"].append("LangChain")
                if "llamaindex" in text_to_analyze or "llama-index" in text_to_analyze or "llama index" in text_to_analyze: 
                    tech_keywords["frameworks"].add("LlamaIndex")
                    insight["technologies"].append("LlamaIndex")
                if "dspy" in text_to_analyze or "dsp" in text_to_analyze: 
                    tech_keywords["frameworks"].add("DSPy (Stanford)")
                    insight["technologies"].append("DSPy")
                if "haystack" in text_to_analyze:
                    tech_keywords["frameworks"].add("Haystack")
                if "autogen" in text_to_analyze or "auto-gen" in text_to_analyze:
                    tech_keywords["frameworks"].add("AutoGen (Microsoft)")
                    insight["technologies"].append("AutoGen")
                if "crewai" in text_to_analyze or "crew ai" in text_to_analyze:
                    tech_keywords["frameworks"].add("CrewAI")
                if "langgraph" in text_to_analyze or "lang graph" in text_to_analyze:
                    tech_keywords["frameworks"].add("LangGraph (stateful agents)")
                    insight["technologies"].append("LangGraph")
                if "instructor" in text_to_analyze and "pydantic" in text_to_analyze: 
                    tech_keywords["frameworks"].add("Instructor (structured outputs)")
                if "guidance" in text_to_analyze and "microsoft" in text_to_analyze:
                    tech_keywords["frameworks"].add("Guidance (Microsoft)")
                if "lmstudio" in text_to_analyze or "lm studio" in text_to_analyze:
                    tech_keywords["frameworks"].add("LM Studio")
                if "vllm" in text_to_analyze:
                    tech_keywords["frameworks"].add("vLLM (fast inference)")
                    insight["technologies"].append("vLLM")
                    
                # Vector databases
                if "qdrant" in text_to_analyze: 
                    tech_keywords["databases"].add("Qdrant")
                    insight["technologies"].append("Qdrant")
                if "pinecone" in text_to_analyze: 
                    tech_keywords["databases"].add("Pinecone")
                    insight["technologies"].append("Pinecone")
                if "weaviate" in text_to_analyze: 
                    tech_keywords["databases"].add("Weaviate")
                    insight["technologies"].append("Weaviate")
                if "chroma" in text_to_analyze or "chromadb" in text_to_analyze: 
                    tech_keywords["databases"].add("ChromaDB")
                if "pgvector" in text_to_analyze or "pg_vector" in text_to_analyze: 
                    tech_keywords["databases"].add("pgvector (PostgreSQL)")
                    insight["technologies"].append("pgvector")
                if "milvus" in text_to_analyze: 
                    tech_keywords["databases"].add("Milvus")
                if "faiss" in text_to_analyze: 
                    tech_keywords["databases"].add("FAISS (Meta)")
                if "vespa" in text_to_analyze:
                    tech_keywords["databases"].add("Vespa")
                if "elasticsearch" in text_to_analyze:
                    tech_keywords["databases"].add("Elasticsearch")
                if "redis" in text_to_analyze and "vector" in text_to_analyze:
                    tech_keywords["databases"].add("Redis Stack (vector search)")
                    
                # Extract key contribution if not set
                if not insight["key_contribution"]:
                    # Try to find performance claims
                    if "improve" in text_to_analyze or "better" in text_to_analyze or "outperform" in text_to_analyze:
                        # Extract number if present
                        import re
                        numbers = re.findall(r'(\d+(?:\.\d+)?)\s*%', text_to_analyze)
                        if numbers:
                            insight["key_contribution"] = f"Performance improvement: {numbers[0]}%"
                        else:
                            insight["key_contribution"] = "Performance improvements demonstrated"
                    elif "novel" in text_to_analyze or "new" in text_to_analyze:
                        insight["key_contribution"] = "Novel approach or architecture"
                    else:
                        insight["key_contribution"] = paper.abstract[:150] + "..."
                
                if insight["technologies"] or insight["key_contribution"] != paper.abstract[:150] + "...":
                    paper_insights.append(insight)
            
            # Determine architecture from project brief
            brief_lower = document_brief.lower()
            architecture_choice = "Hybrid (RAG + LLM)"
            if "chatbot" in brief_lower or "conversation" in brief_lower:
                architecture_choice = "LLM with Memory"
            elif "knowledge" in brief_lower or "document" in brief_lower or "search" in brief_lower:
                architecture_choice = "RAG (Retrieval-Augmented Generation)"
            elif "agent" in brief_lower or "tool" in brief_lower:
                architecture_choice = "LLM Agents with Tools"
            
            # Build dynamic tech stack based on extracted technologies
            llm_models = list(tech_keywords["models"])[:6] if tech_keywords["models"] else ["GPT-4o (OpenAI)", "Claude 3.5 Sonnet"]
            frameworks_list = list(tech_keywords["frameworks"])[:6] if tech_keywords["frameworks"] else ["LangChain", "FastAPI"]
            vector_dbs = list(tech_keywords["databases"])[:4] if tech_keywords["databases"] else ["Qdrant", "Pinecone"]
            methods_list = list(tech_keywords["methods"])[:8]
            techniques_list = list(tech_keywords["techniques"])[:6]
            metrics_list = list(tech_keywords["metrics"])[:5]
            
            # Create detailed research insights
            research_insights = []
            for insight in paper_insights[:10]:  # Top 10 papers with meaningful insights
                research_insights.append(
                    f"[{insight['year']}] {insight['paper']} - {insight['key_contribution']}" + 
                    (f" (Uses: {', '.join(insight['technologies'][:3])})" if insight['technologies'] else "")
                )
            
            analysis = {
                "project_understanding": ["Analyzing project requirements and objectives"],
                "assumptions": [],
                "user_personas_and_use_cases": ["Primary users and their use cases"],
                "functional_requirements": {
                    "must_have": ["Core functionality based on project brief"],
                    "should_have": ["Additional features for enhanced experience"]
                },
                "non_functional_requirements": {
                    "latency": "Target response time < 3s",
                    "privacy": "Handle data according to requirements",
                    "scale": "Scale based on user base",
                    "cost": "Optimize for cost-effectiveness"
                },
                "architecture_decision": {
                    "choice": architecture_choice,
                    "reasoning": f"Based on project requirements and research findings: {', '.join(list(tech_keywords['methods'])[:3])}"
                },
                "system_design": {
                    "components": ["Ingestion Pipeline", "Vector Store", "Retrieval Engine", "LLM API", "Backend API", "Frontend UI"],
                    "data_flow": [
                        "1. Ingest and preprocess documents",
                        "2. Generate embeddings and store in vector DB",
                        "3. On query: retrieve relevant context",
                        "4. Augment with LLM for generation",
                        "5. Return response with citations"
                    ]
                },
                "research_digest": {
                    "key_notes": [
                        f"📊 Analyzed {len(papers)} LATEST papers ({len([p for p in papers if p.year >= 2024])} from 2024-2026)",
                        f"🔬 Key methodologies: {', '.join(methods_list[:4])}" if methods_list else "Modern AI/ML approaches",
                        f"🤖 State-of-art models: {', '.join(list(tech_keywords['models'])[:4])}" if tech_keywords['models'] else "Latest LLM architectures",
                        f"🛠️ Popular frameworks: {', '.join(list(tech_keywords['frameworks'])[:4])}" if tech_keywords['frameworks'] else "Emerging AI frameworks",
                        f"💾 Vector databases: {', '.join(vector_dbs[:3])}" if vector_dbs else "Modern vector storage solutions",
                        f"🎯 Advanced techniques: {', '.join(techniques_list[:4])}" if techniques_list else "State-of-art methods",
                        f"📈 Evaluation metrics: {', '.join(metrics_list[:4])}" if metrics_list else "Standard evaluation approaches"
                    ],
                    "paper_insights": research_insights if research_insights else ["Papers analyzed for latest techniques"],
                    "novel_techniques": methods_list + techniques_list if (methods_list or techniques_list) else ["Transformer-based architectures", "Retrieval-augmented approaches"],
                    "specific_models": list(tech_keywords["models"])[:8] if tech_keywords["models"] else ["GPT-4o", "Claude 3.5"],
                    "latest_findings": [
                        f"Papers span {min(p.year for p in papers) if papers else 2023}-{max(p.year for p in papers) if papers else 2026}",
                        f"Emerging patterns: {', '.join(methods_list[:3])}" if len(methods_list) >= 3 else "Modern AI/ML techniques",
                        f"Most cited tools: {', '.join(list(tech_keywords['frameworks'])[:3])}" if len(tech_keywords['frameworks']) >= 3 else "Leading frameworks"
                    ],
                    "evaluation_frameworks": list(tech_keywords["metrics"]) if tech_keywords["metrics"] else ["Custom evaluation metrics"]
                },
                "tech_stack": {
                    "llm_layer": llm_models if llm_models else ["GPT-4o (OpenAI)", "Claude 3.5 Sonnet (Anthropic)", "Llama 3.1 (open-source)"],
                    "retrieval_layer": (
                        ["text-embedding-3-large (OpenAI embeddings)"] + vector_dbs 
                        if ("rag" in brief_lower or "retrieval" in brief_lower or "knowledge" in brief_lower) 
                        else []
                    ),
                    "data_stores": ["PostgreSQL with pgvector extension", "Redis Stack (caching)", "MinIO or S3 (document storage)"],
                    "backend": (frameworks_list if frameworks_list else []) + ["FastAPI (Python 3.12)", "Uvicorn (ASGI server)"],
                    "frontend": (
                        ["Next.js 14+ with App Router", "React 18", "Tailwind CSS", "shadcn/ui components"] 
                        if any(word in brief_lower for word in ["ui", "frontend", "web", "interface", "dashboard"]) 
                        else ["REST API endpoints only"]
                    ),
                    "tools_libraries": list(set(frameworks_list + ["Pydantic v2", "Instructor (structured outputs)", "LiteLLM (multi-provider)"][:4])),
                    "evaluation": ["RAGAS (RAG evaluation)", "LangSmith (tracing)", "Custom eval suite", "A/B testing framework"]
                },
                "milestones": {
                    "mvp": "Basic ingestion and retrieval (Week 1-2)",
                    "v1": "Full pipeline with LLM integration (Week 3-4)",
                    "v2": "Advanced features and optimization (Week 5-6)"
                },
                "risks_and_mitigations": [
                    {"risk": "LLM API costs", "mitigation": "Implement caching and rate limiting"},
                    {"risk": "Latency issues", "mitigation": "Optimize retrieval and use async processing"}
                ],
                "next_steps": [
                    "Set up development environment",
                    "Implement document ingestion pipeline",
                    "Configure vector database",
                    "Build retrieval mechanism",
                    "Integrate LLM for generation"
                ]
            }
        
        # Add research papers to digest with FULL details
        research_digest = {
            "papers_analyzed": [
                {
                    "title": p.title,
                    "authors": p.authors[:3] if len(p.authors) > 3 else p.authors,  # First 3 authors
                    "year": p.year,
                    "url": p.url,
                    "abstract": p.abstract[:300] + "..." if len(p.abstract) > 300 else p.abstract,
                    "source": p.source.upper(),
                    "relevance_score": round(p.relevance_score, 2) if hasattr(p, 'relevance_score') else 0.0
                }
                for p in papers[:15]  # Include top 15 papers
            ],
            "arxiv_papers": [
                {
                    "title": p.title,
                    "year": p.year,
                    "url": p.url,
                    "key_idea": p.abstract[:200] + "...",
                    "project_takeaway": f"Relevant for {keywords.get('problem_domain', 'implementation')}"
                }
                for p in papers if p.source == "arxiv"
            ],
            "openreview_papers": [
                {
                    "title": p.title,
                    "year": p.year,
                    "url": p.url,
                    "key_idea": p.abstract[:200] + "...",
                    "project_takeaway": "Evaluation insights"
                }
                for p in papers if p.source == "openreview"
            ],
            "key_notes": analysis.get("research_digest", {}).get("key_notes", []),
            "paper_insights": analysis.get("research_digest", {}).get("paper_insights", []),
            "novel_techniques": analysis.get("research_digest", {}).get("novel_techniques", []),
            "specific_models": analysis.get("research_digest", {}).get("specific_models", []),
            "latest_findings": analysis.get("research_digest", {}).get("latest_findings", []),
            "evaluation_frameworks": analysis.get("research_digest", {}).get("evaluation_frameworks", [])
        }
        
        return CopilotResponse(
            project_name=project_name,
            arxiv_papers=[p for p in papers if p.source == "arxiv"],
            project_understanding=analysis.get("project_understanding", []),
            assumptions=analysis.get("assumptions", []),
            user_personas_and_use_cases=analysis.get("user_personas_and_use_cases", []),
            functional_requirements=analysis.get("functional_requirements", {}),
            non_functional_requirements=analysis.get("non_functional_requirements", {}),
            architecture_decision=analysis.get("architecture_decision", {}),
            system_design=analysis.get("system_design", {}),
            research_digest=research_digest,
            tech_stack=analysis.get("tech_stack", {}),
            milestones=analysis.get("milestones", {}),
            risks_and_mitigations=analysis.get("risks_and_mitigations", []),
            next_steps=analysis.get("next_steps", [])
        )
        
    except Exception as e:
        logger.error(f"Analysis generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# ============================================================================
# API ENDPOINT
# ============================================================================

@router.post("/analyze", response_model=CopilotResponse)
async def analyze_project(request: CopilotRequest):
    """
    Research Copilot Pipeline: Project Brief → Comprehensive Analysis
    
    Steps:
    1. Extract keywords/topics from document brief
    2. Search arXiv API for relevant papers
    3. Search OpenReview & AI/ML sites
    4. Rank papers by relevance
    5. Generate comprehensive 12-section analysis
    """
    
    try:
        logger.info(f"🤖 Starting analysis for: {request.project_name}")
        
        # Step 0: Extract keywords first (to get project hash)
        logger.info("Step 0/5: Extracting project-specific keywords")
        keywords = await extract_keywords_and_topics(request.project_brief)
        project_hash = keywords.get("project_hash", "")
        
        logger.info(f"   🔑 Project Hash: {project_hash[:8]}")
        logger.info(f"   🎯 Keywords: {', '.join(keywords.get('keywords', [])[:5])}")
        
        # Step 1: Search arXiv API for LATEST papers
        logger.info(f"Step 1/5: Searching arXiv for LATEST papers on: {', '.join(keywords.get('keywords', [])[:5])}")
        arxiv_papers = await search_arxiv(keywords.get("keywords", []))
        logger.info(f"🔍 Found {len(arxiv_papers)} papers from arXiv (2023-2026)")
        
        # Step 2: Search other AI/ML sites
        logger.info("Step 2/5: Searching OpenReview and AI/ML research sites")
        other_papers = await search_ai_ml_sites(keywords.get("keywords", []))
        
        # Combine all sources
        all_papers = arxiv_papers + other_papers
        
        logger.info(f"📚 Total papers found: {len(all_papers)}")
        
        # Step 3: Rank papers by relevance
        logger.info("Step 3/5: Ranking papers by relevance to project")
        ranked_papers = await rank_papers_by_relevance(
            all_papers,
            request.project_brief,
            keywords.get("keywords", [])
        )
        
        # Step 4: Generate comprehensive analysis
        logger.info("Step 4/5: Generating comprehensive 12-section analysis")
        analysis = await generate_comprehensive_analysis(
            project_name=request.project_name,
            document_brief=request.project_brief,
            keywords=keywords,
            papers=ranked_papers
        )
        
        logger.info(f"✅ Analysis complete for: {request.project_name}")
        return analysis
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Project Research Copilot",
        "pipeline": [
            "1. Extract keywords/topics",
            "2. Search arXiv",
            "3. Search OpenReview & AI/ML sites",
            "4. Rank papers",
            "5. Generate 12-section analysis"
        ]
    }
