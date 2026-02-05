#!/usr/bin/env python3
"""
Diagnostic script to check RAG-EDR system state.
"""
import asyncio
from engine.adapters.vector_store import vector_store
from engine.detection.red_flag_detector import red_flag_detector
from engine.detection.trust_scorer import trust_scorer

async def diagnose():
    print("=" * 60)
    print("RAG-EDR System Diagnostic")
    print("=" * 60)

    # Get all documents
    print("\nFetching all documents from ChromaDB...")
    all_docs = await vector_store.get_all_documents()
    print(f"Total documents: {len(all_docs)}")

    # Analyze each document
    print("\n" + "=" * 60)
    print("Document Analysis:")
    print("=" * 60)

    for doc in all_docs:
        doc_id = doc["doc_id"]
        metadata = doc["metadata"]
        content = doc["content"]

        print(f"\n📄 Document: {doc_id}")
        print(f"   Source: {metadata.get('source', 'unknown')}")
        print(f"   Category: {metadata.get('category', 'unknown')}")
        print(f"   Quarantined: {metadata.get('is_quarantined', False)}")

        # Trust score
        trust = trust_scorer.score(metadata)
        print(f"   Trust Score: {trust:.2f} ({trust*100:.0f}%)")

        # Red flag detection
        red_flag_score = red_flag_detector.score(content)
        detected_flags, flag_count = red_flag_detector.detect_flags(content)
        print(f"   Red Flag Score: {red_flag_score:.2f} ({red_flag_score*100:.0f}%)")
        print(f"   Red Flags Found: {flag_count}")
        if detected_flags:
            for category, flags in detected_flags.items():
                print(f"      - {category}: {flags}")

        # Show first 200 chars of content
        print(f"   Content Preview: {content[:200]}...")

    print("\n" + "=" * 60)
    print("Diagnostic Complete")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(diagnose())
