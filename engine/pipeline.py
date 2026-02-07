"""
RAGShieldPipeline: Orchestrates retrieval, integrity checks, and generation.

Phase 1 Enhancement: Query preprocessing with CVE ID extraction and augmentation.
"""
from typing import List, Dict, Any
from uuid import uuid4
from engine.adapters.vector_store import vector_store
from engine.adapters.llm import llm
from engine.detection.integrity_engine import integrity_engine
from engine.response.quarantine_vault import quarantine_vault
from engine.response.blast_radius import blast_radius_analyzer
from engine.logging.event_logger import logger
from engine.schemas import Event, EventLevel, EventCategory
from engine.utils.query_processor import QueryProcessor
import config


class RAGPipeline:
    """
    End-to-end RAG pipeline with integrity checks and quarantine filtering.

    Flow:
    0. Preprocess query (Phase 1: extract CVE IDs, augment query)
    1. Retrieve documents from vector store (exclude quarantined, with metadata filter)
    2. Run integrity checks on retrieved docs
    3. Quarantine suspicious docs
    4. If clean docs remain, generate answer
    5. Log query lineage for blast radius
    6. Return answer or safety message
    """

    async def query(
        self,
        query_text: str,
        user_id: str = "default-user",
        k: int = 5
    ) -> Dict[str, Any]:
        """
        Execute RAG query with EDR protection.

        Phase 1: Includes query preprocessing for exact CVE ID matching.

        Args:
            query_text: User question
            user_id: User identifier (for lineage tracking)
            k: Number of documents to retrieve

        Returns:
            Dict with keys:
            - answer: Generated response or safety message
            - retrieved_docs: List of doc IDs used
            - quarantined_docs: List of doc IDs quarantined during query
            - integrity_signals: Signals for each retrieved doc
            - query_id: Unique query identifier
        """
        query_id = str(uuid4())

        # Step 0: Phase 1 - Preprocess query (extract CVE IDs, augment for better matching)
        augmented_query, metadata_filter = QueryProcessor.process_query(query_text)

        # Step 1: Retrieve documents with preprocessing
        retrieved = await vector_store.retrieve(
            augmented_query,
            k=k,
            exclude_quarantined=True,
            metadata_filter=metadata_filter
        )

        if not retrieved:
            await logger.log_system_event(
                event_id=1001,
                message=f"Query returned no documents: {query_text[:50]}...",
                details={"query_id": query_id, "user_id": user_id}
            )
            return {
                "answer": "No documents available to answer this query.",
                "retrieved_docs": [],
                "quarantined_docs": [],
                "integrity_signals": {},
                "query_id": query_id
            }

        # Step 2: Run integrity checks
        all_docs = await vector_store.get_all_documents()
        quarantined_docs = []
        clean_docs = []
        signals_map = {}

        for doc in retrieved:
            # Evaluate integrity
            signals = await integrity_engine.evaluate_document(
                doc_id=doc["doc_id"],
                content=doc["content"],
                metadata=doc["metadata"],
                embedding=doc.get("embedding"),
                all_docs=all_docs
            )

            signals_map[doc["doc_id"]] = signals.model_dump()

            # Step 3: Quarantine if triggered
            if signals.should_quarantine():
                await self._quarantine_doc(doc, signals, query_id, query_text, user_id)
                quarantined_docs.append(doc["doc_id"])

                # Log integrity check with quarantine
                await logger.log_integrity_check(
                    query_id=query_id,
                    query_text=query_text,
                    doc_id=doc["doc_id"],
                    signals=signals,
                    quarantined=True,
                    user_id=user_id
                )
            else:
                clean_docs.append(doc)

                # Log integrity check passed
                await logger.log_integrity_check(
                    query_id=query_id,
                    query_text=query_text,
                    doc_id=doc["doc_id"],
                    signals=signals,
                    quarantined=False,
                    user_id=user_id
                )

        # Step 4: Generate answer or return safety message
        if clean_docs:
            answer = await llm.generate(query_text, clean_docs)
            action_taken = "partial" if quarantined_docs else "allow"
        else:
            answer = "This query cannot be answered safely at this moment. The retrieved documents have been flagged for security review. Please contact your security team."
            action_taken = "quarantine"

        # Step 5: Log lineage
        retrieved_doc_ids = [doc["doc_id"] for doc in retrieved]
        await blast_radius_analyzer.log_query(
            query_id=query_id,
            query_text=query_text,
            user_id=user_id,
            retrieved_docs=retrieved_doc_ids,
            integrity_signals=signals_map,
            action_taken=action_taken
        )

        return {
            "answer": answer,
            "retrieved_docs": retrieved_doc_ids,
            "quarantined_docs": quarantined_docs,
            "integrity_signals": signals_map,
            "query_id": query_id
        }

    async def _quarantine_doc(self, doc: Dict, signals, query_id: str, query_text: str, user_id: str):
        """
        Helper to quarantine document.

        Args:
            doc: Document to quarantine
            signals: IntegritySignals
            query_id: Query that triggered quarantine
            query_text: Query text
            user_id: User who made the query
        """
        # Get detailed report
        report = integrity_engine.get_detailed_report(
            doc_id=doc["doc_id"],
            content=doc["content"],
            signals=signals
        )

        reason = (
            f"Triggered quarantine on query {query_id}. "
            f"Low signals: {', '.join(report['low_signals'])}. "
            f"Combined score: {signals.combined_score:.2f}. "
            f"Red flags: {report['red_flags']['total_count']} detected."
        )

        # Quarantine in vault
        record = await quarantine_vault.quarantine_document(
            doc_id=doc["doc_id"],
            content=doc["content"],
            metadata=doc["metadata"],
            integrity_signals=signals,
            reason=reason
        )

        # Mark quarantined in vector store
        await vector_store.mark_quarantined(doc["doc_id"], record.quarantine_id)

        # Log quarantine action
        await logger.log_quarantine_action(
            quarantine_id=record.quarantine_id,
            doc_id=doc["doc_id"],
            reason=reason,
            action="initiated"
        )

    async def initialize(self):
        """
        Initialize pipeline (load golden corpus, check Ollama, etc.).

        Call this once at startup.
        """
        # Load golden corpus for semantic drift detection
        all_docs = await vector_store.get_all_documents()
        from engine.detection.semantic_drift import semantic_drift_detector
        await semantic_drift_detector.load_golden_corpus(all_docs)

        # Check Ollama status
        ollama_ok = await llm.check_ollama_status()

        # Log startup
        await logger.log_system_event(
            event_id=4001,
            message="RAGShieldpipeline started",
            details={
                "ollama_connected": ollama_ok,
                "document_count": vector_store.get_document_count(),
                "quarantine_count": quarantine_vault.get_quarantine_count()
            }
        )

        return ollama_ok


# Global instance
rag_pipeline = RAGPipeline()
