"""Project brief parsing and deterministic insight extraction."""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List
from xml.etree import ElementTree

from pypdf import PdfReader


SUPPORTED_BRIEF_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}


class BriefParsingError(ValueError):
    """Raised when a brief cannot be parsed safely."""


@dataclass(frozen=True)
class ParsedBrief:
    file_name: str
    file_type: str
    content_text: str
    metadata: Dict[str, Any]


DOMAIN_KEYWORDS = {
    "AI/ML": {"llm", "machine learning", "deep learning", "neural network", "model training", "inference", "ai", "artificial intelligence"},
    "RAG": {"rag", "retrieval augmented", "semantic search", "vector search", "embedding", "knowledge retrieval"},
    "NLP": {"nlp", "natural language", "text processing", "translation", "transcription", "sentiment", "language model"},
    "translation/localization": {"translation", "transcreation", "localization", "locale", "multilingual", "reviewer", "quality review"},
    "market research": {"market research", "consumer sentiment", "social listening", "survey", "desk research", "qualitative", "voice of customer"},
    "mobile": {"mobile", "ios", "android", "app store", "flutter", "react native", "swift", "kotlin"},
    "web": {"web app", "website", "frontend", "backend", "full-stack", "spa", "pwa"},
    "data": {"data pipeline", "etl", "analytics", "data warehouse", "big data", "spark", "kafka"},
    "devops": {"devops", "ci/cd", "kubernetes", "docker", "deployment", "infrastructure", "cloud"},
    "blockchain": {"blockchain", "web3", "smart contract", "ethereum", "defi", "nft", "crypto"},
    "iot": {"iot", "embedded", "sensor", "arduino", "raspberry pi", "edge computing"},
    "game": {"game", "unity", "unreal", "gaming", "3d", "multiplayer"},
    "healthcare": {"medical", "clinical", "doctor", "patient", "healthcare", "ehr", "diagnosis", "telemedicine"},
    "legal": {"legal", "law", "contract", "compliance", "regulatory", "policy"},
    "finance": {"finance", "financial", "banking", "trading", "payments", "risk", "fintech"},
    "developer tooling": {"developer", "code", "repository", "github", "ci", "sdk", "api", "ide"},
    "enterprise knowledge": {"enterprise", "knowledge base", "document", "intranet", "support"},
    "education": {"student", "learning", "course", "education", "teacher", "e-learning"},
    "commerce": {"commerce", "retail", "product", "shopping", "marketplace", "ecommerce"},
    "security": {"security", "privacy", "soc", "threat", "vulnerability", "compliance", "cybersecurity"},
    "saas": {"saas", "subscription", "multi-tenant", "b2b", "platform"},
    "social": {"social media", "social network", "messaging", "chat", "community"},
    "media": {"video", "streaming", "media", "audio", "content delivery"},
}

TECH_TERMS = [
    "RAG",
    "retrieval augmented generation",
    "LLM",
    "agent",
    "agentic AI",
    "workflow automation",
    "semantic search",
    "vector database",
    "pgvector",
    "Pinecone",
    "Qdrant",
    "Weaviate",
    "Milvus",
    "FAISS",
    "LangChain",
    "LangGraph",
    "LlamaIndex",
    "DSPy",
    "OpenAI",
    "Claude",
    "Gemini",
    "Llama",
    "Mistral",
    "Cohere",
    "Hugging Face",
    "embedding",
    "reranking",
    "hybrid search",
    "knowledge graph",
    "PostgreSQL",
    "FastAPI",
    "Next.js",
    "React",
    "Celery",
    "APScheduler",
    "Redis",
    "Kubernetes",
    "observability",
    "evaluation",
    "RAGAS",
    "LangSmith",
]

