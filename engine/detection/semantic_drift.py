"""
Signal 4: Semantic Drift

Embedding similarity to golden corpus.
"""
from typing import List, Dict, Any, Optional
import numpy as np
import config


class SemanticDriftDetector:
    """
    Compare document embeddings to golden corpus.

    High drift = document semantically diverges from trusted baseline.
    """

    def __init__(self):
        self.golden_embeddings: Optional[List[np.ndarray]] = None

    async def load_golden_corpus(self, all_docs: List[Dict[str, Any]]):
        """
        Load golden corpus embeddings for comparison.

        Args:
            all_docs: All documents from vector store
        """
        self.golden_embeddings = []

        for doc in all_docs:
            metadata = doc.get("metadata", {})
            category = metadata.get("category", "")
            source = metadata.get("source", "")

            # Identify golden documents
            if category == "golden" or "golden" in source:
                embedding = doc.get("embedding")
                if embedding is not None and len(embedding) > 0:
                    self.golden_embeddings.append(np.array(embedding))

        if len(self.golden_embeddings) == 0:
            # If no golden corpus, use clean documents as baseline
            for doc in all_docs:
                metadata = doc.get("metadata", {})
                category = metadata.get("category", "")
                if category == "clean":
                    embedding = doc.get("embedding")
                    if embedding is not None and len(embedding) > 0:
                        self.golden_embeddings.append(np.array(embedding))

    def score(self, doc_embedding: Optional[List[float]]) -> float:
        """
        Calculate semantic drift score.

        Args:
            doc_embedding: Document's embedding vector

        Returns:
            Score between 0.0 (high drift) and 1.0 (aligned with golden corpus)
        """
        if self.golden_embeddings is None or len(self.golden_embeddings) == 0 or doc_embedding is None:
            return 0.5  # Neutral if no baseline

        # Calculate cosine similarity to each golden doc
        similarities = []
        doc_vec = np.array(doc_embedding)

        # Normalize document vector
        doc_norm = np.linalg.norm(doc_vec)
        if doc_norm == 0:
            return 0.5

        for golden_vec in self.golden_embeddings:
            golden_norm = np.linalg.norm(golden_vec)
            if golden_norm == 0:
                continue

            # Cosine similarity
            similarity = np.dot(doc_vec, golden_vec) / (doc_norm * golden_norm)
            similarities.append(float(similarity))

        if len(similarities) == 0:
            return 0.5

        # Return max similarity (closest match to golden corpus)
        # Cosine similarity ranges from -1 to 1, normalize to 0-1
        max_sim = max(similarities)
        score = (max_sim + 1.0) / 2.0  # Convert from [-1, 1] to [0, 1]

        return score


# Global instance
semantic_drift_detector = SemanticDriftDetector()
