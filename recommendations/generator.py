"""
Recommendation generator - produces actionable recommendations with citations
"""
from typing import List, Dict, Any
import json
import time
from sqlalchemy.orm import Session
from loguru import logger

from prompts.extraction_prompts import get_recommendation_prompt
from utils.llm_client import LLMClient
from config import get_settings

settings = get_settings()


class RecommendationGenerator:
    """Generates research-backed recommendations from claims"""
    
    def __init__(self, db: Session):
        self.db = db
        self.llm = LLMClient()
    
    async def generate(
        self,
        claims: List[Dict],
        context: Any  # ProjectContext pydantic model
    ) -> Dict[str, Any]:
        """
        Generate recommendations from reranked claims
        
        Returns complete recommendation response
        """
        start_time = time.time()
        
        # Prepare claims for prompt (remove embeddings, etc.)
        clean_claims = self._prepare_claims_for_prompt(claims)
        
        # Generate prompt
        prompt = get_recommendation_prompt(
            project_context=context.dict(),
            claims=clean_claims
        )
        
        # Generate with LLM
        response_text = await self.llm.complete(
            prompt=prompt,
            temperature=0.1,
            max_tokens=4000
        )
        
        # Parse response
        try:
            response_json = self._parse_json_response(response_text)
            
            # Validate structure
            self._validate_response(response_json)
            
            # Add metadata
            response_json["project_context"] = context.dict()
            response_json["retrieval_metrics"] = {
                "total_claims_retrieved": len(claims),
                "vector_search_weight": settings.vector_search_weight,
                "keyword_search_weight": settings.keyword_search_weight
            }
            response_json["llm_model"] = settings.llm_model
            response_json["response_time_ms"] = int((time.time() - start_time) * 1000)
            
            # Build citations list
            response_json["citations"] = self._build_citations(claims)
            
            logger.info(f"Generated {len(response_json.get('recommendations', []))} recommendations")
            return response_json
            
        except Exception as e:
            logger.error(f"Failed to parse recommendation response: {e}")
            
            # Fallback response
            return {
                "project_context": context,
                "summary": "Unable to generate recommendations. Please check logs.",
                "recommendations": [],
                "citations": [],
                "retrieval_metrics": {},
                "error": str(e)
            }
    
    def _prepare_claims_for_prompt(self, claims: List[Dict]) -> List[Dict]:
        """Clean claims for prompt (remove binary data, etc.)"""
        clean_claims = []
        
        for claim in claims:
            clean_claim = {
                "id": str(claim["id"]),
                "claim_text": claim["claim_text"],
                "evidence_type": claim["evidence_type"],
                "evidence_location": claim.get("evidence_location"),
                "metrics": claim.get("metrics"),
                "conditions": claim.get("conditions"),
                "limitations": claim.get("limitations"),
                "rag_applicability": claim["rag_applicability"],
                "confidence_score": claim["confidence_score"],
                "source_title": claim.get("source_title"),
                "source_tier": claim.get("source_tier"),
                "rerank_score": claim.get("rerank_score")
            }
            clean_claims.append(clean_claim)
        
        return clean_claims
    
    def _parse_json_response(self, response_text: str) -> Dict:
        """Parse JSON from LLM response"""
        # Remove markdown code blocks
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        return json.loads(response_text)
    
    def _validate_response(self, response: Dict):
        """Validate response structure"""
        required_fields = ["summary", "recommendations"]
        
        for field in required_fields:
            if field not in response:
                raise ValueError(f"Missing required field: {field}")
        
        if not isinstance(response["recommendations"], list):
            raise ValueError("Recommendations must be a list")
    
    def _build_citations(self, claims: List[Dict]) -> List[Dict[str, str]]:
        """Build citation list from claims"""
        citations = []
        seen_urls = set()
        
        for claim in claims:
            url = claim.get("source_url")
            if url and url not in seen_urls:
                citations.append({
                    "url": url,
                    "title": claim.get("source_title", "Unknown"),
                    "tier": claim.get("source_tier", "unknown")
                })
                seen_urls.add(url)
        
        return citations
