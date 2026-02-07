"""
ChromaDB adapter for RAG-EDR.

Handles document ingestion, retrieval, and quarantine filtering.

Phase 1 Enhancement: Metadata-enriched retrieval with CVE ID filtering.
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import config
from engine.utils.entity_extractor import EntityExtractor


class VectorStore:
    """
    Wrapper around ChromaDB with quarantine-aware retrieval.

    Documents have metadata:
    - doc_id: Unique identifier
    - source: Origin (for trust scoring)
    - is_quarantined: Boolean flag
    - quarantine_id: If quarantined, reference to vault
    - category: clean/poisoned/golden
    - cve_ids: CVE ID string (Phase 1, e.g., "CVE-2024-0004")
      Note: Currently stores single CVE per document for $eq filtering
    """

    def __init__(self):
        """Initialize ChromaDB client and load embedding model"""
        self.client = chromadb.PersistentClient(
            path=str(config.CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=config.CHROMA_COLLECTION,
            metadata={"description": "RAGShielddocument corpus"}
        )

        # Load embedding model for semantic similarity
        self.embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)

    async def ingest_document(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> None:
        """
        Add document to vector store with enriched metadata.

        Phase 1: Automatically extracts CVE IDs from content and stores in metadata.

        Args:
            doc_id: Unique identifier
            content: Full text content
            metadata: Must include 'source', optionally 'is_quarantined'
        """
        # Existing metadata defaults
        metadata.setdefault("is_quarantined", False)
        metadata.setdefault("quarantine_id", "")

        # Phase 1: Extract and store CVE IDs from content
        # ChromaDB requires scalar types and only supports $eq for exact match
        # Store first CVE ID only (sufficient for current corpus where each doc has one CVE)
        entities = EntityExtractor.extract_entities(content)
        cve_id_str = entities["cve_ids"][0] if entities["cve_ids"] else ""
        metadata.setdefault("cve_ids", cve_id_str)

        # Generate embedding
        embedding = self.embedding_model.encode(content).tolist()

        # Add to ChromaDB
        self.collection.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[metadata],
            embeddings=[embedding]
        )

    async def retrieve(
        self,
        query: str,
        k: int = 5,
        exclude_quarantined: bool = True,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents for query with optional metadata filtering.

        Phase 1: Supports ChromaDB WHERE filters for exact CVE ID matching.
        Note: cve_ids stores single CVE ID string, filtered with $eq.

        Args:
            query: Search query
            k: Number of results
            exclude_quarantined: Filter out quarantined docs
            metadata_filter: Optional ChromaDB WHERE clause for exact CVE match
                Example: {"cve_ids": {"$eq": "CVE-2024-0004"}}
                Supported operators: $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin

        Returns:
            List of dicts with keys: doc_id, content, metadata, distance, embedding

        Example:
            # Exact CVE ID match
            results = await retrieve(
                "How to fix CVE-2024-0004?",
                metadata_filter={"cve_ids": {"$eq": "CVE-2024-0004"}}
            )
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query).tolist()

        # Query ChromaDB (over-fetch if we need to filter)
        n_results = k * 3 if exclude_quarantined else k

        # Build query parameters
        query_params = {
            "query_embeddings": [query_embedding],
            "n_results": min(n_results, self.collection.count()),
            "include": ["documents", "metadatas", "distances", "embeddings"]
        }

        # Phase 1: Add metadata filter if provided
        if metadata_filter:
            query_params["where"] = metadata_filter

        # Execute query
        results = self.collection.query(**query_params)

        if not results["ids"] or not results["ids"][0]:
            return []

        documents = []
        for i, doc_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i]

            # Filter quarantined docs if requested
            if exclude_quarantined and metadata.get("is_quarantined", False):
                continue

            documents.append({
                "id": doc_id,  # Use 'id' for consistency
                "doc_id": doc_id,  # Keep for backwards compatibility
                "content": results["documents"][0][i],
                "metadata": metadata,
                "distance": results["distances"][0][i],
                "embedding": results["embeddings"][0][i] if results.get("embeddings") else None
            })

            if len(documents) >= k:
                break

        return documents

    async def mark_quarantined(self, doc_id: str, quarantine_id: str) -> None:
        """
        Mark document as quarantined (soft delete).

        Updates metadata to exclude from retrieval.
        """
        # Get current document data
        result = self.collection.get(
            ids=[doc_id],
            include=["metadatas", "documents", "embeddings"]
        )

        if not result["ids"]:
            return

        # Update metadata
        metadata = result["metadatas"][0]
        metadata["is_quarantined"] = True
        metadata["quarantine_id"] = quarantine_id

        # Update in ChromaDB
        self.collection.update(
            ids=[doc_id],
            metadatas=[metadata]
        )

    async def restore_document(self, doc_id: str) -> None:
        """Unmark quarantined document (restore to active corpus)"""
        result = self.collection.get(
            ids=[doc_id],
            include=["metadatas"]
        )

        if not result["ids"]:
            return

        metadata = result["metadatas"][0]
        metadata["is_quarantined"] = False
        metadata.pop("quarantine_id", None)

        self.collection.update(
            ids=[doc_id],
            metadatas=[metadata]
        )

    async def get_all_documents(self) -> List[Dict[str, Any]]:
        """
        Fetch all documents (for dashboard and integrity checks).

        Returns:
            List of all documents with full metadata
        """
        results = self.collection.get(
            include=["metadatas", "documents", "embeddings"]
        )

        docs = []
        for i, doc_id in enumerate(results["ids"]):
            docs.append({
                "doc_id": doc_id,
                "content": results["documents"][i],
                "metadata": results["metadatas"][i],
                "embedding": results["embeddings"][i] if results.get("embeddings") is not None else None
            })

        return docs

    def get_document_count(self) -> int:
        """Get total document count in collection"""
        return self.collection.count()

    async def reset(self) -> None:
        """
        Reset vector store (for demo reset).

        Deletes and recreates the collection.
        """
        self.client.delete_collection(name=config.CHROMA_COLLECTION)
        self.collection = self.client.get_or_create_collection(
            name=config.CHROMA_COLLECTION,
            metadata={"description": "RAGShielddocument corpus"}
        )


# Global instance
vector_store = VectorStore()
