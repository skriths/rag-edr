"""
Signal 3: Anomaly Score

Source diversity and trust variance analysis across corpus.
"""
from typing import List, Dict, Any
import statistics


class AnomalyScorer:
    """
    Detect anomalies in source distribution and trust variance.

    High anomaly = document comes from unusual source cluster or
    has significantly different trust score than corpus average.
    """

    def score(self, doc_metadata: Dict[str, Any], all_docs: List[Dict[str, Any]]) -> float:
        """
        Calculate anomaly score for document in context of corpus.

        Args:
            doc_metadata: Metadata for document being scored
            all_docs: All documents in corpus (for distribution analysis)

        Returns:
            Score between 0.0 (anomalous) and 1.0 (normal)
        """
        if len(all_docs) < 3:
            return 1.0  # Not enough data for statistical analysis

        # Extract sources from corpus
        sources = [doc.get("metadata", {}).get("source", "unknown") for doc in all_docs]
        doc_source = doc_metadata.get("source", "unknown")

        # Calculate source frequency
        source_counts = {}
        for src in sources:
            source_counts[src] = source_counts.get(src, 0) + 1

        doc_frequency = source_counts.get(doc_source, 0) / len(sources)

        # Anomaly if source is rare (< 20% of corpus)
        frequency_score = min(doc_frequency / 0.2, 1.0)

        # Trust variance analysis
        trust_scores = []
        for doc in all_docs:
            source = doc.get("metadata", {}).get("source", "unknown")
            category = doc.get("metadata", {}).get("category", "")

            # Simple trust lookup
            from engine.detection.trust_scorer import trust_scorer
            trust = trust_scorer.score({"source": source, "category": category})
            trust_scores.append(trust)

        if len(trust_scores) >= 3:
            avg_trust = statistics.mean(trust_scores)
            std_trust = statistics.stdev(trust_scores) if len(trust_scores) > 1 else 0.1

            # Document's trust score
            from engine.detection.trust_scorer import trust_scorer
            doc_trust = trust_scorer.score(doc_metadata)

            # Z-score: how many std deviations from mean
            if std_trust > 0:
                z_score = abs(doc_trust - avg_trust) / std_trust
                # High z-score = anomalous
                variance_score = max(0.0, 1.0 - (z_score / 3.0))  # Normalize to 0-1
            else:
                variance_score = 1.0
        else:
            variance_score = 1.0

        # Combine frequency and variance
        combined_score = (frequency_score * 0.6) + (variance_score * 0.4)

        return combined_score


# Global instance
anomaly_scorer = AnomalyScorer()
