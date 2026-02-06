"""
Unit tests for Phase 1 retrieval improvements.

Tests:
- Entity extraction (CVE IDs)
- Query augmentation
- Metadata filter creation
- End-to-end query processing
"""
try:
    import pytest
except ImportError:
    pytest = None  # Optional dependency

from engine.utils.entity_extractor import EntityExtractor
from engine.utils.query_processor import QueryProcessor


class TestEntityExtractor:
    """Test CVE ID extraction functionality."""

    def test_extract_single_cve(self):
        """Test extracting a single CVE ID."""
        text = "How to fix CVE-2024-0004?"
        result = EntityExtractor.extract_cve_ids(text)
        assert result == ["CVE-2024-0004"]

    def test_extract_multiple_cves(self):
        """Test extracting multiple CVE IDs."""
        text = "CVE-2024-0001 and CVE-2024-0002 are related"
        result = EntityExtractor.extract_cve_ids(text)
        assert result == ["CVE-2024-0001", "CVE-2024-0002"]

    def test_extract_lowercase_cve(self):
        """Test normalization of lowercase CVE IDs."""
        text = "Check cve-2024-0004 for details"
        result = EntityExtractor.extract_cve_ids(text)
        assert result == ["CVE-2024-0004"]

    def test_extract_no_cve(self):
        """Test query with no CVE IDs."""
        text = "How to secure MySQL databases?"
        result = EntityExtractor.extract_cve_ids(text)
        assert result == []

    def test_extract_mixed_case(self):
        """Test mixed case CVE IDs."""
        text = "Compare CVE-2024-0001 with cve-2024-0002"
        result = EntityExtractor.extract_cve_ids(text)
        assert result == ["CVE-2024-0001", "CVE-2024-0002"]

    def test_extract_duplicates(self):
        """Test duplicate CVE ID removal."""
        text = "CVE-2024-0004 is critical. CVE-2024-0004 affects MySQL."
        result = EntityExtractor.extract_cve_ids(text)
        assert result == ["CVE-2024-0004"]

    def test_extract_with_varying_lengths(self):
        """Test CVE IDs with different number lengths."""
        text = "CVE-2024-1 and CVE-2024-12345 and CVE-2024-1234567"
        result = EntityExtractor.extract_cve_ids(text)
        assert result == ["CVE-2024-1", "CVE-2024-12345", "CVE-2024-1234567"]

    def test_has_cve_id_true(self):
        """Test has_cve_id returns True."""
        assert EntityExtractor.has_cve_id("CVE-2024-0004") is True

    def test_has_cve_id_false(self):
        """Test has_cve_id returns False."""
        assert EntityExtractor.has_cve_id("General security question") is False

    def test_extract_entities_structure(self):
        """Test extract_entities returns correct structure."""
        text = "Mitigate CVE-2024-0004 in MySQL"
        result = EntityExtractor.extract_entities(text)
        assert "cve_ids" in result
        assert "software" in result
        assert "versions" in result
        assert result["cve_ids"] == ["CVE-2024-0004"]
        assert result["software"] == []
        assert result["versions"] == []

    def test_extract_from_empty_string(self):
        """Test extraction from empty string."""
        result = EntityExtractor.extract_cve_ids("")
        assert result == []

    def test_extract_from_none(self):
        """Test extraction from None."""
        result = EntityExtractor.extract_cve_ids(None)
        assert result == []


