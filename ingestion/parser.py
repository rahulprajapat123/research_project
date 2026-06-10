"""
Document parser - handles PDF and HTML parsing
"""
from typing import Optional, Dict, Any
import io
import pypdf
import pdfplumber
from bs4 import BeautifulSoup
from loguru import logger


class DocumentParser:
    """Unified document parser for multiple formats"""
    
    @staticmethod
    def parse_pdf(file_content: bytes) -> Dict[str, Any]:
        """
        Parse PDF document to extract text and metadata
        
        Returns:
            Dict with 'text', 'metadata', and 'page_count'
        """
        try:
            # Try pdfplumber first (better for tables)
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                text_parts = []
                
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                
                full_text = "\n\n".join(text_parts)
                
                # Get metadata
                metadata = pdf.metadata or {}
                
                return {
                    "text": full_text,
                    "metadata": {
                        "title": metadata.get("Title", ""),
                        "author": metadata.get("Author", ""),
                        "creator": metadata.get("Creator", ""),
                        "producer": metadata.get("Producer", ""),
                        "creation_date": metadata.get("CreationDate", "")
                    },
                    "page_count": len(pdf.pages),
                    "parser": "pdfplumber"
                }
                
        except Exception as e:
            logger.warning(f"pdfplumber failed, trying pypdf: {e}")
            
            try:
                # Fallback to pypdf
                pdf = pypdf.PdfReader(io.BytesIO(file_content))
                text_parts = []
                
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                
                full_text = "\n\n".join(text_parts)
                
                metadata = pdf.metadata or {}
                
                return {
                    "text": full_text,
                    "metadata": {
                        "title": metadata.get("/Title", ""),
                        "author": metadata.get("/Author", ""),
                        "creator": metadata.get("/Creator", ""),
                        "producer": metadata.get("/Producer", "")
                    },
                    "page_count": len(pdf.pages),
                    "parser": "pypdf"
                }
                
            except Exception as e2:
                logger.error(f"PDF parsing completely failed: {e2}")
                raise ValueError(f"Failed to parse PDF: {e2}")
    
    @staticmethod
    def parse_html(html_content: str) -> Dict[str, Any]:
        """
        Parse HTML document to extract text and metadata
        
        Returns:
            Dict with 'text', 'metadata'
        """
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Extract text
            text = soup.get_text(separator="\n", strip=True)
            
            # Extract metadata
            metadata = {}
            
            # Title
            if soup.title:
                metadata["title"] = soup.title.string
            
            # Meta tags
            for meta in soup.find_all("meta"):
                name = meta.get("name", meta.get("property", ""))
                content = meta.get("content", "")
                
                if name and content:
                    metadata[name] = content
            
            # Look for author in common patterns
            author_tag = soup.find("meta", {"name": "author"}) or \
                        soup.find("meta", {"property": "article:author"})
            
            if author_tag:
                metadata["author"] = author_tag.get("content", "")
            
            return {
                "text": text,
                "metadata": metadata,
                "parser": "beautifulsoup"
            }
            
        except Exception as e:
            logger.error(f"HTML parsing failed: {e}")
            raise ValueError(f"Failed to parse HTML: {e}")
    
    @staticmethod
    def parse_text(text_content: str) -> Dict[str, Any]:
        """
        Parse plain text document
        
        Returns:
            Dict with 'text'
        """
        return {
            "text": text_content.strip(),
            "metadata": {},
            "parser": "plain_text"
        }
    
    @classmethod
    def parse(cls, file_content: bytes, file_type: str) -> Dict[str, Any]:
        """
        Unified parse method that routes to appropriate parser
        
        Args:
            file_content: Raw file bytes
            file_type: 'pdf', 'html', or 'txt'
        
        Returns:
            Parsed document dict
        """
        if file_type == "pdf":
            return cls.parse_pdf(file_content)
        elif file_type == "html":
            return cls.parse_html(file_content.decode('utf-8', errors='ignore'))
        elif file_type == "txt":
            return cls.parse_text(file_content.decode('utf-8', errors='ignore'))
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
