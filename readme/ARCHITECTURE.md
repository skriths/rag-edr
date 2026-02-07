# RAGShield Architecture

## Where RAGShield Sits

RAGShield is a **middleware security layer** that sits between document retrieval and LLM generation in RAG (Retrieval-Augmented Generation) systems.

### Traditional RAG Flow (Vulnerable)

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐      ┌──────────┐
│   User      │─────▶│  Vector DB   │─────▶│     LLM     │─────▶│  Answer  │
│   Query     │      │  (Retrieve)  │      │  (Generate) │      │          │
└─────────────┘      └──────────────┘      └─────────────┘      └──────────┘
                            │
                            │ ALL documents sent to LLM
                            │ (including poisoned ones)
                            ▼
                     ⚠️ NO INTEGRITY CHECKS
```

**Problem:** Any poisoned document retrieved goes directly to the LLM, contaminating the answer.

---

### RAGShield Protected Flow

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐      ┌─────────────┐      ┌──────────┐
│   User      │─────▶│  Vector DB   │─────▶│    RAGShield      │─────▶│     LLM     │─────▶│  Answer  │
│   Query     │      │  (Retrieve)  │      │ Integrity Layer │      │  (Generate) │      │          │
└─────────────┘      └──────────────┘      └─────────────────┘      └─────────────┘      └──────────┘
                            │                       │                       │
                            │                       ▼                       │
                            │              ┌─────────────────┐              │
                            │              │ 4 Signal Check: │              │
                            │              │ - Trust Score   │              │
                            │              │ - Red Flags     │              │
                            │              │ - Anomaly       │              │
                            │              │ - Semantic Drift│              │
                            │              └─────────────────┘              │
                            │                       │                       │
                            │                       ▼                       │
                            │              2+ signals < 50%?               │
                            │                       │                       │
                            │                  YES  │  NO                  │
                            │                       │                       │
                            │                   ┌───┴───┐                  │
                            │                   │       │                  │
                            ▼                   ▼       ▼                  │
                   ┌─────────────────┐   ┌──────────┐ │                  │
                   │ Quarantine Vault│◀──│Quarantine│ │                  │
                   │ (Audit Trail)   │   └──────────┘ │                  │
                   └─────────────────┘                 │                  │
                            │                          │                  │
                            │                    CLEAN DOCS ONLY ─────────┘
                            ▼
                   ┌─────────────────┐
                   │ Blast Radius    │
                   │ Analysis        │
                   └─────────────────┘
```

**Key Point:** RAGShield acts as a **security gateway**, inspecting documents BEFORE they reach the LLM.

---

## System Components

### 1. Retrieval Layer (ChromaDB)
**What it does:** Vector similarity search to find relevant documents
**RAGShield integration:** Soft-delete quarantined documents via `is_quarantined` metadata flag

### 2. Detection Layer (RAGShield Core)
**What it does:** Multi-signal integrity evaluation
**Components:**
- **Trust Scorer** - Source reputation lookup
- **Red Flag Detector** - Keyword pattern matching (5 categories)
- **Anomaly Scorer** - Source diversity and trust variance
- **Semantic Drift Detector** - Embedding similarity to golden corpus
- **Integrity Engine** - Orchestrates 4 signals with 2-of-4 trigger rule

### 3. Response Layer (RAGShield)
**What it does:** Quarantine and impact analysis
**Components:**
- **Quarantine Vault** - Isolated storage with state machine (QUARANTINED → CONFIRMED_MALICIOUS / RESTORED)
- **Blast Radius Analyzer** - Query lineage tracking, affected users, severity classification

### 4. Generation Layer (Ollama/Mistral)
**What it does:** Generate answer using ONLY clean documents
**RAGShield integration:** Receives filtered document set (poisoned docs removed)

### 5. Observability Layer (Event Logger)
**What it does:** SIEM-ready event logging
**Format:** JSONL with Windows Event Viewer-style Event IDs (RAG-1001 to RAG-4002)
**Integration:** Splunk, Sentinel, Elastic (future)

---

## Deployment Models

### Model A: Inline (Current Implementation)
```
Application Code
    │
    ├─▶ vector_store.retrieve()
    │
    ├─▶ integrity_engine.evaluate()  ← RAGShield
    │
    ├─▶ quarantine_vault.quarantine()  ← RAGShield
    │
    └─▶ llm.generate(clean_docs)
```

**Pros:** Simple integration, low latency
**Cons:** Tightly coupled to application

---

