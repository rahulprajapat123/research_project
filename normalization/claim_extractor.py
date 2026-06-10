"""
Claim extractor - LLM-based extraction with retries and validation
"""
from typing import List, Dict, Any, Optional
import json
from uuid import UUID
from loguru import logger

from prompts.extraction_prompts import get_claim_extraction_prompt
from utils.llm_client import LLMClient
from utils.embedding_client import EmbeddingClient
from config import get_settings

settings = get_settings()


class ClaimExtractor:
    """Extracts structured claims from research documents using LLM"""
    
    def __init__(self):
        self.llm = LLMClient()
        self.embedder = EmbeddingClient()
    
    async def extract_claims(
        self,
        document_text: str,
        source_id: UUID,
        source_metadata: dict
    ) -> List[Dict[str, Any]]:
        """
        Extract structured claims from document text
        
        Returns list of claim dictionaries with embeddings
        """
        # Truncate if too long (LLM context limits)
        max_length = 50000  # characters
        if len(document_text) > max_length:
            logger.warning(f"Document too long ({len(document_text)} chars), truncating to {max_length}")
            document_text = document_text[:max_length]
        
        prompt = get_claim_extraction_prompt(document_text)
        
        # Extract claims with retries
        claims = await self._extract_with_retries(prompt)
        
        if not claims:
            logger.warning(f"No claims extracted from source {source_id}")
            return []
        
        # Post-process and enrich claims
        enriched_claims = await self._enrich_claims(claims, source_metadata)
        
        # Generate embeddings
        claims_with_embeddings = await self._add_embeddings(enriched_claims)
        
        logger.info(f"Extracted {len(claims_with_embeddings)} claims from {source_id}")
        return claims_with_embeddings
    
    async def _extract_with_retries(self, prompt: str) -> List[Dict]:
        """Extract claims with retry logic for malformed responses"""
        max_retries = settings.claim_extraction_max_retries
        
        for attempt in range(max_retries):
            try:
                response = await self.llm.complete(
                    prompt=prompt,
                    temperature=settings.claim_extraction_temperature,
                    model=settings.claim_extraction_model
                )
                
                # Parse JSON
                claims = self._parse_json_response(response)
                
                # Validate structure
                valid_claims = self._validate_claims(claims)
                
                if valid_claims:
                    return valid_claims
                else:
                    logger.warning(f"Attempt {attempt + 1}: No valid claims in response")
                    
            except json.JSONDecodeError as e:
                logger.warning(f"Attempt {attempt + 1}: JSON parse error: {e}")
            except Exception as e:
                logger.error(f"Attempt {attempt + 1}: Extraction error: {e}")
        
        logger.error(f"Failed to extract claims after {max_retries} attempts")
        return []
    
    def _parse_json_response(self, response: str) -> List[Dict]:
        """Parse JSON from LLM response, handling markdown code blocks"""
        # Remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        
        response = response.strip()
        
        # Parse JSON
        claims = json.loads(response)
        
        if not isinstance(claims, list):
            raise ValueError("Response is not a JSON array")
        
        return claims
    
    def _validate_claims(self, claims: List[Dict]) -> List[Dict]:
        """Validate claim structure and filter out invalid ones"""
        required_fields = [
            "claim_text",
            "evidence_type",
            "rag_applicability",
            "confidence_score"
        ]
        
        valid_evidence_types = [
            "experiment", "benchmark", "case_study", "theoretical", "anecdotal"
        ]
        
        valid_applicabilities = [
            "retrieval", "chunking", "embedding", "reranking", 
            "generation", "evaluation", "other"
        ]
        
        valid_claims = []
        
        for claim in claims:
            # Check required fields
            if not all(field in claim for field in required_fields):
                logger.warning(f"Claim missing required fields: {claim}")
                continue
            
            # Validate evidence type
            if claim["evidence_type"] not in valid_evidence_types:
                logger.warning(f"Invalid evidence_type: {claim['evidence_type']}")
                continue
            
            # Validate RAG applicability
            if claim["rag_applicability"] not in valid_applicabilities:
                logger.warning(f"Invalid rag_applicability: {claim['rag_applicability']}")
                continue
            
            # Validate confidence score
            try:
                confidence = float(claim["confidence_score"])
                if not (0.0 <= confidence <= 1.0):
                    logger.warning(f"Confidence score out of range: {confidence}")
                    continue
            except (ValueError, TypeError):
                logger.warning(f"Invalid confidence_score: {claim['confidence_score']}")
                continue
            
            # Filter by minimum confidence
            if confidence < settings.min_claim_confidence:
                logger.debug(f"Claim below min confidence ({confidence}): {claim['claim_text'][:50]}")
                continue
            
            valid_claims.append(claim)
        
        return valid_claims
    
    async def _enrich_claims(
        self,
        claims: List[Dict],
        source_metadata: dict
    ) -> List[Dict]:
        """Add source context to claims"""
        for claim in claims:
            claim["source_title"] = source_metadata.get("title")
            claim["source_url"] = source_metadata.get("url")
            claim["source_tier"] = source_metadata.get("tier")
        
        return claims
    
    async def _add_embeddings(self, claims: List[Dict]) -> List[Dict]:
        """Generate embeddings for claims"""
        texts = [claim["claim_text"] for claim in claims]
        
        embeddings = await self.embedder.embed_batch(texts)
        
        for claim, embedding in zip(claims, embeddings):
            claim["embedding"] = embedding
        
        return claims
