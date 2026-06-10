"""
Claim extraction prompts - structured templates for LLM-based extraction
"""

CLAIM_EXTRACTION_PROMPT = """You are analyzing a research document about RAG (Retrieval-Augmented Generation) systems.

Your task is to extract all empirical claims from this document that are backed by evidence.

DOCUMENT:
---
{document_text}
---

INSTRUCTIONS:
1. Extract only claims that have supporting evidence in the document
2. Each claim must be specific and actionable
3. Include the exact location (section/figure/table) where evidence is found
4. Assign confidence based on strength of evidence

For each claim, provide a JSON object with these exact fields:

- claim_text: The specific assertion (one clear sentence, max 200 chars)
- evidence_type: One of [experiment, benchmark, case_study, theoretical, anecdotal]
- evidence_location: Exact section/figure/table reference (e.g., "Section 3.2", "Figure 4", "Table 2")
- metrics: Quantitative results if any (e.g., {{"recall_improvement": "+18%", "latency": "250ms"}})
- conditions: Under what conditions does this claim hold? (e.g., "For technical documentation with avg doc length >2000 tokens")
- limitations: What caveats or constraints apply? (e.g., "Only tested on English text", "Requires GPU inference")
- rag_applicability: Primary RAG component - one of [retrieval, chunking, embedding, reranking, generation, evaluation, other]
- confidence_score: Float 0.0-1.0 based on evidence strength

EVIDENCE STRENGTH GUIDELINES:
- 0.9-1.0: Controlled experiment with statistical significance, multiple benchmarks
- 0.7-0.9: Single benchmark with clear metrics, reproducible setup
- 0.5-0.7: Case study with qualitative results, limited scope
- 0.3-0.5: Theoretical claim with reasoning but no empirical validation
- 0.0-0.3: Anecdotal observation, marketing claim

EXAMPLE OUTPUT FORMAT:
```json
[
  {{
    "claim_text": "Semantic chunking improves retrieval recall by 18% vs fixed-size chunks for technical docs",
    "evidence_type": "experiment",
    "evidence_location": "Section 4.2, Table 3",
    "metrics": {{"recall_improvement": "+18%", "baseline": "fixed_512"}},
    "conditions": "Technical documentation, avg doc length 2000+ tokens, domain-specific queries",
    "limitations": "Only tested on English technical docs, single dataset",
    "rag_applicability": "chunking",
    "confidence_score": 0.85
  }}
]
```

CRITICAL RULES:
- Do NOT extract claims without evidence pointers
- Do NOT include marketing statements without empirical backing
- Do NOT combine multiple claims into one
- If no valid claims found, return empty array []

Return ONLY the JSON array, no additional text.
"""

CLAIM_VALIDATION_PROMPT = """You are validating an extracted claim from a RAG research document.

ORIGINAL DOCUMENT EXCERPT:
---
{document_excerpt}
---

EXTRACTED CLAIM:
{claim_json}

VALIDATION TASKS:
1. Verify the claim is accurately extracted from the document
2. Check if evidence location is correct
3. Assess if confidence score is appropriate
4. Identify any issues

Return a JSON object with:
- is_valid: boolean (true if claim is accurate and well-supported)
- issues: array of strings (any problems found, empty if none)
- suggested_confidence: float 0.0-1.0 (your recommended confidence score)
- suggested_edits: object with any field corrections needed (empty if none)

EXAMPLE OUTPUT:
```json
{{
  "is_valid": true,
  "issues": [],
  "suggested_confidence": 0.85,
  "suggested_edits": {{}}
}}
```

OR if there are issues:
```json
{{
  "is_valid": false,
  "issues": ["Evidence location not found in document", "Confidence score too high for anecdotal evidence"],
  "suggested_confidence": 0.4,
  "suggested_edits": {{
    "evidence_location": "Section 5.1",
    "confidence_score": 0.4
  }}
}}
```

Return ONLY the JSON object, no additional text.
"""

CONFLICT_DETECTION_PROMPT = """You are comparing multiple claims about RAG systems to detect conflicts.

CLAIM A:
{claim_a}

CLAIM B:
{claim_b}

Determine if these claims conflict with each other.

CONFLICT TYPES:
- Direct contradiction: Claims make opposite assertions
- Incompatible conditions: Claims about same technique give different results under similar conditions
- Methodology disagreement: Different experimental conclusions about same approach

Return JSON:
```json
{{
  "has_conflict": boolean,
  "conflict_type": "direct_contradiction | incompatible_conditions | methodology_disagreement | no_conflict",
  "explanation": "Brief explanation of conflict or why no conflict",
  "severity": "high | medium | low"
}}
```

Return ONLY the JSON object.
"""

RECOMMENDATION_GENERATION_PROMPT = """You are a RAG system architect generating research-backed recommendations.

PROJECT CONTEXT:
{project_context}

RELEVANT RESEARCH CLAIMS (sorted by relevance and credibility):
{claims_json}

TASK:
Generate specific, actionable recommendations for this RAG project based on the research evidence.

REQUIREMENTS:
1. Each recommendation must cite specific claims
2. Prioritize based on impact and applicability
3. Include implementation guidance
4. Acknowledge limitations and trade-offs
5. Structure by RAG component (chunking, retrieval, reranking, etc.)

OUTPUT FORMAT:
```json
{{
  "summary": "2-3 sentence executive summary of key recommendations",
  "recommendations": [
    {{
      "technique": "Specific technique name",
      "component": "chunking | retrieval | embedding | reranking | generation | evaluation",
      "description": "What this technique does",
      "rationale": "Why it's recommended for this project based on evidence",
      "supporting_claim_ids": ["uuid1", "uuid2"],
      "implementation_priority": "high | medium | low",
      "estimated_impact": "High: +15-20% recall improvement (based on Claim X)",
      "implementation_notes": "Specific steps or considerations",
      "trade_offs": "What to watch out for",
      "when_to_apply": "Specific conditions when this is most beneficial"
    }}
  ],
  "avoid": [
    {{
      "technique": "What NOT to do",
      "reason": "Why to avoid based on evidence",
      "supporting_claim_ids": ["uuid3"]
    }}
  ],
  "monitoring_recommendations": [
    "What metrics to track",
    "How to evaluate success"
  ]
}}
```

CRITICAL RULES:
- Every recommendation MUST cite at least one claim_id
- Prioritize high-confidence claims (>0.7)
- Consider project constraints (budget, latency, scale)
- Be specific and actionable, not generic advice
- Acknowledge when evidence is limited

Return ONLY the JSON object.
"""


def get_claim_extraction_prompt(document_text: str) -> str:
    """Get formatted claim extraction prompt"""
    return CLAIM_EXTRACTION_PROMPT.format(document_text=document_text)


def get_validation_prompt(document_excerpt: str, claim_json: str) -> str:
    """Get formatted validation prompt"""
    return CLAIM_VALIDATION_PROMPT.format(
        document_excerpt=document_excerpt,
        claim_json=claim_json
    )


def get_conflict_detection_prompt(claim_a: dict, claim_b: dict) -> str:
    """Get formatted conflict detection prompt"""
    import json
    return CONFLICT_DETECTION_PROMPT.format(
        claim_a=json.dumps(claim_a, indent=2),
        claim_b=json.dumps(claim_b, indent=2)
    )


def get_recommendation_prompt(project_context: dict, claims: list) -> str:
    """Get formatted recommendation generation prompt"""
    import json
    return RECOMMENDATION_GENERATION_PROMPT.format(
        project_context=json.dumps(project_context, indent=2),
        claims_json=json.dumps(claims, indent=2)
    )