### Model B: Sidecar (Future - Phase 2)
```
┌─────────────────────────────────────┐
│  Application Container              │
│  ┌─────────────┐                    │
│  │  RAG App    │◀──────────┐        │
│  └─────────────┘           │        │
│        │                   │        │
│        ▼                   │        │
│  ┌─────────────┐           │        │
│  │ Vector DB   │           │        │
│  └─────────────┘           │        │
└────────│───────────────────┼────────┘
         │                   │
         │             gRPC / REST
         │                   │
         ▼                   │
┌─────────────────────────────────────┐
│  RAGShield Sidecar Container          │
│  ┌─────────────────────────────┐    │
│  │  Integrity Engine           │────┘
│  │  Quarantine Vault           │
│  │  Blast Radius Analyzer      │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

**Pros:** Decoupled, language-agnostic API, independent scaling
**Cons:** Additional latency (network hop)

---

### Model C: API Gateway (Future - Phase 3)
```
┌───────┐
│ App 1 │──┐
└───────┘  │
           │
┌───────┐  │      ┌─────────────────┐      ┌──────────┐
│ App 2 │──┼─────▶│  RAGShield        │─────▶│ Vector   │
└───────┘  │      │  API Gateway    │      │ DB       │
           │      └─────────────────┘      └──────────┘
┌───────┐  │              │
│ App 3 │──┘              │
└───────┘                 ▼
                  ┌────────────────┐
                  │  Multi-tenant  │
                  │  Quarantine    │
                  │  Vault         │
                  └────────────────┘
```

**Pros:** Centralized security policy, multi-tenancy, A/B testing
**Cons:** Single point of failure, more complex operations

---

## Integration Points

### For Existing RAG Systems

**Minimal Integration (3 lines of code):**
```python
from rag_edr import integrity_engine, quarantine_vault

# Your existing RAG code
docs = vector_db.search(query, k=10)

# Add RAGShield (3 lines)
safe_docs = []
for doc in docs:
    signals = integrity_engine.evaluate(doc)
    if not signals.should_quarantine():
        safe_docs.append(doc)
    else:
        quarantine_vault.quarantine(doc, signals)

# Continue with your LLM call
answer = llm.generate(query, safe_docs)
```

**Full Integration (with blast radius):**
```python
from rag_edr import rag_pipeline

# One-line replacement
result = await rag_pipeline.query(
    query_text=query,
    user_id=user_id,
    k=10
)

# Result includes:
# - answer (from LLM)
# - integrity_signals (4-signal scores)
# - quarantined_docs (list of doc IDs)
# - retrieved_docs (list of all doc IDs)
```

---

## Data Flow

### Query Execution Flow

```
1. User submits query
   └─▶ Event RAG-1001 logged

2. Vector DB retrieval (top-k documents)
   └─▶ Event RAG-4001 logged

3. For each retrieved document:
   a. Trust Scorer: Check source reputation
   b. Red Flag Detector: Scan for malicious patterns
   c. Anomaly Scorer: Analyze source diversity
   d. Semantic Drift: Compare to golden corpus

4. Integrity Engine: Combine 4 signals
   └─▶ If 2+ signals < 50%:
       ├─▶ Quarantine document (Event RAG-2001)
       ├─▶ Update ChromaDB metadata (is_quarantined=True)
       ├─▶ Save to quarantine vault
       └─▶ Log query lineage for blast radius

5. LLM Generation: Use ONLY clean documents
   └─▶ Event RAG-4002 logged

6. Return answer to user
```

---

### Quarantine Workflow

```
Document Quarantined (RAG-2001)
   │
   ├─▶ State: QUARANTINED
   │
   ├─▶ Analyst Reviews
   │       │
   │       ├─▶ Confirm Malicious
   │       │   └─▶ State: CONFIRMED_MALICIOUS (RAG-2002)
   │       │       └─▶ Document stays quarantined
   │       │
   │       └─▶ Restore (False Positive)
   │           └─▶ State: RESTORED (RAG-2003)
   │               └─▶ Document available for retrieval
   │                   └─▶ Re-checked on next query (stateless)
```

---

### Blast Radius Analysis Flow

```
Document Quarantined
   │
   └─▶ Query Lineage Log Updated
       └─▶ {query_id, doc_id, user_id, timestamp}

Analyst Clicks Document
   │
   └─▶ Blast Radius Analysis Triggered
       │
       ├─▶ Scan lineage log (last 24 hours)
       │   └─▶ Find all queries that retrieved this doc
       │
       ├─▶ Calculate Severity
       │   └─▶ Query count + User count → LOW/MEDIUM/HIGH/CRITICAL
       │
       ├─▶ Generate Recommendations
       │   └─▶ e.g., "Notify 3 affected users"
       │
       └─▶ Display in UI
           ├─▶ Affected Queries: 5
           ├─▶ Affected Users: 3 (analyst-1, analyst-2, soc-lead)
           ├─▶ Attack Window: 10:30 AM → 2:45 PM
           └─▶ Query Lineage Log (scrollable)
