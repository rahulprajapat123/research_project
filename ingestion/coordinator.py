"""
Ingestion coordinator - orchestrates the full document processing pipeline
"""
from typing import Optional, List
from datetime import date
from uuid import UUID, uuid4
import httpx
import json
from sqlalchemy.orm import Session
from sqlalchemy import text
from loguru import logger

from ingestion.parser import DocumentParser
from normalization.claim_extractor import ClaimExtractor
from utils.storage_client import StorageClient
from config import get_settings

settings = get_settings()


class IngestCoordinator:
    """Coordinates document ingestion pipeline"""
    
    def __init__(self, db: Session):
        self.db = db
        self.parser = DocumentParser()
        self.claim_extractor = ClaimExtractor()
        self.storage = StorageClient()
    
    def create_source_entry(
        self,
        url: str,
        title: Optional[str],
        authors: Optional[List[str]],
        publication_date: Optional[date],
        source_type: str,
        tier: str,
        credibility_score: int,
        citation_count: Optional[int],
        author_h_index: Optional[int],
        metadata: dict
    ) -> UUID:
        """Create initial source entry in database"""
        
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        
        source_id = uuid4()
        
        self.db.execute(
            text("""
                INSERT INTO sources 
                 (id, url, title, authors, publication_date, source_type, domain, 
                 tier, credibility_score, citation_count, author_h_index, metadata, 
                 ingestion_status)
                VALUES 
                (:id, :url, :title, :authors, :pub_date, :source_type, :domain,
                 :tier, :cred_score, :citation_count, :h_index, :metadata::jsonb, 'pending')
            """),
            {
                "id": str(source_id),
                "url": url,
                "title": title,
                "authors": authors,
                "pub_date": publication_date,
                "source_type": source_type,
                "domain": domain,
                "tier": tier,
                "cred_score": credibility_score,
                "citation_count": citation_count,
                "h_index": author_h_index,
                "metadata": json.dumps(metadata)
            }
        )
        self.db.commit()
        
        logger.info(f"Created source entry: {source_id}")
        return source_id
    
    async def process_document_pipeline(self, source_id: UUID):
        """
        Full processing pipeline:
        1. Download document
        2. Store in object storage
        3. Parse to text
        4. Extract claims
        5. Queue for validation
        """
        try:
            # Update status
            self._update_source_status(source_id, "processing")
            
            # Get source info
            source = self._get_source(source_id)
            
            # Step 1: Download document
            logger.info(f"Downloading document: {source['url']}")
            file_content = await self._download_document(source["url"])
            
            # Step 2: Store in object storage
            file_type = self._detect_file_type(source["url"])
            if file_type not in settings.allowed_file_types_list:
                raise ValueError(f"File type not allowed: {file_type}")
            
            max_bytes = settings.max_document_size_mb * 1024 * 1024
            if len(file_content) > max_bytes:
                raise ValueError(f"Document exceeds max size: {len(file_content)} bytes")
            
            storage_url = self.storage.upload(
                file_content,
                f"sources/{source_id}.{file_type}"
            )
            
            self.db.execute(
                text("""
                    UPDATE sources 
                    SET raw_file_url = :url, raw_file_size_bytes = :size
                    WHERE id = :id
                """),
                {
                    "url": storage_url,
                    "size": len(file_content),
                    "id": str(source_id)
                }
            )
            self.db.commit()
            
            # Step 3: Parse document
            logger.info(f"Parsing document: {source_id}")
            parsed = self.parser.parse(file_content, file_type)
            
            self.db.execute(
                text("UPDATE sources SET parsed_text = :text WHERE id = :id"),
                {"text": parsed["text"], "id": str(source_id)}
            )
            self.db.commit()
            
            # Step 4: Extract claims
            logger.info(f"Extracting claims from: {source_id}")
            claims = await self.claim_extractor.extract_claims(
                document_text=parsed["text"],
                source_id=source_id,
                source_metadata={
                    "title": source.get("title"),
                    "url": source["url"],
                    "tier": source["tier"]
                }
            )
            
            # Store claims
            for claim in claims:
                self._store_claim(claim, source_id)
            
            # Step 5: Queue for validation
            await self._queue_for_validation(source_id, claims)
            
            # Update to completed
            self._update_source_status(source_id, "completed")
            logger.info(f"✅ Pipeline completed for {source_id}: {len(claims)} claims extracted")
            
        except Exception as e:
            logger.error(f"Pipeline error for {source_id}: {e}", exc_info=True)
            self._update_source_status(source_id, "failed", error=str(e))
    
    async def _download_document(self, url: str) -> bytes:
        """Download document from URL"""
        async with httpx.AsyncClient(timeout=settings.parse_timeout_seconds) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            return response.content
    
    def _detect_file_type(self, url: str) -> str:
        """Detect file type from URL"""
        url_lower = url.lower()
        if ".pdf" in url_lower:
            return "pdf"
        elif ".html" in url_lower or ".htm" in url_lower:
            return "html"
        else:
            return "txt"
    
    def _get_source(self, source_id: UUID) -> dict:
        """Get source from database"""
        result = self.db.execute(
            text("SELECT * FROM sources WHERE id = :id"),
            {"id": str(source_id)}
        ).fetchone()
        
        if not result:
            raise ValueError(f"Source {source_id} not found")
        
        return {
            "id": result[0],
            "url": result[1],
            "title": result[2],
            "tier": result[7]
        }
    
    def _update_source_status(
        self,
        source_id: UUID,
        status: str,
        error: Optional[str] = None
    ):
        """Update source ingestion status"""
        self.db.execute(
            text("""
                UPDATE sources 
                SET ingestion_status = :status, ingestion_error = :error
                WHERE id = :id
            """),
            {"status": status, "error": error, "id": str(source_id)}
        )
        self.db.commit()
    
    def _store_claim(self, claim: dict, source_id: UUID):
        """Store extracted claim in database"""
        claim_id = uuid4()
        
        self.db.execute(
            text("""
                INSERT INTO claims
                (id, source_id, claim_text, evidence_type, evidence_location,
                 metrics, conditions, limitations, rag_applicability, 
                 confidence_score, embedding)
                VALUES
                (:id, :source_id, :text, :evidence_type, :evidence_loc,
                 :metrics::jsonb, :conditions, :limitations, :applicability,
                 :confidence, :embedding::vector)
            """),
            {
                "id": str(claim_id),
                "source_id": str(source_id),
                "text": claim["claim_text"],
                "evidence_type": claim["evidence_type"],
                "evidence_loc": claim.get("evidence_location"),
                "metrics": json.dumps(claim.get("metrics", {})),
                "conditions": claim.get("conditions"),
                "limitations": claim.get("limitations"),
                "applicability": claim["rag_applicability"],
                "confidence": claim["confidence_score"],
                "embedding": self._format_embedding(claim.get("embedding"))
            }
        )
        self.db.commit()
        claim["claim_id"] = claim_id
        return claim_id
    
    async def _queue_for_validation(self, source_id: UUID, claims: List[dict]):
        """Queue claims for human validation based on sampling rules"""
        from normalization.validation_queue import ValidationQueue
        
        queue = ValidationQueue(self.db)
        await queue.enqueue_for_validation(source_id, claims)
        claim_ids = [claim.get("claim_id") for claim in claims if claim.get("claim_id")]
        await queue.send_validation_notification(claim_ids)

    @staticmethod
    def _format_embedding(embedding: Optional[List[float]]) -> Optional[str]:
        """Format embedding as pgvector literal string"""
        if embedding is None:
            return None
        return "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"