class TestQueryProcessor:
    """Test query augmentation and preprocessing."""

    def test_augment_query_with_cve(self):
        """Test query augmentation with CVE ID."""
        query = "How to mitigate CVE-2024-0004?"
        result = QueryProcessor.augment_query(query, boost_factor=3)
        expected = "CVE-2024-0004 CVE-2024-0004 CVE-2024-0004 How to mitigate CVE-2024-0004?"
        assert result == expected

    def test_augment_query_no_cve(self):
        """Test query augmentation without CVE ID (no change)."""
        query = "How to secure MySQL?"
        result = QueryProcessor.augment_query(query)
        assert result == query

    def test_augment_query_multiple_cves(self):
        """Test augmentation with multiple CVE IDs."""
        query = "Compare CVE-2024-0003 and CVE-2024-0004"
        result = QueryProcessor.augment_query(query, boost_factor=2)
        expected = "CVE-2024-0003 CVE-2024-0003 CVE-2024-0004 CVE-2024-0004 Compare CVE-2024-0003 and CVE-2024-0004"
        assert result == expected

    def test_augment_query_custom_boost(self):
        """Test custom boost factor."""
        query = "Fix CVE-2024-0004"
        result = QueryProcessor.augment_query(query, boost_factor=5)
        boosted = " ".join(["CVE-2024-0004"] * 5)
        expected = f"{boosted} Fix CVE-2024-0004"
        assert result == expected

    def test_create_metadata_filter_with_cve(self):
        """Test metadata filter creation for CVE query."""
        query = "How to fix CVE-2024-0004?"
        result = QueryProcessor.create_metadata_filter(query)
        assert result == {"cve_ids": {"$contains": "CVE-2024-0004"}}

    def test_create_metadata_filter_no_cve(self):
        """Test metadata filter returns None for non-CVE query."""
        query = "How to secure MySQL?"
        result = QueryProcessor.create_metadata_filter(query)
        assert result is None

    def test_create_metadata_filter_multiple_cves(self):
        """Test metadata filter uses first CVE ID."""
        query = "Compare CVE-2024-0003 and CVE-2024-0004"
        result = QueryProcessor.create_metadata_filter(query)
        # Should use first CVE found
        assert result == {"cve_ids": {"$contains": "CVE-2024-0003"}}

    def test_process_query_with_cve(self):
        """Test full query processing pipeline with CVE."""
        query = "How to mitigate CVE-2024-0004?"
        augmented, filter_clause = QueryProcessor.process_query(query)

        # Check augmentation
        assert "CVE-2024-0004" in augmented
        assert augmented.count("CVE-2024-0004") == 4  # 3 boosts + 1 original

        # Check filter
        assert filter_clause == {"cve_ids": {"$contains": "CVE-2024-0004"}}

    def test_process_query_without_cve(self):
        """Test query processing without CVE (no changes)."""
        query = "How to secure MySQL?"
        augmented, filter_clause = QueryProcessor.process_query(query)

        # No augmentation
        assert augmented == query

        # No filter
        assert filter_clause is None

    def test_get_query_type_cve_lookup(self):
        """Test query type classification: CVE lookup."""
        query = "What is CVE-2024-0004?"
        result = QueryProcessor.get_query_type(query)
        assert result == "cve_lookup"

    def test_get_query_type_comparison(self):
        """Test query type classification: comparison."""
        queries = [
            "Compare CVE-2024-0003 and CVE-2024-0004",
            "CVE-2024-0003 vs CVE-2024-0004",
            "Difference between CVE-2024-0003 versus CVE-2024-0004"
        ]
        for query in queries:
            result = QueryProcessor.get_query_type(query)
            assert result == "comparison"

    def test_get_query_type_general(self):
        """Test query type classification: general."""
        query = "How to secure MySQL databases?"
        result = QueryProcessor.get_query_type(query)
        assert result == "general"