CONSTRAINT_PATTERNS = [
    r"\bunder\s+\d+(?:\.\d+)?\s*(?:ms|milliseconds|s|sec|seconds|minutes?)\b",
    r"\b\d+(?:\.\d+)?\s*(?:ms|milliseconds|s|sec|seconds)\b",
    r"\b(?:budget|cost|latency|privacy|security|compliance|gdpr|hipaa|soc\s*2|scale|sla)\b[^.]{0,120}",
    r"\b(?:must|should|need(?:s)? to|require(?:s|d)?)\b[^.]{0,160}",
]

RISK_KEYWORDS = {
    "privacy and compliance": {"privacy", "compliance", "hipaa", "gdpr", "soc 2", "pii"},
    "latency": {"latency", "real-time", "under", "response time"},
    "hallucination": {"hallucination", "citation", "grounded", "evidence"},
    "cost": {"cost", "budget", "api spend", "token"},
    "scale": {"scale", "throughput", "concurrent", "millions"},
    "security": {"security", "secrets", "vulnerability", "access control"},
}


def validate_upload(file_name: str, content: bytes, max_size_mb: int) -> str:
    """Validate uploaded brief metadata and return the normalized extension."""
    extension = Path(file_name or "").suffix.lower()
    if extension not in SUPPORTED_BRIEF_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_BRIEF_EXTENSIONS))
        raise BriefParsingError(f"Unsupported file type '{extension or 'unknown'}'. Supported: {supported}")

    max_bytes = max_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise BriefParsingError(f"File exceeds {max_size_mb} MB upload limit")
    if not content:
        raise BriefParsingError("Uploaded file is empty")
    return extension.lstrip(".")


def parse_brief_file(file_name: str, content: bytes, max_size_mb: int = 20) -> ParsedBrief:
    """Parse PDF, TXT, MD, and DOCX project briefs into sanitized text."""
    file_type = validate_upload(file_name=file_name, content=content, max_size_mb=max_size_mb)
    extension = f".{file_type}"

    if extension == ".pdf":
        raw_text = _parse_pdf(content)
    elif extension == ".docx":
        raw_text = _parse_docx(content)
    else:
        raw_text = _parse_text(content)

    content_text = sanitize_text(raw_text)
    if len(content_text.strip()) < 20:
        raise BriefParsingError("Could not extract enough text from the uploaded brief")

    return ParsedBrief(
        file_name=file_name,
        file_type=file_type,
        content_text=content_text,
        metadata={
            "character_count": len(content_text),
            "word_count": len(content_text.split()),
        },
    )


def sanitize_text(text: str, max_chars: int = 300_000) -> str:
    """Remove control characters and cap text length before storage/LLM use."""
    cleaned = text.replace("\x00", " ")
    cleaned = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()[:max_chars]


def extract_brief_insights(content_text: str) -> Dict[str, Any]:
    """Extract product-facing brief fields plus compatibility fields used by scoring."""
    text = sanitize_text(content_text)
    text_lower = text.lower()
    sentences = _split_sentences(text)

    domain = _detect_domain(text_lower)
    stack = _detect_stack(text)
    constraints = _extract_constraints(text, sentences)
    goals = _extract_goals(sentences)
    problem_statement = _extract_problem_statement(sentences, goals)
    target_users = _extract_target_users(text, sentences)
    risks = _extract_risks(text_lower)
    requirements = _extract_requirements(sentences, stack, constraints)
    deliverables = _extract_deliverables(sentences)
    topics = _extract_topics(text, stack, domain, requirements)
    technical_keywords = _dedupe_preserve_order([*stack, *topics])

    confidence = 0.45
    if len(text.split()) > 120:
        confidence += 0.15
    if stack:
        confidence += 0.15
    if goals:
        confidence += 0.1
    if constraints:
        confidence += 0.1
    confidence = min(confidence, 0.95)

    return {
        "problem_statement": problem_statement,
        "domain": domain,
        "industry": domain,
        "goals": goals,
        "constraints": constraints,
        "target_users": target_users,
        "stack": stack,
        "risks": risks,
        "requirements": requirements,
        "technical_requirements": requirements,
        "technical_keywords": technical_keywords,
        "expected_deliverables": deliverables,
        "key_topics": topics,
        "confidence_score": round(confidence, 3),
    }


