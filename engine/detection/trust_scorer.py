"""
Signal 1: Trust Score

Source reputation lookup based on metadata.
"""
from typing import Dict, Any
import config


class TrustScorer:
    """
    Assign trust score based on document source.

    Uses predefined reputation database (config.TRUST_SOURCES).
    """

    def __init__(self, trust_db: Dict[str, float] = None):
        self.trust_db = trust_db or config.TRUST_SOURCES

    def score(self, metadata: Dict[str, Any]) -> float:
        """
        Calculate trust score for document.

        Args:
            metadata: Document metadata (must include 'source' key)

        Returns:
            Trust score between 0.0 (untrusted) and 1.0 (fully trusted)
        """
        source = metadata.get("source", "unknown").lower()

        # Exact match
        if source in self.trust_db:
            return self.trust_db[source]

        # Partial match (e.g., subdomain or contains keyword)
        for trusted_source, score in self.trust_db.items():
            if trusted_source in source or source in trusted_source:
                return score

        # Check category
        category = metadata.get("category", "")
        if category in self.trust_db:
            return self.trust_db[category]

        # Default: unknown source
        return self.trust_db.get("unknown", 0.3)


# Global instance
trust_scorer = TrustScorer()
