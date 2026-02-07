"""
Ingest corpus documents into ChromaDB.

Run once at startup or after demo reset.
"""
import asyncio
from pathlib import Path
from engine.adapters.vector_store import vector_store
from engine.logging.event_logger import logger
import config


async def ingest_corpus():
    """Load all corpus documents into vector store"""

    print("=" * 60)
    print("RAGShieldCorpus Ingestion")
    print("=" * 60)

    total_docs = 0

    corpus_dirs = [
        (config.CLEAN_CORPUS, "clean"),
        (config.POISONED_CORPUS, "poisoned"),
        (config.GOLDEN_CORPUS, "golden")
    ]

    for corpus_dir, category in corpus_dirs:
        print(f"\nProcessing {category} corpus from {corpus_dir}...")

        if not corpus_dir.exists():
            print(f"  WARNING: Directory not found: {corpus_dir}")
            continue

        doc_count = 0
        for doc_path in corpus_dir.glob("*.txt"):
            doc_id = doc_path.stem  # Filename without extension
            content = doc_path.read_text(encoding='utf-8')

            # Determine source from content
            content_lower = content.lower()
            if "nvd.nist.gov" in content_lower:
                source = "nvd.nist.gov"
            elif "ubuntu.com/security" in content_lower:
                source = "ubuntu.com/security"
            elif "debian.org/security" in content_lower:
                source = "debian.org/security"
            elif "cve.mitre.org" in content_lower:
                source = "cve.mitre.org"
            elif category == "golden":
                source = "golden"
            elif category == "clean":
                source = "clean"
            else:
                source = "unknown"

            metadata = {
                "source": source,
                "category": category,
                "filename": doc_path.name
            }

            await vector_store.ingest_document(doc_id, content, metadata)
            print(f"  ✓ Ingested: {doc_id} (source={source})")

            doc_count += 1
            total_docs += 1

        print(f"  {doc_count} documents from {category} corpus")

    # Log ingestion completion
    await logger.log_system_event(
        event_id=4003,
        message=f"Corpus ingestion completed: {total_docs} documents loaded",
        details={
            "total_documents": total_docs,
            "clean": len(list(config.CLEAN_CORPUS.glob("*.txt"))),
            "poisoned": len(list(config.POISONED_CORPUS.glob("*.txt"))),
            "golden": len(list(config.GOLDEN_CORPUS.glob("*.txt")))
        }
    )

    print("\n" + "=" * 60)
    print(f"Corpus ingestion complete! Total: {total_docs} documents")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(ingest_corpus())
