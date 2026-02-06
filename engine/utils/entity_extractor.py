"""
Entity extraction utilities for RAG-EDR.

Extracts structured entities from queries and documents:
- CVE IDs (CVE-YYYY-NNNNN format)
- Software names (future)
- Version numbers (future)
"""
import re
from typing import List, Dict, Any


class EntityExtractor:
    """
    Extract structured entities from text.

    Phase 1: CVE ID extraction
    Future: Software names, version numbers, other identifiers
    """

    # Regex pattern for CVE IDs: CVE-YYYY-NNNNN (4-7 digits)
    # Examples: CVE-2024-0004, CVE-2023-12345, cve-2022-1
    CVE_PATTERN = re.compile(r'CVE-\d{4}-\d{1,7}', re.IGNORECASE)

    @staticmethod
    def extract_cve_ids(text: str) -> List[str]:
        """
        Extract CVE IDs from text.

        Args:
            text: Input text (query or document content)

        Returns:
            List of CVE IDs in uppercase format

        Examples:
            >>> EntityExtractor.extract_cve_ids("How to fix CVE-2024-0004?")
            ['CVE-2024-0004']

            >>> EntityExtractor.extract_cve_ids("CVE-2024-0001 and cve-2024-0002")
            ['CVE-2024-0001', 'CVE-2024-0002']

            >>> EntityExtractor.extract_cve_ids("No CVEs here")
            []
        """
        if not text:
            return []

        matches = EntityExtractor.CVE_PATTERN.findall(text)
        # Normalize to uppercase and remove duplicates while preserving order
        seen = set()
        result = []
        for m in matches:
            normalized = m.upper()
            if normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        return result

    @staticmethod
    def extract_entities(text: str) -> Dict[str, Any]:
        """
        Extract all entities from text.

        Args:
            text: Input text

        Returns:
            Dictionary with entity types as keys:
            {
                "cve_ids": ["CVE-2024-0004"],
                "software": [],  # Future Phase 2
                "versions": []   # Future Phase 2
            }

        Examples:
            >>> EntityExtractor.extract_entities("Mitigate CVE-2024-0004 in MySQL")
            {'cve_ids': ['CVE-2024-0004'], 'software': [], 'versions': []}
        """
        return {
            "cve_ids": EntityExtractor.extract_cve_ids(text),
            "software": [],   # Placeholder for Phase 2
            "versions": []    # Placeholder for Phase 2
        }

    @staticmethod
    def has_cve_id(text: str) -> bool:
        """
        Check if text contains any CVE ID.

        Args:
            text: Input text

        Returns:
            True if at least one CVE ID found

        Examples:
            >>> EntityExtractor.has_cve_id("CVE-2024-0004")
            True

            >>> EntityExtractor.has_cve_id("General security question")
            False
        """
        return bool(EntityExtractor.extract_cve_ids(text))
