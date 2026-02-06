"""
Query preprocessing utilities for RAG-EDR.

Improves retrieval accuracy through:
- Term boosting (Phase 1)
- Query expansion (Future Phase 2)
- Intent classification (Future Phase 2)
"""
from typing import Tuple, Dict, Any, Optional
from engine.utils.entity_extractor import EntityExtractor


class QueryProcessor:
    """
    Preprocess queries to improve retrieval accuracy.

    Phase 1: Term boosting for identifiers (CVE IDs)
    Future: Synonym expansion, intent classification, multi-entity handling
    """

    @staticmethod
    def augment_query(query: str, boost_factor: int = 3) -> str:
        """
        Boost important terms by repeating them in query.

        Strategy:
        - CVE IDs repeated boost_factor times (high importance)
        - Original query appended (preserves semantic meaning)
        - Works because embedding models weight frequently occurring terms higher

        Args:
            query: Original user query
            boost_factor: Number of times to repeat each CVE ID (default: 3)

        Returns:
            Augmented query with boosted terms

        Example:
            >>> QueryProcessor.augment_query("How to mitigate CVE-2024-0004?")
            'CVE-2024-0004 CVE-2024-0004 CVE-2024-0004 How to mitigate CVE-2024-0004?'

        Why this works:
        - Embedding models use TF-IDF-like weighting
        - Repeated terms get higher importance in embedding space
        - Original query preserved for semantic context
        - Minimal latency overhead (~1ms)
        """
        cve_ids = EntityExtractor.extract_cve_ids(query)

        if not cve_ids:
            return query  # No augmentation needed

        # Repeat each CVE ID boost_factor times
        boosted_terms = []
        for cve_id in cve_ids:
            boosted_terms.extend([cve_id] * boost_factor)

        # Combine: [boosted terms] + [original query]
        augmented = " ".join(boosted_terms) + " " + query
        return augmented

    @staticmethod
    def create_metadata_filter(query: str) -> Optional[Dict[str, Any]]:
        """
        Create ChromaDB metadata filter from query entities.

        Phase 1: Filter by first CVE ID found
        Future Phase 2: Multi-CVE filters, software filters

        Note: cve_ids is stored as comma-separated string in ChromaDB.
        This filter matches if the CVE ID appears in that string.

        Args:
            query: User query

        Returns:
            ChromaDB WHERE clause dict, or None if no entities found

        Example:
            >>> QueryProcessor.create_metadata_filter("How to fix CVE-2024-0004?")
            {'cve_ids': {'$contains': 'CVE-2024-0004'}}

            >>> QueryProcessor.create_metadata_filter("General security question")
            None
        """
        entities = EntityExtractor.extract_entities(query)

        # Phase 1: Filter by first CVE ID only
        if entities["cve_ids"]:
            # ChromaDB only supports: $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin
            # Since each document typically has one CVE, use $eq for exact match
            return {"cve_ids": {"$eq": entities["cve_ids"][0]}}

        # Future Phase 2: Add software, version filters
        # if entities["software"]:
        #     return {"software": {"$in": entities["software"]}}

        return None

    @staticmethod
    def process_query(query: str, boost_factor: int = 3) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Full query preprocessing pipeline.

        Combines:
        1. Entity extraction
        2. Metadata filter creation
        3. Query augmentation

        Args:
            query: Original user query
            boost_factor: CVE ID repetition count (default: 3)

        Returns:
            Tuple of (augmented_query, metadata_filter)

        Example:
            >>> augmented, filter = QueryProcessor.process_query("How to mitigate CVE-2024-0004?")
            >>> augmented
            'CVE-2024-0004 CVE-2024-0004 CVE-2024-0004 How to mitigate CVE-2024-0004?'
            >>> filter
            {'cve_ids': {'$contains': 'CVE-2024-0004'}}

        Usage in pipeline:
            augmented_query, metadata_filter = QueryProcessor.process_query(user_query)
            results = await vector_store.retrieve(augmented_query, metadata_filter=metadata_filter)
        """
        # Create metadata filter for exact matching
        metadata_filter = QueryProcessor.create_metadata_filter(query)

        # Augment query for better semantic matching
        augmented_query = QueryProcessor.augment_query(query, boost_factor)

        return augmented_query, metadata_filter

    @staticmethod
    def get_query_type(query: str) -> str:
        """
        Classify query intent (for future routing logic).

        Phase 1: Basic classification
        Future Phase 2: Use small classifier model

        Args:
            query: User query

        Returns:
            Query type: "cve_lookup", "general", "comparison"

        Example:
            >>> QueryProcessor.get_query_type("What is CVE-2024-0004?")
            'cve_lookup'

            >>> QueryProcessor.get_query_type("How to secure MySQL?")
            'general'
        """
        has_cve = EntityExtractor.has_cve_id(query)

        if has_cve:
            # Check for comparison keywords
            if any(keyword in query.lower() for keyword in ["compare", "vs", "versus", "difference"]):
                return "comparison"
            return "cve_lookup"

        return "general"