class TestIntegration:
    """Integration tests for Phase 1 components."""

    def test_end_to_end_cve_query(self):
        """Test complete query preprocessing flow for CVE query."""
        query = "How to mitigate CVE-2024-0004?"

        # Step 1: Extract entities
        entities = EntityExtractor.extract_entities(query)
        assert entities["cve_ids"] == ["CVE-2024-0004"]

        # Step 2: Process query
        augmented, metadata_filter = QueryProcessor.process_query(query)
        assert "CVE-2024-0004" in augmented
        assert metadata_filter is not None

        # Step 3: Verify filter structure for ChromaDB
        assert "$contains" in metadata_filter["cve_ids"]
        assert metadata_filter["cve_ids"]["$contains"] == "CVE-2024-0004"

    def test_end_to_end_general_query(self):
        """Test complete query preprocessing flow for general query."""
        query = "Best practices for MySQL security"

        # Step 1: Extract entities
        entities = EntityExtractor.extract_entities(query)
        assert entities["cve_ids"] == []

        # Step 2: Process query
        augmented, metadata_filter = QueryProcessor.process_query(query)
        assert augmented == query  # No augmentation
        assert metadata_filter is None  # No filter

    def test_case_insensitive_cve_matching(self):
        """Test case-insensitive CVE matching."""
        queries = [
            "CVE-2024-0004",
            "cve-2024-0004",
            "Cve-2024-0004",
            "CvE-2024-0004"
        ]

        for query in queries:
            augmented, metadata_filter = QueryProcessor.process_query(query)
            assert metadata_filter == {"cve_ids": {"$contains": "CVE-2024-0004"}}

    def test_query_with_punctuation(self):
        """Test CVE extraction with various punctuation."""
        queries = [
            "How to fix CVE-2024-0004?",
            "CVE-2024-0004.",
            "CVE-2024-0004!",
            "(CVE-2024-0004)",
            "[CVE-2024-0004]"
        ]

        for query in queries:
            cves = EntityExtractor.extract_cve_ids(query)
            assert "CVE-2024-0004" in cves


# Benchmark tests (optional, for performance tracking)
class TestPerformance:
    """Performance benchmarks for Phase 1 components."""

    def test_entity_extraction_performance(self, benchmark=None):
        """Benchmark CVE extraction performance."""
        text = "CVE-2024-0001 CVE-2024-0002 CVE-2024-0003" * 10

        if benchmark:
            result = benchmark(EntityExtractor.extract_cve_ids, text)
        else:
            import time
            start = time.time()
            for _ in range(1000):
                EntityExtractor.extract_cve_ids(text)
            elapsed = time.time() - start
            print(f"Entity extraction: {elapsed*1000:.2f}ms for 1000 iterations")

    def test_query_augmentation_performance(self, benchmark=None):
        """Benchmark query augmentation performance."""
        query = "How to mitigate CVE-2024-0004?"

        if benchmark:
            result = benchmark(QueryProcessor.augment_query, query)
        else:
            import time
            start = time.time()
            for _ in range(1000):
                QueryProcessor.augment_query(query)
            elapsed = time.time() - start
            print(f"Query augmentation: {elapsed*1000:.2f}ms for 1000 iterations")


if __name__ == "__main__":
    """Run tests without pytest."""
    import sys

    # Run entity extractor tests
    print("Testing EntityExtractor...")
    test_entity = TestEntityExtractor()
    for method in dir(test_entity):
        if method.startswith("test_"):
            try:
                getattr(test_entity, method)()
                print(f"  ✓ {method}")
            except AssertionError as e:
                print(f"  ✗ {method}: {e}")
                sys.exit(1)

    # Run query processor tests
    print("\nTesting QueryProcessor...")
    test_query = TestQueryProcessor()
    for method in dir(test_query):
        if method.startswith("test_"):
            try:
                getattr(test_query, method)()
                print(f"  ✓ {method}")
            except AssertionError as e:
                print(f"  ✗ {method}: {e}")
                sys.exit(1)

    # Run integration tests
    print("\nTesting Integration...")
    test_integration = TestIntegration()
    for method in dir(test_integration):
        if method.startswith("test_"):
            try:
                getattr(test_integration, method)()
                print(f"  ✓ {method}")
            except AssertionError as e:
                print(f"  ✗ {method}: {e}")
                sys.exit(1)

    print("\n✅ All tests passed!")
