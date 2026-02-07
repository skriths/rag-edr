# RAGShield Retrieval System: Technical Reference

**Document Version:** 1.3
**Last Updated:** February 6, 2025
**Status:** ✅ Phase 1 Implemented (Exact CVE Matching)

---

## Table of Contents

1. [Current Retrieval Model](#1-current-retrieval-model)
2. [Identified Issues](#2-identified-issues)
3. [Phase 1: Quick Wins Implementation](#3-phase-1-quick-wins-implementation)
4. [Detailed Improvement Suggestions](#4-detailed-improvement-suggestions)
5. [Implementation Roadmap](#5-implementation-roadmap)
6. [Performance Considerations](#6-performance-considerations)

---

## 1. Current Retrieval Model

### 1.1 Architecture Overview

**Location:** [`engine/adapters/vector_store.py:62-113`](../engine/adapters/vector_store.py#L62-L113)

```
User Query
    ↓
[1] Text Embedding (SentenceTransformer)
    ↓
[2] Vector Search (ChromaDB - Cosine Similarity)
    ↓
[3] Quarantine Filtering (Metadata-based)
    ↓
[4] Return Top-K Documents
```

### 1.2 Technical Components

#### Embedding Model
- **Model:** `all-MiniLM-L6-v2` (SentenceTransformers)
- **Dimensions:** 384
- **Domain:** General-purpose semantic embeddings

#### Vector Database
- **Engine:** ChromaDB (Persistent)
- **Index:** HNSW (Hierarchical Navigable Small World)
- **Distance:** Cosine similarity
- **Storage:** Local filesystem (`chromadb_store/`)

#### Retrieval Process
```python
async def retrieve(
    query: str,
    k: int = 5,
    exclude_quarantined: bool = True
) -> List[Dict[str, Any]]:
    """
    Pure semantic vector search with quarantine filtering.

    Steps:
    1. Embed query using SentenceTransformer
    2. Query ChromaDB with cosine similarity
    3. Over-fetch by 3x if excluding quarantined (k*3)
    4. Filter out documents where is_quarantined=True
    5. Return top-K results
    """
```

### 1.3 Current Data Flow

```
Query: "How to mitigate CVE-2024-0004?"
    ↓
Embedding: [0.023, -0.145, 0.891, ..., 0.034] (384-dim vector)
    ↓
ChromaDB Search:
    - Compare query embedding to all document embeddings
    - Rank by cosine similarity
    - Return top-15 (k=5, over-fetch 3x for filtering)
    ↓
Filter:
    - Skip documents where metadata.is_quarantined == True
    - Collect until K=5 clean documents
    ↓
Results:
    1. CVE-2024-0003.txt (distance: 0.234) ← Semantically similar!
    2. CVE-2024-0002.txt (distance: 0.456)
    3. CVE-2024-0001.txt (distance: 0.512)
    4. security-best-practices.txt (distance: 0.578)
    5. CVE-2024-0006.txt (distance: 0.623)

❌ PROBLEM: CVE-2024-0004 not retrieved (poisoned doc quarantined OR
   semantically ranked lower than CVE-2024-0003)
```

### 1.4 Metadata Schema

Documents stored with rich metadata:

```json
{
  "doc_id": "CVE-2024-0003",
  "source": "debian.org/security",
  "category": "cve",
  "title": "Linux Kernel Use-After-Free Vulnerability",
  "is_quarantined": false,
  "quarantine_id": ""
}
```

**Current Usage:** Metadata is stored but **NOT used for filtering** during retrieval (only for quarantine status).

### 1.5 Strengths of Current Model

| Strength | Description | Impact |
|----------|-------------|--------|
| **Semantic Understanding** | Handles paraphrased queries, synonyms, conceptual matches | Good for exploratory queries |
| **Low Latency** | ~14ms embedding + ~8ms vector search | Fast user experience |
| **Quarantine-Aware** | Automatically excludes flagged documents | Security feature working |
| **Scalable** | HNSW index scales to 100K+ documents | High scale indexing |
| **Clean Architecture** | Async, modular, type-hinted | Easy to extend |

### 1.6 Weaknesses of Current Model

| Weakness | Description | Impact |
|----------|-------------|--------|
| **No Exact Matching** | Treats CVE IDs as semantic tokens, not identifiers | CVE-2024-0004 retrieves CVE-2024-0003 |
| **Vocabulary Mismatch** | Rare terms (product names, versions) poorly represented | "MySQL 8.0.x" may not match "MySQL 8.0.32" |
| **No Keyword Boosting** | Important terms (CVE IDs) weighted same as common words | Query signal diluted |
| **Single-Stage Retrieval** | No re-ranking or refinement | Lower precision |
| **Metadata Underutilized** | Rich metadata stored but not used for filtering | Missing structured query capability |

---

## 2. Identified Issues

### 2.1 Primary Issue: CVE ID Mismatch

**Problem Statement:**
Query `"How to mitigate CVE-2024-0004?"` retrieves `CVE-2024-0003.txt` instead of `CVE-2024-0004-poisoned.txt`.

**Root Cause Analysis:**

1. **Semantic Similarity Dominance**
   - CVE-2024-0003 contains strong remediation language:
     - "Update kernel to patched versions"
     - "Reboot systems after kernel update"
     - "Enable kernel hardening features"
   - Query contains "mitigate" (strong security term)
   - Embedding model matches on **security action semantics**, not CVE ID

2. **CVE ID as Text Token**
   - Embeddings treat "CVE-2024-0004" as sequence of tokens: `["CVE", "-", "2024", "-", "0004"]`
   - Model doesn't recognize this as a unique identifier
   - Similar CVE IDs have nearly identical embeddings:
     - `CVE-2024-0003` embedding ≈ `CVE-2024-0004` embedding (cosine ~0.98)

3. **No Exact Match Fallback**
   - System doesn't check: "Does query contain exact CVE ID?"
   - No priority boosting for identifier matches
   - Pure semantic ranking

**Impact:**
- **Demo Failure:** Both "unsafe" and "protected" modes return same answer (CVE-2024-0003 remediation)
- **No EDR Demonstration:** Poisoned doc never retrieved → can't show quarantine
- **User Confusion:** System appears to ignore specific CVE request

### 2.2 Secondary Issues

#### Issue 2.2.1: Query Language Mismatch
- User query: "How urgent is CVE-2024-0004?" (casual tone)
- Poisoned doc: "Low priority - Not urgent" (casual tone)
- Clean doc: "Severity: HIGH (CVSS 7.8)" (formal tone)
- **Problem:** Semantic matching should favor poisoned, but formal docs rank higher

#### Issue 2.2.2: Technical Term Vocabulary
- User query: "MySQL authentication bypass"
- Document uses: "MySQL auth issue", "login vulnerability"
- **Problem:** Synonym mismatch reduces relevance

#### Issue 2.2.3: Version Precision
- Query: "MySQL 8.0 vulnerability"
- Doc 1: "MySQL 8.0.x" (should match)
- Doc 2: "MySQL 8.1.x" (shouldn't match)
- **Problem:** Both rank similarly (semantic embeddings blur version differences)

### Fixes:
- Partially fixed with CVE ID matches
- Further fine tuning will be attempted for faster retrieval and better matches.
---

## 3. Phase 1: Quick Wins Implementation

### 3.1 Approach Overview

**Goal:** Fix CVE ID mismatch with minimal architectural changes (2-4 hours implementation).

**Strategy:** Metadata-enhanced retrieval with exact CVE matching

```
Query: "How to mitigate CVE-2024-0004?"
    ↓
[Stage 0: Entity Extraction]
    - Extract CVE IDs: ["CVE-2024-0004"]
    - Extract software: ["MySQL"] (future)
    ↓
[Stage 1: Query Augmentation]
    - Boost important terms in query text
    - Repeat CVE ID 3x: "CVE-2024-0004 CVE-2024-0004 CVE-2024-0004 how to mitigate"
    ↓
[Stage 2: Metadata-Filtered Retrieval]
    - IF CVE ID found in query:
        → ChromaDB WHERE filter: cve_ids $eq "CVE-2024-0004"
        → Retrieve with exact match filter
    - ELSE:
        → Pure semantic search (no filter)
    ↓
[Stage 3: Handle Quarantine]
    - IF exact match returned 0 documents:
        → Log: "CVE document quarantined or not found"
        → Return clear message to user about quarantine
    - ELSE:
        → Continue with EDR integrity checks
    ↓
[Stage 4: EDR Integrity Checks]
    - Evaluate retrieved documents
    - Quarantine suspicious docs
    ↓
Return Top-K Clean Documents or Quarantine Message
```

**Key Innovation:** Exact CVE matching with clear quarantine communication:
1. Try exact CVE match first (preferred for accuracy)
2. If no results, show clear quarantine message (user transparency)
3. Augmented query boosts CVE ID importance in embedding space

### 3.2 Implementation Plan

#### Component A: CVE ID Extraction

**File:** `engine/utils/entity_extractor.py` (NEW)

```python
import re
from typing import List, Dict, Any

class EntityExtractor:
    """
    Extract structured entities from queries and documents.

    Handles:
    - CVE IDs (CVE-YYYY-NNNNN format)
    - Software names (future: MySQL, Redis, Docker)
    - Version numbers (future: 8.0.x, 7.2.1)
    """

    CVE_PATTERN = re.compile(r'CVE-\d{4}-\d{4,7}', re.IGNORECASE)

    @staticmethod
    def extract_cve_ids(text: str) -> List[str]:
        """
        Extract CVE IDs from text.

        Examples:
            "How to fix CVE-2024-0004?" → ["CVE-2024-0004"]
            "CVE-2024-0001 and cve-2024-0002" → ["CVE-2024-0001", "CVE-2024-0002"]
        """
        matches = EntityExtractor.CVE_PATTERN.findall(text)
        return [m.upper() for m in matches]  # Normalize to uppercase

    @staticmethod
    def extract_entities(text: str) -> Dict[str, Any]:
        """
        Extract all entities from text.

        Returns:
            {
                "cve_ids": ["CVE-2024-0004"],
                "software": [],  # Future
                "versions": []   # Future
            }
        """
        return {
            "cve_ids": EntityExtractor.extract_cve_ids(text),
            "software": [],
            "versions": []
        }
```

**Testing:**
```python
# Test cases
assert extract_cve_ids("How to fix CVE-2024-0004?") == ["CVE-2024-0004"]
assert extract_cve_ids("cve-2024-1234 and CVE-2024-5678") == ["CVE-2024-1234", "CVE-2024-5678"]
assert extract_cve_ids("No CVEs here") == []
```

#### Component B: Metadata Enrichment

**File:** `engine/adapters/vector_store.py` (MODIFY)

**Change 1: Update `ingest_document()` to extract and store CVE IDs**

```python
async def ingest_document(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> None:
    """
    Add document to vector store with enriched metadata.

    NEW: Extract CVE IDs from content and add to metadata
    """
    from engine.utils.entity_extractor import EntityExtractor

    # Existing metadata defaults
    metadata.setdefault("is_quarantined", False)
    metadata.setdefault("quarantine_id", "")

    # NEW: Extract and store CVE IDs
    entities = EntityExtractor.extract_entities(content)
    metadata["cve_ids"] = entities["cve_ids"]

    # Generate embedding
    embedding = self.embedding_model.encode(content).tolist()

    # Add to ChromaDB
    self.collection.add(
        ids=[doc_id],
        documents=[content],
        metadatas=[metadata],
        embeddings=[embedding]
    )
```

**Change 2: Update `retrieve()` to support metadata filtering**

```python
async def retrieve(
    self,
    query: str,
    k: int = 5,
    exclude_quarantined: bool = True,
    metadata_filter: Optional[Dict[str, Any]] = None  # NEW parameter
) -> List[Dict[str, Any]]:
    """
    Retrieve documents with optional metadata filtering.

    NEW: Support ChromaDB WHERE filters for exact matching

    Args:
        query: Search query
        k: Number of results
        exclude_quarantined: Filter out quarantined docs
        metadata_filter: ChromaDB WHERE clause (e.g., {"cve_ids": {"$contains": "CVE-2024-0004"}})
    """
    from engine.utils.entity_extractor import EntityExtractor

    # NEW: Auto-detect CVE IDs and create filter if not provided
    if metadata_filter is None:
        cve_ids = EntityExtractor.extract_cve_ids(query)
        if cve_ids:
            # Create filter for first CVE ID found
            metadata_filter = {"cve_ids": {"$contains": cve_ids[0]}}

    # Generate query embedding
    query_embedding = self.embedding_model.encode(query).tolist()

    # Query ChromaDB with optional filter
    n_results = k * 3 if exclude_quarantined else k

    # NEW: Add where parameter if filter exists
    query_params = {
        "query_embeddings": [query_embedding],
        "n_results": min(n_results, self.collection.count()),
        "include": ["documents", "metadatas", "distances", "embeddings"]
    }
    if metadata_filter:
        query_params["where"] = metadata_filter

    results = self.collection.query(**query_params)

    # ... rest of filtering logic unchanged ...
```

#### Component C: Query Augmentation

**File:** `engine/utils/query_processor.py` (NEW)

```python
from typing import Tuple
from engine.utils.entity_extractor import EntityExtractor

class QueryProcessor:
    """
    Preprocess queries to improve retrieval accuracy.

    Phase 1: Term boosting for identifiers
    Future: Synonym expansion, intent classification
    """

    @staticmethod
    def augment_query(query: str, boost_factor: int = 3) -> str:
        """
        Boost important terms by repeating them.

        Strategy:
        - CVE IDs repeated 3x (high importance)
        - Original query appended (preserves semantic meaning)

        Example:
            Input: "How to mitigate CVE-2024-0004?"
            Output: "CVE-2024-0004 CVE-2024-0004 CVE-2024-0004 How to mitigate CVE-2024-0004?"

        Why this works:
        - Embedding models weight frequently occurring terms higher
        - TF-IDF-like effect in semantic space
        - Preserves original query for context
        """
        cve_ids = EntityExtractor.extract_cve_ids(query)

        if not cve_ids:
            return query  # No augmentation needed

        # Repeat each CVE ID boost_factor times
        boosted_terms = []
        for cve_id in cve_ids:
            boosted_terms.extend([cve_id] * boost_factor)

        # Combine: [boosted terms] + [original query]
        augmented = " ".join(boosted_terms) + " " + query
        return augmented

    @staticmethod
    def process_query(query: str) -> Tuple[str, dict]:
        """
        Full query preprocessing pipeline.

        Returns:
            (augmented_query, metadata_filter)
        """
        # Extract entities for filtering
        entities = EntityExtractor.extract_entities(query)

        # Create metadata filter if CVE IDs found
        metadata_filter = None
        if entities["cve_ids"]:
            metadata_filter = {"cve_ids": {"$contains": entities["cve_ids"][0]}}

        # Augment query for better semantic matching
        augmented_query = QueryProcessor.augment_query(query)

        return augmented_query, metadata_filter
```

**Testing:**
```python
# Test query augmentation
query = "How to mitigate CVE-2024-0004?"
augmented, filter = QueryProcessor.process_query(query)

assert augmented == "CVE-2024-0004 CVE-2024-0004 CVE-2024-0004 How to mitigate CVE-2024-0004?"
assert filter == {"cve_ids": {"$contains": "CVE-2024-0004"}}
```

#### Component D: Pipeline Integration

**File:** `engine/pipeline.py` (MODIFY)

**Change: Update query method to use new preprocessing**

```python
from engine.utils.query_processor import QueryProcessor

async def query(
    self,
    query_text: str,
    user_id: str = "default-user",
    k: int = 5
) -> Dict[str, Any]:
    """
    Execute RAG query with EDR protection.

    NEW: Phase 1 - Query preprocessing with entity extraction and augmentation
    """
    query_id = str(uuid4())

    # NEW: Preprocess query (augment + extract entities)
    augmented_query, metadata_filter = QueryProcessor.process_query(query_text)

    # Step 1: Retrieve documents with preprocessing
    # OLD: retrieved = await vector_store.retrieve(query_text, k=k, exclude_quarantined=True)
    # NEW: Use augmented query and metadata filter
    retrieved = await vector_store.retrieve(
        augmented_query,  # Boosted query
        k=k,
        exclude_quarantined=True,
        metadata_filter=metadata_filter  # Exact CVE ID match if present
    )

    # ... rest of pipeline unchanged (integrity checks, quarantine, generation) ...
```

### 3.3 Expected Behavior After Phase 1

#### Test Case 1: Exact CVE ID Query
```
Query: "How to mitigate CVE-2024-0004?"

BEFORE Phase 1:
  ❌ Retrieved: CVE-2024-0003.txt (semantic match on "mitigate")

AFTER Phase 1:
  ✅ Metadata filter: cve_ids CONTAINS "CVE-2024-0004"
  ✅ Augmented query: "CVE-2024-0004 CVE-2024-0004 CVE-2024-0004 How to mitigate CVE-2024-0004?"
  ✅ Retrieved: CVE-2024-0004-poisoned.txt (exact match)
  ✅ EDR detects: Trust 30%, Red Flags 34% → QUARANTINED
  ✅ Demo works: Unsafe mode shows malicious, Protected mode blocks
```

#### Test Case 2: Semantic Query (No CVE ID)
```
Query: "How do I secure MySQL databases?"

BEFORE Phase 1:
  ✅ Semantic search works fine

AFTER Phase 1:
  ✅ No CVE ID detected → No metadata filter
  ✅ No augmentation needed
  ✅ Falls back to pure semantic search (unchanged behavior)
  ✅ Backward compatible
```

#### Test Case 3: Multiple CVE IDs
```
Query: "Compare CVE-2024-0003 and CVE-2024-0004"

AFTER Phase 1:
  ✅ Extracts: ["CVE-2024-0003", "CVE-2024-0004"]
  ✅ Filters by first: CVE-2024-0003 (precedence rule)
  ✅ Augmented: "CVE-2024-0003 CVE-2024-0003 CVE-2024-0003 CVE-2024-0004 CVE-2024-0004 CVE-2024-0004 Compare..."
  ✅ Retrieved: Both documents (if k=5 has room)

  Future enhancement: Multi-CVE filter logic
```

### 3.4 Code Changes Summary

| File | Change Type | Lines Changed | Description |
|------|-------------|---------------|-------------|
| `engine/utils/entity_extractor.py` | NEW | ~40 | CVE ID extraction utility |
| `engine/utils/query_processor.py` | NEW | ~50 | Query augmentation logic |
| `engine/adapters/vector_store.py` | MODIFY | ~20 | Add metadata filtering support |
| `engine/pipeline.py` | MODIFY | ~5 | Integrate query preprocessing |
| `tests/test_phase1_retrieval.py` | NEW | ~100 | Unit tests for new components |

**Total:** ~215 lines of code

### 3.5 Migration Steps

1. **Create new utility modules** (no breaking changes)
2. **Re-ingest corpus** with CVE ID metadata:
   ```bash
   python3 ingest_corpus.py --force-refresh
   ```
3. **Run tests** to verify metadata extraction:
   ```bash
   pytest tests/test_phase1_retrieval.py -v
   ```
4. **Deploy** (backward compatible - falls back to semantic if no CVE ID)

### 3.6 Phase 1 Limitations

| Limitation | Description | Mitigation |
|------------|-------------|------------|
| **Single CVE Priority** | If multiple CVE IDs in query, only first is filtered | Phase 2: Multi-entity filtering |
| **No Software Filtering** | "MySQL CVE" doesn't filter by software | Phase 2: Software entity extraction |
| **No Version Precision** | "8.0.x vs 8.1.x" still blurred | Phase 3: Structured version parsing |
| **Keyword Boosting Only** | Augmentation is simple term repetition | Phase 2: BM25 hybrid search |
| **No Re-ranking** | Still single-stage retrieval | Phase 2: Cross-encoder re-ranking |

---

## 4. Detailed Improvement Suggestions

### 4.1 Hybrid Search (BM25 + Vector)

**Priority:** HIGH (Phase 2 candidate)
**Complexity:** Medium (6-8 hours)
**Impact:** Addresses all keyword matching weaknesses

#### How It Works

Combine two complementary search paradigms:

1. **BM25 (Sparse Retrieval)** - Keyword matching based on term frequency
   - Excels at: Exact terms, rare terms, identifiers (CVE IDs)
   - Formula: `score(q,d) = Σ IDF(q_i) * (f(q_i,d) * (k1+1)) / (f(q_i,d) + k1 * (1-b+b*|d|/avgdl))`
   - Parameters:
     - `k1`: Term saturation (default 1.2)
     - `b`: Length normalization (default 0.75)

2. **Dense Vector Search** - Semantic similarity (current approach)
   - Excels at: Synonyms, paraphrasing, conceptual queries
   - Formula: `score(q,d) = cosine(embed(q), embed(d))`

3. **Reciprocal Rank Fusion (RRF)** - Combine rankings
   - Formula: `score(d) = Σ 1/(k + rank_bm25(d)) + α * 1/(k + rank_vector(d))`
   - Parameters:
     - `k`: Rank offset (default 60)
     - `α`: Vector weight (default 1.0, adjust to favor semantic vs keyword)

#### Architecture

```python
# New class in engine/adapters/hybrid_retriever.py

from rank_bm25 import BM25Okapi
import numpy as np

class HybridRetriever:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.bm25_index = None
        self.doc_ids = []

    async def build_bm25_index(self, documents: List[Dict]):
        """
        Build BM25 index from corpus.

        Run once during ingestion or on startup.
        """
        # Tokenize documents
        tokenized_docs = [doc['content'].lower().split() for doc in documents]
        self.doc_ids = [doc['doc_id'] for doc in documents]

        # Build BM25 index
        self.bm25_index = BM25Okapi(tokenized_docs)

    async def hybrid_retrieve(
        self,
        query: str,
        k: int = 5,
        alpha: float = 0.5,  # Weight: 0=pure BM25, 1=pure vector
        rrf_k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval with RRF fusion.

        Args:
            alpha: Vector search weight (0-1)
            rrf_k: Rank offset for RRF formula
        """
        # 1. BM25 Search
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25_index.get_scores(tokenized_query)
        bm25_ranking = np.argsort(bm25_scores)[::-1]  # Descending

        # 2. Vector Search
        vector_results = await self.vector_store.retrieve(query, k=k*2)
        vector_ranking = {doc['doc_id']: i for i, doc in enumerate(vector_results)}

        # 3. RRF Fusion
        rrf_scores = {}

        # BM25 contribution
        for rank, doc_idx in enumerate(bm25_ranking[:k*2]):
            doc_id = self.doc_ids[doc_idx]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + (1-alpha) / (rrf_k + rank)

        # Vector contribution
        for doc_id, rank in vector_ranking.items():
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + alpha / (rrf_k + rank)

        # 4. Sort by RRF score and return top-K
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        # Fetch full documents
        result_docs = []
        for doc_id, score in sorted_docs[:k]:
            # Lookup from vector_results or fetch from DB
            doc = next((d for d in vector_results if d['doc_id'] == doc_id), None)
            if doc:
                doc['rrf_score'] = score
                result_docs.append(doc)

        return result_docs
```

#### Implementation Checklist

- [ ] Install dependency: `pip install rank-bm25`
- [ ] Create `engine/adapters/hybrid_retriever.py`
- [ ] Build BM25 index during corpus ingestion
- [ ] Add hybrid retrieval option to pipeline
- [ ] Add dashboard toggle: "Retrieval Mode: [Vector | Hybrid | BM25]"
- [ ] Benchmark: Compare precision@5 for CVE queries
- [ ] Tune alpha parameter (0.5 = balanced, 0.3 = favor keywords, 0.7 = favor semantic)

#### PROS

| Advantage | Explanation |
|-----------|-------------|
| **Best of Both Worlds** | BM25 catches exact CVE IDs, Vector handles paraphrasing |
| **Proven Approach** | Used by Elasticsearch, Weaviate, Pinecone |
| **Tunable Balance** | Adjust alpha based on query type (lookup vs exploration) |
| **No Training Required** | BM25 is unsupervised (just build index) |
| **Handles Rare Terms** | BM25 IDF gives high weight to unique identifiers |
| **Robust to Typos** | Vector search still works if BM25 fails on misspelling |

#### CONS

| Disadvantage | Explanation | Mitigation |
|--------------|-------------|------------|
| **Extra Index Storage** | BM25 requires tokenized corpus (~20% overhead) | Use compressed token storage |
| **Slower Ingestion** | Must build both BM25 and vector index | Build asynchronously |
| **Tuning Complexity** | Requires alpha parameter tuning | Start with 0.5, tune on eval set |
| **Memory Overhead** | BM25 index kept in RAM (~50MB for 1K docs) | Acceptable for most deployments |
| **No Semantic in BM25** | BM25 alone fails on synonyms | RRF fusion mitigates |

#### Expected Impact

**Test Case: CVE-2024-0004 Query**

| Approach | Top Result | Rank of Correct Doc |
|----------|------------|---------------------|
| Pure Vector (current) | CVE-2024-0003 | Not retrieved |
| Phase 1 (metadata filter) | CVE-2024-0004 | #1 (if filter works) |
| **Hybrid (BM25+Vector)** | **CVE-2024-0004** | **#1 (robust)** |

**BM25 Scoring:**
- "CVE-2024-0004" appears 3x in CVE-2024-0004 doc → High TF
- "CVE-2024-0004" rare in corpus → High IDF
- BM25 score: ~8.5 (strong signal)

**Vector Scoring:**
- CVE-2024-0003 has better "mitigation" language → Slightly higher
- But RRF combines both → CVE-2024-0004 wins overall

---

### 4.2 Cross-Encoder Re-Ranking

**Priority:** MEDIUM (Phase 2 candidate)
**Complexity:** Medium (4-6 hours)
**Impact:** +10-15% precision improvement

#### How It Works

Two-stage retrieval:

```
Stage 1: Fast Retrieval (Current approach)
    → Retrieve top-20 candidates using vector/hybrid search
    → Goal: High recall (cast wide net)
    ↓
Stage 2: Cross-Encoder Re-Ranking
    → Score each (query, document) pair with cross-encoder model
    → Model sees full interaction between query and doc
    → Re-rank based on cross-encoder scores
    → Return top-5
    → Goal: High precision (refine results)
```

**Key Difference from Bi-Encoder (Current):**

| Bi-Encoder (Current) | Cross-Encoder (Re-Ranking) |
|----------------------|----------------------------|
| Query and doc encoded **separately** | Query and doc encoded **together** |
| Fast: Embed once, compare many | Slow: Forward pass per pair |
| No interaction between Q and D | Full attention between Q and D |
| Used for retrieval (100K docs) | Used for re-ranking (top-20) |

#### Architecture

```python
# New class in engine/adapters/reranker.py

from sentence_transformers import CrossEncoder

class CrossEncoderReranker:
    """
    Re-rank retrieved documents using cross-encoder model.

    Model: ms-marco-MiniLM-L-6-v2
    - Trained on MS MARCO passage ranking dataset
    - Input: [query, document] pair
    - Output: Relevance score (0-1)
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = CrossEncoder(model_name)

    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Re-rank documents using cross-encoder scores.

        Args:
            query: User query
            documents: Retrieved candidates (typically 10-20)
            top_k: Number of final results

        Returns:
            Top-K documents sorted by cross-encoder score
        """
        if not documents:
            return []

        # Prepare pairs: [(query, doc1), (query, doc2), ...]
        pairs = [(query, doc['content'][:512]) for doc in documents]  # Truncate to 512 tokens

        # Score all pairs (batched for efficiency)
        scores = self.model.predict(pairs, batch_size=32)

        # Add scores to documents
        for doc, score in zip(documents, scores):
            doc['rerank_score'] = float(score)
            doc['original_rank'] = documents.index(doc)

        # Sort by cross-encoder score (descending)
        reranked = sorted(documents, key=lambda d: d['rerank_score'], reverse=True)

        return reranked[:top_k]
```

#### Integration

**File:** `engine/pipeline.py`

```python
from engine.adapters.reranker import CrossEncoderReranker

class RAGPipeline:
    def __init__(self):
        self.vector_store = vector_store
        self.reranker = CrossEncoderReranker()  # NEW

    async def query(self, query_text: str, k: int = 5):
        # Stage 1: Over-fetch candidates
        candidates = await vector_store.retrieve(query_text, k=k*4)  # Get 20 for k=5

        # Stage 2: Re-rank with cross-encoder (NEW)
        reranked = await self.reranker.rerank(query_text, candidates, top_k=k)

        # Continue with integrity checks on reranked docs
        # ...
```

#### PROS

| Advantage | Explanation |
|-----------|-------------|
| **Highest Precision** | Cross-encoders outperform bi-encoders on all benchmarks (MS MARCO, BEIR) |
| **Query-Document Interaction** | Model sees both together, captures nuanced relevance |
| **Proven Effective** | +10-15% precision improvement in systems |
| **Easy Integration** | Drop-in replacement for re-ranking step |
| **Pre-trained Models** | No training needed, use MS MARCO models |
| **Corrects Vector Errors** | Fixes mistakes from Stage 1 retrieval |

#### CONS

| Disadvantage | Explanation | Mitigation |
|--------------|-------------|------------|
| **Latency Overhead** | ~200ms for 20 candidates (10ms per pair) | Acceptable for k=20, limit over-fetch |
| **Not Scalable for Retrieval** | Can't run on 100K docs | Only use for re-ranking top candidates |
| **Model Size** | MiniLM: 80MB, Large models: 400MB+ | Use MiniLM variant (sufficient quality) |
| **GPU Benefits** | 10x faster on GPU, slower on CPU | Run on CPU, optimize batch size |
| **Another Model to Manage** | Adds deployment complexity | Worth it for quality gain |



### 4.3 Fine-Tuned Domain Embeddings

**Priority:** LOW (Phase 3, nice-to-have)
**Complexity:** HIGH (2-3 days)
**Impact:** +15-20% recall improvement on security queries

#### How It Works

Customize embedding model for security domain:

1. **Collect Training Data**
   - Positive pairs: (query, relevant CVE doc)
     - "How to fix CVE-2024-0004?" → CVE-2024-0004.txt
   - Negative pairs: (query, irrelevant CVE doc)
     - "How to fix CVE-2024-0004?" → CVE-2024-0003.txt
   - Need ~1000 pairs minimum

2. **Fine-Tune SentenceTransformer**
   - Start with `all-MiniLM-L6-v2` (current model)
   - Fine-tune with contrastive loss:
     - Pull positive pairs closer in embedding space
     - Push negative pairs apart
   - Train for 3-5 epochs

3. **Evaluate & Deploy**
   - Test on held-out CVE queries
   - Measure recall@5, precision@5, MRR
   - Deploy if metrics improve >10%

#### Training Recipe

```python
# training/finetune_embeddings.py

from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

# 1. Prepare training data
train_examples = [
    InputExample(texts=['How to fix CVE-2024-0004?', 'CVE-2024-0004 content...'], label=1.0),  # Positive
    InputExample(texts=['How to fix CVE-2024-0004?', 'CVE-2024-0003 content...'], label=0.0),  # Negative
    # ... 1000 more examples
]

# 2. Load base model
model = SentenceTransformer('all-MiniLM-L6-v2')

# 3. Define loss (Contrastive or MultipleNegativesRanking)
train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)
train_loss = losses.CosineSimilarityLoss(model)

# 4. Fine-tune
model.fit(
    train_objectives=[(train_dataloader, train_loss)],
    epochs=3,
    warmup_steps=100,
    output_path='./models/cve-embeddings-v1'
)
```

#### Data Collection Strategy

| Source | Examples | Effort |
|--------|----------|--------|
| **Synthetic (GPT-4)** | Generate queries for each CVE: "How to fix X?", "Is X critical?" | Low (1 hour) |
| **Query Logs** | Real user queries from demo | Medium (1 day) |
| **Manual Annotation** | Security experts label query-doc pairs | High (3 days) |

**Recommended:** Start with synthetic, validate with small manual set.

#### PROS

| Advantage | Explanation |
|-----------|-------------|
| **Domain Adaptation** | Model learns security-specific vocabulary |
| **CVE ID Importance** | Training emphasizes exact CVE matching |
| **Long-term Investment** | Improves over time with more data |
| **Unified Model** | Single embedding model, no hybrid complexity |
| **Better Generalization** | Handles unseen CVEs better than keyword matching |

#### CONS

| Disadvantage | Explanation | Mitigation |
|--------------|-------------|------------|
| **Data Hungry** | Needs 1000+ labeled pairs | Use synthetic data initially |
| **Training Infrastructure** | GPU required for fine-tuning | Cloud VM for 3 hours (~$5) |
| **Maintenance Overhead** | Re-train as domain evolves | Quarterly retraining schedule |
| **Risk of Overfitting** | May worsen on general queries | Keep general queries in training set |
| **Evaluation Complexity** | Need test set to validate | Create 100-example test set upfront |

#### When to Use

- **Yes:** If you have 500+ real user queries with labels
- **Yes:** If system used long-term (ROI on training effort)
- **No:** For prototype/demo (not worth effort)
- **No:** If query patterns change frequently (model becomes stale)

---

### 4.4 Query Expansion with Synonyms

**Priority:** LOW (Phase 2, optional)
**Complexity:** LOW (2-3 hours)
**Impact:** +5-8% recall on synonym-heavy queries

#### How It Works

Expand query with known synonyms before search:

```
Original: "MySQL authentication bypass"
    ↓
Expand: "MySQL authentication bypass auth login access"
    ↓
Search: Retrieves docs with any of these terms
```

#### Implementation

```python
# engine/utils/synonym_expander.py

class SynonymExpander:
    """
    Expand queries with domain synonyms.
    """

    SYNONYMS = {
        "authentication": ["auth", "login", "access", "credential"],
        "bypass": ["circumvent", "skip", "evade"],
        "vulnerability": ["vuln", "CVE", "security issue", "exploit"],
        "mitigation": ["remediation", "fix", "patch", "workaround"],
        "privilege escalation": ["privesc", "root access", "elevation"],
        # ... 50+ more
    }

    @staticmethod
    def expand(query: str, max_expansions: int = 2) -> str:
        """
        Add synonyms to query.

        Args:
            max_expansions: Max synonyms per term
        """
        words = query.lower().split()
        expanded = query  # Start with original

        for word in words:
            if word in SynonymExpander.SYNONYMS:
                synonyms = SynonymExpander.SYNONYMS[word][:max_expansions]
                expanded += " " + " ".join(synonyms)

        return expanded
```

#### PROS

| Advantage | Explanation |
|-----------|-------------|
| **Simple to Implement** | Dictionary-based, no models |
| **Handles Vocabulary Gap** | "auth" retrieves "authentication" docs |
| **Low Latency** | <1ms overhead |
| **Explainable** | Clear why a doc was retrieved |

#### CONS

| Disadvantage | Explanation | Mitigation |
|--------------|-------------|------------|
| **Query Drift** | Over-expansion retrieves irrelevant docs | Limit to 2 synonyms per term |
| **Maintenance** | Synonym dict needs updates | Quarterly review |
| **Context-Blind** | "Bypass" in "bypass proxy" vs "bypass auth" | Use for security domain only |
| **Redundant with Vector** | Embeddings already handle synonyms | Skip if using fine-tuned embeddings |

#### When to Use

- **Yes:** If Phase 1 insufficient and hybrid search not implemented
- **No:** If hybrid search (BM25) or fine-tuned embeddings used (redundant)

---

### 4.5 Multi-Hop Agentic Retrieval

**Priority:** LOW (Phase 3, research)
**Complexity:** VERY HIGH (3-5 days)
**Impact:** Handles complex multi-step queries

#### How It Works

LLM agent decides retrieval strategy dynamically:

```
User: "Compare CVE-2024-0003 and CVE-2024-0004 impact"
    ↓
Agent Plan:
  1. Retrieve CVE-2024-0003
  2. Retrieve CVE-2024-0004
  3. Compare severity scores
  4. Synthesize answer
    ↓
Execute plan with iterative retrieval
```

#### Use Cases

- Comparison queries ("X vs Y")
- Multi-step reasoning ("If X affected, what about Y?")
- Clarification ("Did you mean CVE-2024-0004 or 0005?")

#### PROS

| Advantage | Explanation |
|-----------|-------------|
| **Handles Complexity** | Multi-step reasoning beyond simple retrieval |
| **Adaptive** | Changes strategy per query type |
| **Explainable** | Agent shows reasoning steps |

#### CONS

| Disadvantage | Explanation |
|--------------|-------------|
| **High Latency** | Multiple LLM calls (500ms+ overhead) |
| **Unpredictable** | Agent may fail or loop |
| **Complex to Debug** | Multi-agent orchestration hard to test |
| **Overkill** | 95% of queries don't need it |

#### When to Use

- **Yes:** If supporting power users with complex analytical queries
- **No:** For simple lookup/mitigation queries (current use case)

---

## 5. Implementation Roadmap

### Phase 1: Quick Wins (Week 1)
**Goal:** Fix CVE ID mismatch
**Effort:** 2-4 hours
**Components:**
- [x] Entity extraction (CVE IDs)
- [x] Metadata filtering
- [x] Query augmentation
- [x] Pipeline integration

**Success Metric:** CVE-2024-0004 query retrieves correct doc (100% precision for exact CVE)

---

### Phase 2: Hybrid Search (Week 2)
**Goal:** Robust keyword + semantic search
**Effort:** 6-8 hours
**Components:**
- [ ] BM25 index builder
- [ ] RRF fusion
- [ ] Cross-encoder re-ranking
- [ ] Performance benchmarks

**Success Metric:** +15% precision on CVE query test set (n=50)

---

### Phase 3: Advanced Features (Month 2+)
**Goal:** Domain adaptation
**Effort:** 2-3 days
**Components:**
- [ ] Collect training data (1000 query-doc pairs)
- [ ] Fine-tune embeddings
- [ ] A/B test vs. hybrid search
- [ ] Deploy if >10% improvement

**Success Metric:** +20% recall on long-tail queries

---

## 6. Performance Considerations

Created prototype for demo purpose. To be determined. 

---

## Appendix A: Testing Strategy

### A.1 Test Queries

**Exact Match (CVE ID present):**
1. `"How to mitigate CVE-2024-0004?"`
2. `"What is CVE-2024-0004?"`
3. `"CVE-2024-0004 severity"`

**Semantic (No CVE ID):**
4. `"MySQL authentication vulnerabilities"`
5. `"How to secure Redis from injection?"`
6. `"Docker container escape risks"`

**Multi-CVE:**
7. `"Compare CVE-2024-0003 and CVE-2024-0004"`

### A.2 Expected Results (Phase 1)

| Query | Top Result | EDR Action |
|-------|------------|------------|
| #1 | CVE-2024-0004-poisoned.txt | QUARANTINE |
| #2 | CVE-2024-0004-poisoned.txt | QUARANTINE |
| #3 | CVE-2024-0004-poisoned.txt | QUARANTINE |
| #4 | Best-practices.txt | PASS |
| #5 | CVE-2024-0008-poisoned.txt (Redis) | QUARANTINE |
| #6 | CVE-2024-0005-poisoned.txt (Docker) | QUARANTINE |
| #7 | CVE-2024-0003.txt + CVE-2024-0004-poisoned.txt | PARTIAL QUARANTINE |

### A.3 Metrics

**Precision@5:** % of top-5 results relevant
**Recall@5:** % of relevant docs in top-5
**MRR (Mean Reciprocal Rank):** Average of 1/rank_of_first_relevant
**Quarantine Rate:** % of poisoned docs caught by EDR

**Target:**
- Precision@5: >90% (up from ~70%)
- Recall@5: >85% (up from ~65%)
- Poisoned Doc Quarantine: 100% (already at 100%)

---

## Appendix B: ChromaDB Metadata Filter Reference

### B.1 Supported Operators

| Operator | Syntax | Example |
|----------|--------|---------|
| **Equals** | `{"field": "value"}` | `{"category": "cve"}` |
| **Not Equals** | `{"field": {"$ne": "value"}}` | `{"source": {"$ne": "unknown"}}` |
| **Contains** | `{"field": {"$contains": "value"}}` | `{"cve_ids": {"$contains": "CVE-2024-0004"}}` |
| **In** | `{"field": {"$in": ["v1", "v2"]}}` | `{"category": {"$in": ["cve", "advisory"]}}` |
| **And** | `{"$and": [{...}, {...}]}` | `{"$and": [{"category": "cve"}, {"source": "nvd.nist.gov"}]}` |
| **Or** | `{"$or": [{...}, {...}]}` | `{"$or": [{"severity": "high"}, {"severity": "critical"}]}` |

### B.2 Phase 1 Filter Examples

**Exact CVE Match:**
```python
{"cve_ids": {"$contains": "CVE-2024-0004"}}
```

**CVE + Source Filter:**
```python
{
  "$and": [
    {"cve_ids": {"$contains": "CVE-2024-0004"}},
    {"source": {"$ne": "unknown"}}
  ]
}
```

**Exclude Quarantined:**
```python
{"is_quarantined": False}
```

---

## Appendix C: Recommended Tools & Libraries

### C.1 Phase 1 Dependencies

```bash
# Already installed
pip install sentence-transformers  # Embedding model
pip install chromadb              # Vector DB

# No new dependencies needed for Phase 1
```

### C.2 Phase 2 Dependencies

```bash
# BM25 hybrid search
pip install rank-bm25

# Cross-encoder re-ranking
pip install sentence-transformers  # Already installed, includes CrossEncoder

# Optional: Better tokenization
pip install nltk
python -m nltk.downloader punkt
```

### C.3 Phase 3 Dependencies (Future)

```bash
# Fine-tuning embeddings
pip install torch transformers datasets

# Evaluation metrics
pip install scikit-learn ranx

# Query analysis
pip install spacy
python -m spacy download en_core_web_sm
```

---

## Document Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.3 | 2025-02-06 | Removed semantic fallback, updated to reflect exact match with clear quarantine messaging |
| 1.2 | 2025-02-06 | Added intelligent fallback implementation details |
| 1.0 | 2025-02-05 | Initial document: Current model + Phase 1 plan + Suggestions |

---

**Next Steps:**
1. Review this document with team
2. Approve Phase 1 implementation plan
3. Begin implementation: Entity extraction module
4. Run tests and benchmark before/after
5. Plan Phase 2 kickoff meeting
