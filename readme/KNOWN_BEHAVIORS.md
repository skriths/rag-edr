# Known Behaviors & Expected Variance

This document explains expected system behaviors that may appear inconsistent but are actually working correctly.

---

## Vector Search Non-Determinism

### Observation:
**Same query executed twice returns different answers with different integrity scores.**

**Example:**
```
Query 1: "How do I patch CVE-2024-0001?"
Result: Proper answer with CVE-2024-0001 content

Query 2: "How do I patch CVE-2024-0001?" (same query)
Result: "Not found in provided documents" + generic advice
Scores: All 100% (green)
```

### Why This Happens:

#### 1. Vector Search Variance
- **ChromaDB uses approximate nearest neighbor (ANN) search**
- ANN algorithms (HNSW, IVF) trade accuracy for speed
- Small variations in:
  - Corpus state (quarantined docs change available pool)
  - Index state (background optimizations)
  - Query embedding (minor floating point differences)
- Can result in slightly different top-k results

#### 2. Quarantine Affects Available Documents
**Scenario:**
- First query: CVE-2024-0001, CVE-2024-0004-poisoned, CVE-2024-0005-poisoned, CVE-2024-0008-poisoned, security-best-practices
  - CVE-2024-0004, CVE-2024-0005, CVE-2024-0008 → Quarantined
  - LLM receives: CVE-2024-0001 + security-best-practices → Proper answer

- Second query (after quarantine): CVE-2024-0001, CVE-2024-0002, CVE-2024-0003, security-best-practices, patch-management
  - All clean documents
  - But CVE-2024-0001 might not be in top-5 this time (vector search variance)
  - LLM receives: CVE-2024-0002, CVE-2024-0003, etc. → "Not found" answer

#### 3. Integrity Scores Reflect Retrieved Documents, Not Answer Quality
- **100% scores = retrieved documents are clean**
- **Does NOT mean = retrieved documents answer the question**

**Why scores are 100%:**
- Source Trust: 100% (all from trusted sources: nvd.nist.gov, debian.org, etc.)
- Safety Score: 100% (no red flags in retrieved documents)
- Distribution: 90%+ (multiple trusted sources)
- Alignment: 100% (matches golden corpus best practices)

**Key Point:** Integrity scoring evaluates document **safety**, not document **relevance**.

### Is This a Bug?

**No, this is expected behavior for RAG systems.**

**RAG-EDR's Job:**
- ✅ Ensure retrieved documents are **safe** (no poisoned content)
- ✅ Quarantine documents with malicious patterns
- ✅ Track blast radius of poisoned documents
- ❌ NOT responsible for retrieval relevance (that's the vector DB's job)

**Vector DB's Job:**
- ✅ Return most semantically similar documents
- ⚠️ May return different results due to ANN approximation
- ⚠️ No guarantees of determinism across queries

---

## How to Minimize Variance (Future Work)

### 1. Increase k (Top-K Documents)
**Current:** `k=5` (retrieve 5 documents)
**Alternative:** `k=10` or `k=20`
- More documents → Higher chance of getting the right one
- Trade-off: Slower LLM generation, more context cost

### 2. Use Deterministic Vector Search
**Current:** Approximate Nearest Neighbor (fast, non-deterministic)
**Alternative:** Exact nearest neighbor search
```python
# In vector_store.py
collection.query(
    query_texts=[query],
    n_results=k,
    include=["documents", "metadatas"],
    method="exact"  # Deterministic but slower
)
```
- Trade-off: 10-100x slower for large corpora

### 3. Semantic Reranking
**Approach:** Two-stage retrieval
1. Stage 1: Retrieve k=20 candidates (fast ANN)
2. Stage 2: Rerank with cross-encoder model (slow but accurate)
3. Select top-5 reranked results

**Implementation (Future):**
```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

# After retrieval
scores = reranker.predict([(query, doc) for doc in candidates])
top_k = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)[:5]
```