def build_search_terms(insights: Dict[str, Any], max_terms: int = 10) -> List[str]:
    """Build source-search terms from extracted brief insight fields."""
    candidates: List[str] = []

    problem_statement = insights.get("problem_statement")
    if problem_statement:
        candidates.extend(_candidate_phrases(str(problem_statement))[:2])

    # Prioritize technical stack mentions and explicit keywords.
    stack = insights.get("stack", [])
    if isinstance(stack, list):
        candidates.extend(str(item) for item in stack[:5])

    technical_keywords = insights.get("technical_keywords", [])
    if isinstance(technical_keywords, list):
        candidates.extend(str(item) for item in technical_keywords[:8])

    # Add key topics (most relevant)
    key_topics = insights.get("key_topics", [])
    if isinstance(key_topics, list):
        candidates.extend(str(item) for item in key_topics[:8])

    # Add domain for context
    domain = insights.get("domain")
    if domain and domain != "general":
        candidates.append(str(domain))

    # Add select technical requirements
    requirements = insights.get("requirements") or insights.get("technical_requirements", [])
    if isinstance(requirements, list):
        # Extract noun phrases from requirements
        for req in requirements[:3]:
            candidates.extend(_candidate_phrases(str(req))[:1])

    # Normalize and deduplicate
    normalized: List[str] = []
    seen = set()
    for term in candidates:
        cleaned = re.sub(r"\s+", " ", term).strip()
        # Filter out non-technical terms
        if len(cleaned) < 3:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
    
    # Better fallback terms that are more general but still technical
    fallback_terms = [
        "software architecture",
        "system design",
        "application development",
        "technology stack",
        "software engineering",
    ]
    
    result = normalized[:max_terms]
    if len(result) < 3:
        result.extend(fallback_terms[: max(3 - len(result), 0)])
    
    return result or fallback_terms[:max_terms]


def _parse_pdf(content: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)
    except Exception as exc:
        raise BriefParsingError(f"Could not parse PDF: {exc}") from exc