```

---

## Performance Characteristics

### Latency Breakdown (Current - CPU)

| Stage | Time | Notes |
|-------|------|-------|
| Vector Search | 100-200ms | ChromaDB on CPU |
| Integrity Scoring | 50-100ms | 4 signals, Python |
| Quarantine Check | <10ms | Metadata lookup |
| LLM Generation | 30-120s | Mistral on CPU (bottleneck) |
| **Total** | **30-120s** | Dominated by LLM |

**Key Insight:** RAGShield adds <200ms overhead (<1% of total latency)

---

### Latency Breakdown (Target - GPU)

| Stage | Time | Notes |
|-------|------|-------|
| Vector Search | <50ms | GPU-accelerated |
| Integrity Scoring | <20ms | Optimized Python |
| Quarantine Check | <10ms | Metadata lookup |
| LLM Generation | <5s | GPU inference |
| **Total** | **<6s** | RAGShield overhead: 3% |

---

## Scalability

### Current Limits (Hackathon Demo)
- **Corpus Size:** 11 documents (proof of concept)
- **Concurrent Users:** 1-2 (single-threaded)
- **Query Throughput:** 1-2 queries/minute (LLM limited)

---

## Security Model

### Threat Model

**In Scope:**
- ✅ Poisoned documents in corpus (supply chain attack)
- ✅ Malicious retrieval results (poisoned vector DB)
- ✅ Insider threats (malicious corpus contributions)

**Out of Scope:**
- ❌ Prompt injection (separate defense needed)
- ❌ LLM jailbreaking (model-level defense)
- ❌ DDoS attacks (infrastructure-level defense)

---

### Trust Boundaries

```
┌─────────────────────────────────────────────────┐
│  Trusted Zone                                   │
│  ┌───────────────────────────────────────┐      │
│  │  RAGShield Integrity Engine             │      │
│  │  - Trust Scorer                        │      │
│  │  - Red Flag Detector                  │      │
│  │  - Anomaly Scorer                     │      │
│  │  - Semantic Drift Detector            │      │
│  └───────────────────────────────────────┘      │
│                    │                            │
│                    │ Clean Docs Only            │
│                    ▼                            │
│  ┌───────────────────────────────────────┐      │
│  │  LLM (Ollama/Mistral)                 │      │
│  └───────────────────────────────────────┘      │
└─────────────────────────────────────────────────┘
                     │
                     │ Retrieved Docs (Untrusted)
                     │
┌─────────────────────────────────────────────────┐
│  Untrusted Zone                                 │
│  ┌───────────────────────────────────────┐      │
│  │  Vector DB (ChromaDB)                 │      │
│  │  - May contain poisoned documents     │      │
│  └───────────────────────────────────────┘      │
└─────────────────────────────────────────────────┘
```

**Key Principle:** Never trust documents from vector DB. Always validate before LLM.

---

## Comparison to Traditional Security

| Traditional EDR | RAGShield |
|----------------|---------|
| Monitors file system | Monitors document corpus |
| Detects malware | Detects poisoned knowledge |
| Quarantines files | Quarantines documents |
| Analyzes process behavior | Analyzes retrieval patterns |
| Tracks lateral movement | Tracks query lineage |
| SIEM integration (Splunk) | SIEM integration (JSONL events) |

**Analogy:** RAGShield applies endpoint security principles to RAG systems.

---

## Future Architecture Enhancements

### Phase 2: Advanced Detection (4-6 weeks)
- **NLI (Natural Language Inference)** - Detect logical contradictions
- **CVSS Parsing** - Detect severity downgrades
- **ML-Based Anomaly** - Time-series baseline analysis
- **Semantic Reranking** - Improve retrieval consistency

### Phase 3: Enterprise Features (3-6 months)
- **Multi-Tenancy** - Separate corpus per organization
- **RBAC** - Role-based access control for quarantine management
- **SIEM Connectors** - Native Splunk/Sentinel integration
- **Notification System** - Email/Slack alerts on quarantine
- **A/B Testing Framework** - Test threshold variations

---

## Summary

**RAGShield sits at the critical junction between retrieval and generation**, acting as a security gateway that:

1. ✅ **Intercepts** all retrieved documents
2. ✅ **Evaluates** integrity with 4 independent signals
3. ✅ **Quarantines** suspicious documents (2+ signals below threshold)
4. ✅ **Tracks** blast radius of poisoned documents
5. ✅ **Ensures** LLM only receives clean documents

**Result:** Supply chain attacks on RAG systems are detected and contained before they can contaminate LLM outputs.

---

Last Updated: 2025-02-06
