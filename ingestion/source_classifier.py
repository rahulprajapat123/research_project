"""
Source classifier - determines tier and credibility score
"""
from typing import Tuple
from urllib.parse import urlparse
from config import SOURCE_TIERS, EXCLUDED_SOURCES, get_settings

settings = get_settings()


def classify_source_tier(
    url: str,
    citation_count: int = None,
    author_h_index: int = None
) -> Tuple[str, int]:
    """
    Classify source into tier and calculate credibility score
    
    Returns:
        Tuple of (tier, credibility_score)
    """
    domain = urlparse(url).netloc.lower()
    
    # Check if excluded
    for excluded in EXCLUDED_SOURCES:
        if excluded in domain:
            return "excluded", 0
    
    # Check tiers
    for tier_key, tier_info in SOURCE_TIERS.items():
        for source_pattern in tier_info["sources"]:
            if source_pattern in url.lower() or source_pattern in domain:
                base_score = tier_info["boost"]
                
                # Add citation boost for Tier 1
                if tier_key == "tier_1" and citation_count:
                    if citation_count >= settings.min_citation_count:
                        base_score += min(citation_count // 10, 20)  # Cap at +20
                
                # Add h-index boost for Tier 1
                if tier_key == "tier_1" and author_h_index:
                    if author_h_index >= settings.min_author_h_index:
                        base_score += min(author_h_index // 5, 15)  # Cap at +15
                
                return tier_key, base_score
    
    # Default to tier_3 if not found
    return "tier_3", 0


def is_source_allowed(url: str) -> bool:
    """Check if source is allowed (not in excluded list)"""
    tier, _ = classify_source_tier(url)
    return tier != "excluded"