def _parse_docx(content: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            xml_payload = archive.read("word/document.xml")
    except Exception as exc:
        raise BriefParsingError(f"Could not read DOCX: {exc}") from exc

    try:
        root = ElementTree.fromstring(xml_payload)
    except ElementTree.ParseError as exc:
        raise BriefParsingError(f"Could not parse DOCX XML: {exc}") from exc

    paragraphs: List[str] = []
    current: List[str] = []
    for node in root.iter():
        if node.tag.endswith("}t") and node.text:
            current.append(node.text)
        elif node.tag.endswith("}p") and current:
            paragraphs.append("".join(current))
            current = []
    if current:
        paragraphs.append("".join(current))
    return "\n".join(paragraphs)


def _parse_text(content: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [part.strip(" -\t") for part in parts if len(part.strip()) > 10]


def _detect_domain(text_lower: str) -> str:
    scores = {
        domain: sum(1 for keyword in keywords if keyword in text_lower)
        for domain, keywords in DOMAIN_KEYWORDS.items()
    }
    best_domain, best_score = max(scores.items(), key=lambda item: item[1])
    return best_domain if best_score > 0 else "general"


def _detect_stack(text: str) -> List[str]:
    text_lower = text.lower()
    stack = []
    for term in TECH_TERMS:
        if re.search(rf"\b{re.escape(term.lower())}\b", text_lower):
            stack.append(term)
    return _dedupe_preserve_order(stack)


def _extract_constraints(text: str, sentences: List[str]) -> List[str]:
    constraints = []
    for pattern in CONSTRAINT_PATTERNS:
        constraints.extend(match.group(0).strip(" .") for match in re.finditer(pattern, text, flags=re.I))
    for sentence in sentences:
        if any(word in sentence.lower() for word in ("latency", "budget", "privacy", "secure", "scale", "compliance")):
            constraints.append(sentence[:220])
    return _dedupe_preserve_order(constraints)[:8]


def _extract_goals(sentences: List[str]) -> List[str]:
    markers = ("build", "create", "develop", "launch", "enable", "provide", "allow", "support", "want to")
    goals = [sentence[:240] for sentence in sentences if any(marker in sentence.lower() for marker in markers)]
    return _dedupe_preserve_order(goals)[:6]


def _extract_problem_statement(sentences: List[str], goals: List[str]) -> str:
    markers = (
        "problem",
        "challenge",
        "gap",
        "objective",
        "need",
        "goal",
        "aim",
        "pain",
        "difficulty",
    )
    for sentence in sentences:
        if any(marker in sentence.lower() for marker in markers):
            return sentence[:360]
    if goals:
        return goals[0][:360]
    return sentences[0][:360] if sentences else ""


def _extract_target_users(text: str, sentences: List[str]) -> List[str]:
    users = []
    patterns = [
        r"\bfor\s+([A-Za-z][A-Za-z0-9 ,/&-]{2,80})",
        r"\btarget users?\s*(?:are|:)?\s*([A-Za-z][A-Za-z0-9 ,/&-]{2,100})",
        r"\bused by\s+([A-Za-z][A-Za-z0-9 ,/&-]{2,80})",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.I):
            candidate = match.group(1).split(".")[0].strip(" ,")
            if candidate:
                users.append(candidate[:100])
    for sentence in sentences:
        lower = sentence.lower()
        if any(word in lower for word in ("admin", "developer", "analyst", "team", "user", "customer")):
            users.append(sentence[:180])
    return _dedupe_preserve_order(users)[:6] or ["Technical team"]


def _extract_risks(text_lower: str) -> List[str]:
    risks = [
        risk
        for risk, keywords in RISK_KEYWORDS.items()
        if any(keyword in text_lower for keyword in keywords)
    ]
    return _dedupe_preserve_order(risks)[:8]


def _extract_requirements(sentences: List[str], stack: List[str], constraints: List[str]) -> List[str]:
    requirements = []
    for sentence in sentences:
        lower = sentence.lower()
        if any(marker in lower for marker in ("must", "should", "need", "require", "support", "integrate")):
            requirements.append(sentence[:220])
    requirements.extend(f"Use or evaluate {term}" for term in stack[:6])
    requirements.extend(constraints[:3])
    return _dedupe_preserve_order(requirements)[:10]


def _extract_deliverables(sentences: List[str]) -> List[str]:
    deliverables = []
    markers = (
        "deliverable",
        "deliverables",
        "output",
        "report",
        "dashboard",
        "email",
        "api",
        "export",
        "written response",
        "analysis",
        "prototype",
        "document",
    )
    for sentence in sentences:
        lower = sentence.lower()
        if any(marker in lower for marker in markers):
            deliverables.append(sentence[:220])
    return _dedupe_preserve_order(deliverables)[:8]


def _extract_topics(text: str, stack: List[str], domain: str, requirements: List[str]) -> List[str]:
    text_lower = text.lower()
    topics = list(stack)
    
    # Comprehensive domain-specific technical topics
    domain_topics = {
        "AI/ML": ["machine learning", "neural networks", "model optimization", "training pipeline"],
        "RAG": ["retrieval augmented generation", "citation-backed retrieval", "semantic search", "vector embeddings"],
        "NLP": ["natural language processing", "text analysis", "language models", "sentiment analysis"],
        "mobile": ["mobile development", "cross-platform apps", "native development", "mobile UI/UX"],
        "web": ["web development", "responsive design", "api design", "web architecture"],
        "data": ["data engineering", "data processing", "real-time analytics", "data visualization"],
        "devops": ["continuous integration", "container orchestration", "infrastructure as code", "monitoring"],
        "blockchain": ["distributed ledger", "consensus mechanisms", "smart contracts", "decentralization"],
        "iot": ["sensor networks", "edge computing", "embedded systems", "real-time monitoring"],
        "game": ["game engine", "real-time rendering", "multiplayer networking", "game physics"],
        "enterprise knowledge": ["enterprise RAG", "knowledge base search", "document intelligence"],
        "developer tooling": ["code intelligence", "repository search", "developer automation", "code analysis"],
        "security": ["AI security", "privacy-preserving AI", "compliance automation", "threat detection"],
        "healthcare": ["clinical decision support", "medical AI", "evidence-based medicine", "health data"],
        "legal": ["legal AI", "contract analysis", "regulatory compliance", "legal research"],
        "finance": ["financial AI", "risk intelligence", "algorithmic trading", "fraud detection"],
        "education": ["adaptive learning", "educational technology", "learning analytics", "online education"],
        "commerce": ["recommendation systems", "search optimization", "inventory management", "customer analytics"],
        "saas": ["multi-tenancy", "scalability", "subscription management", "api-first design"],
        "social": ["social graphs", "content moderation", "real-time messaging", "user engagement"],
        "media": ["video processing", "content delivery", "streaming architecture", "media transcoding"],
    }
    topics.extend(domain_topics.get(domain, []))
    
    # Extract technical keywords from text
    technical_keywords = _extract_technical_keywords(text_lower)
    topics.extend(technical_keywords)
    
    # Common AI/tech phrases
    phrase_candidates = [
        "retrieval augmented generation",
        "semantic search",
        "vector embeddings",
        "hybrid search",
        "agentic workflow",
        "real-time processing",
        "scalable architecture",
        "cloud native",
        "microservices",
        "api-first",
        "serverless",
        "event-driven",
        "machine learning",
        "deep learning",
        "natural language",
        "computer vision",
        "recommendation engine",
        "personalization",
        "automation",
        "intelligent system",
    ]
    topics.extend(phrase for phrase in phrase_candidates if phrase in text_lower)
    
    # Extract meaningful phrases from requirements
    for requirement in requirements[:5]:
        words = re.findall(r"[A-Za-z][A-Za-z0-9+-]{2,}", requirement)
        if len(words) >= 2:
            topics.append(" ".join(words[:4]))
    
    # Add domain as fallback
    if domain and domain != "general":
        topics.append(domain)
    
    return _dedupe_preserve_order(topics)[:15] or ["software development", "system architecture", "technology stack"]


def _extract_technical_keywords(text_lower: str) -> List[str]:
    """Extract technical keywords and phrases from text using pattern matching."""
    keywords = []
    
    # Common technical patterns
    patterns = [
        r"\b(\w+\s+(?:api|sdk|framework|platform|service|system|engine|database|server))\b",
        r"\b((?:real-time|cloud-based|ai-powered|ml-based|data-driven)\s+\w+)\b",
        r"\b(\w+\s+(?:processing|analysis|optimization|automation|integration))\b",
        r"\b(\w+\s+(?:development|architecture|infrastructure|deployment))\b",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text_lower)
        keywords.extend(matches[:5])  # Limit per pattern
    
    return keywords[:10]


def _candidate_phrases(text: str) -> List[str]:
    stopwords = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "into",
        "must",
        "should",
        "need",
        "needs",
        "will",
        "can",
        "are",
        "was",
        "were",
        "have",
        "has",
        "our",
        "your",
    }
    words = [
        word
        for word in re.findall(r"[A-Za-z][A-Za-z0-9+-]{2,}", text)
        if word.lower() not in stopwords
    ]
    phrases = []
    if len(words) >= 4:
        phrases.append(" ".join(words[:4]))
    if len(words) >= 3:
        phrases.append(" ".join(words[:3]))
    if len(words) >= 2:
        phrases.append(" ".join(words[:2]))
    return phrases


def _dedupe_preserve_order(values: List[str]) -> List[str]:
    seen = set()
    deduped = []
    for value in values:
        cleaned = re.sub(r"\s+", " ", str(value)).strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return deduped
