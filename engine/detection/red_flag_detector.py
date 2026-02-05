"""
Signal 2: Red Flag Detection

Multi-layer keyword matching with category scoring.
"""
from typing import Dict, List, Tuple
import config


class RedFlagDetector:
    """
    Detect malicious patterns in document content.

    Categories:
    - security_downgrade: Disabling security controls
    - dangerous_permissions: Insecure file permissions
    - severity_downplay: Minimizing CVE severity
    - unsafe_operations: Skipping security best practices
    - social_engineering: Manipulative language
    """

    def __init__(self, red_flags: Dict[str, List[str]] = None):
        self.red_flags = red_flags or config.RED_FLAGS

    def score(self, content: str) -> float:
        """
        Calculate red flag score.

        Args:
            content: Document text

        Returns:
            Score between 0.0 (many red flags) and 1.0 (clean)
        """
        content_lower = content.lower()
        total_flags = 0
        categories_with_flags = 0

        for category, keywords in self.red_flags.items():
            category_flags = 0
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    category_flags += 1

            if category_flags > 0:
                categories_with_flags += 1
                total_flags += category_flags

        # Base score calculation
        max_possible_flags = sum(len(keywords) for keywords in self.red_flags.values())
        if max_possible_flags == 0:
            return 1.0

        base_score = 1.0 - (total_flags / max_possible_flags)

        # Cross-category amplification
        if categories_with_flags >= 3:
            base_score *= 0.75  # Severe: 3+ categories
        elif categories_with_flags >= 2:
            base_score *= 0.85  # High: 2+ categories

        return max(base_score, 0.0)

    def detect_flags(self, content: str) -> Tuple[Dict[str, List[str]], int]:
        """
        Return detected red flags by category (for detailed reporting).

        Returns:
            Tuple of (detected_flags_dict, total_count)
        """
        content_lower = content.lower()
        detected = {}
        total_count = 0

        for category, keywords in self.red_flags.items():
            found = [kw for kw in keywords if kw.lower() in content_lower]
            if found:
                detected[category] = found
                total_count += len(found)

        return detected, total_count


# Global instance
red_flag_detector = RedFlagDetector()