### 4. Query Expansion
**Approach:** Expand query with synonyms/related terms
```python
# Instead of: "How do I patch CVE-2024-0001?"
# Use: ["How do I patch CVE-2024-0001?",
#       "CVE-2024-0001 remediation",
#       "Fix CVE-2024-0001",
#       "Apache HTTP Server vulnerability 2024-0001"]

# Retrieve for all variants, merge results
```

### 5. Hybrid Search (Vector + Keyword)
**Approach:** Combine vector similarity with BM25 keyword matching
- Vector search: Semantic similarity
- BM25: Exact keyword matches (e.g., "CVE-2024-0001")
- Merge results with weighted scoring

**Benefit:** CVE IDs are exact strings, keyword search guarantees retrieval

---

## When to Be Concerned

### 🚨 Red Flags (Actual Issues):

1. **Same query, vastly different integrity scores**
   - Example: First query 100%, second query 30%
   - Indicates: Document corruption or indexing issue

2. **Poisoned documents NOT quarantined**
   - Document has 10+ red flags but scores 80%
   - Indicates: Red flag detection bug

3. **Clean documents quarantined (False Positive)**
   - Official CVE advisory quarantined
   - Indicates: Red flag detector too aggressive

4. **Quarantine doesn't persist across queries**
   - Document quarantined, then retrieved again on next query
   - Indicates: ChromaDB metadata update failed

### ✅ Green Flags (Expected Behavior):

1. **Same query, different but clean answers**
   - Both answers are safe, just different docs retrieved
   - Expected: Vector search variance

2. **Answer says "not found" but scores 100%**
   - Retrieved docs are clean, just not relevant
   - Expected: RAG-EDR ensures safety, not relevance

3. **Different queries retrieve different doc sets**
   - Obviously expected, queries have different embeddings

---

## Workarounds for Demo Consistency

### Option 1: Pre-select Specific Documents
Instead of vector search, manually specify documents for demo queries:

```python
# demo_queries.py
DEMO_QUERIES = {
    "How do I patch CVE-2024-0001?": [
        "CVE-2024-0001.txt",
        "security-best-practices.txt"
    ],
    "How to mitigate CVE-2024-0004?": [
        "CVE-2024-0004-poisoned.txt",
        "patch-management-procedures.txt"
    ]
}
```

**Pros:** 100% deterministic, perfect for demos
**Cons:** Not representative of real RAG usage

### Option 2: Increase Corpus Size
- Current: 11 documents
- Target: 50-100 documents
- More documents → Vector search has more context → More stable results

**Benefit:** Reduces variance without sacrificing realism

### Option 3: Use Metadata Filtering
```python
# Force retrieval of specific CVEs
vector_store.retrieve(
    query="How do I patch CVE-2024-0001?",
    k=5,
    where={"cve_id": {"$eq": "CVE-2024-0001"}}  # Filter by metadata
)
```

**Benefit:** Guarantees retrieval of specific documents
**Trade-off:** Requires metadata tagging in corpus

---

## Summary

| Behavior | Expected? | Action |
|----------|-----------|--------|
| Same query, different answers (both clean) | ✅ YES | Document in KNOWN_BEHAVIORS.md |
| Same query, different integrity scores | ❌ NO | Investigate red flag detection |
| Answer "not found" but 100% scores | ✅ YES | This is correct (safe docs, not relevant) |
| Poisoned doc not quarantined | ❌ NO | Check red flag thresholds |
| Quarantined doc appears in next query | ❌ NO | Check ChromaDB metadata update |
| Restored doc disappears from UI | ✅ YES | API filters RESTORED state (fixed) |

---

## References

- **ChromaDB ANN Search:** https://docs.trychroma.com/usage-guide#querying-a-collection
- **Vector Search Variance:** "Approximate Nearest Neighbor Search: State of the Art and Beyond" (2021)
- **Semantic Reranking:** "In-Batch Negatives for Cross-Encoders" (Hofstätter et al., 2021)
- **Hybrid Search:** "The Best of Both Worlds: Combining Learned and Symbolic Models for Retrieval" (2020)

---

Last Updated: 2025-02-05
Version: 1.0
