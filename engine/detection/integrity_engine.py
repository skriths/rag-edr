"""
Integrity Engine: Orchestrates all 4 signals and trigger logic.
"""
from typing import Dict, Any, List, Optional
from engine.schemas import IntegritySignals
from engine.detection.trust_scorer import trust_scorer
from engine.detection.red_flag_detector import red_flag_detector
from engine.detection.anomaly_scorer import anomaly_scorer
from engine.detection.semantic_drift import semantic_drift_detector
import config


class IntegrityEngine:
    """
    Orchestrates 4-signal integrity scoring and quarantine trigger.

    Trigger rule: 2 of 4 signals below threshold → quarantine

    Signals:
    1. Trust Score (weight: 0.25) - Source reputation
    2. Red Flag Score (weight: 0.35) - Keyword detection (highest weight)
    3. Anomaly Score (weight: 0.15) - Statistical outlier detection
    4. Semantic Drift Score (weight: 0.25) - Golden corpus similarity
    """

    def __init__(self, threshold: float = config.INTEGRITY_THRESHOLD):
        self.threshold = threshold

    async def evaluate_document(
        self,
        doc_id: str,
        content: str,
        metadata: Dict[str, Any],
        embedding: Optional[List[float]],
        all_docs: List[Dict[str, Any]]
    ) -> IntegritySignals:
        """
        Run all 4 signals on document.

        Args:
            doc_id: Document identifier
            content: Full text
            metadata: Metadata (source, category, etc.)
            embedding: Vector embedding
            all_docs: Corpus for anomaly detection

        Returns:
            IntegritySignals with all scores
        """
        # Signal 1: Trust Score
        trust_score = trust_scorer.score(metadata)

        # Signal 2: Red Flag Detection (context-aware for golden corpus)
        red_flag_score = red_flag_detector.score(content, metadata)

        # Signal 3: Anomaly Score
        anomaly_score = anomaly_scorer.score(metadata, all_docs)

        # Signal 4: Semantic Drift
        semantic_score = semantic_drift_detector.score(embedding)

        return IntegritySignals(
            trust_score=trust_score,
            red_flag_score=red_flag_score,
            anomaly_score=anomaly_score,
            semantic_drift_score=semantic_score
        )

    async def evaluate_batch(
        self,
        documents: List[Dict[str, Any]],
        all_docs: List[Dict[str, Any]]
    ) -> Dict[str, IntegritySignals]:
        """
        Evaluate multiple documents in batch.

        Args:
            documents: List of documents to evaluate
            all_docs: Full corpus for context

        Returns:
            Dictionary mapping doc_id to IntegritySignals
        """
        results = {}

        for doc in documents:
            signals = await self.evaluate_document(
                doc_id=doc["doc_id"],
                content=doc["content"],
                metadata=doc["metadata"],
                embedding=doc.get("embedding"),
                all_docs=all_docs
            )
            results[doc["doc_id"]] = signals

        return results

    def get_detailed_report(
        self,
        doc_id: str,
        content: str,
        signals: IntegritySignals
    ) -> Dict[str, Any]:
        """
        Generate detailed integrity report for dashboard/logging.

        Args:
            doc_id: Document ID
            content: Document content
            signals: Computed integrity signals

        Returns:
            Detailed report dictionary
        """
        # Get red flags breakdown
        detected_flags, flag_count = red_flag_detector.detect_flags(content)

        report = {
            "doc_id": doc_id,
            "scores": {
                "trust": signals.trust_score,
                "red_flag": signals.red_flag_score,
                "anomaly": signals.anomaly_score,
                "semantic_drift": signals.semantic_drift_score,
                "combined": signals.combined_score
            },
            "should_quarantine": signals.should_quarantine(self.threshold),
            "low_signals": signals.get_low_signals(self.threshold),
            "red_flags": {
                "detected": detected_flags,
                "total_count": flag_count,
                "categories_affected": len(detected_flags)
            },
            "severity": self._calculate_severity(signals)
        }

        return report

    def _calculate_severity(self, signals: IntegritySignals) -> str:
        """
        Calculate severity level based on signals.

        Returns:
            "CLEAN", "SUSPICIOUS", "MALICIOUS", "CRITICAL"
        """
        combined = signals.combined_score
        low_signals = len(signals.get_low_signals(self.threshold))

        if combined >= 0.7:
            return "CLEAN"
        elif combined >= 0.5:
            return "SUSPICIOUS"
        elif low_signals >= 3:
            return "CRITICAL"
        else:
            return "MALICIOUS"


# Global instance
integrity_engine = IntegrityEngine()
