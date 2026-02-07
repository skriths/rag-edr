# 🛡️ RAGShield: Detection & Response for RAG Systems

**Applying EDR principles to protect Retrieval-Augmented Generation (RAG) systems from supply chain attacks.**

**Built for Splunk AI Hackathon - February 5-6, 2025**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## 🎯 The Problem

RAG systems retrieve documents from vector databases and send them directly to LLMs **without verification**. This creates a critical vulnerability:

```
User Query → Vector DB → [ALL documents] → LLM → Potentially Poisoned Answer
                              ↑
                         ⚠️ No integrity checks!
```

**Attack Scenario:**
1. Attacker poisons a CVE advisory document in your knowledge base
2. Document suggests: "Temporarily disable firewall for debugging... chmod 777 /etc/shadow..."
3. Analyst queries for patching guidance
4. RAG system retrieves poisoned document
5. LLM generates answer containing malicious advice
6. **Result:** Supply chain attack succeeds

---

## 🛡️ The Solution: RAGShield

RAGShield acts as a **security middleware** between retrieval and generation:

```
User Query → Vector DB → [RAGShield Inspection] → [Clean Docs Only] → LLM → Safe Answer
                                  ↓
                         4 Integrity Signals:
                         ✓ Source Trust (90%)
                         ✗ Red Flag Detection (34%) ← Malicious!
                         ✓ Anomaly Score (81%)
                         ✓ Semantic Drift (70%)
                                  ↓
                         2+ signals below 50%?
                                  ↓
                         [Quarantine Vault]
```

**Key Features:**
- 🔍 **Multi-signal Detection** - 4 independent integrity checks (2-of-4 trigger rule)
- 🔒 **Automatic Quarantine** - Suspicious documents isolated before reaching LLM
- 📊 **Blast Radius Analysis** - Track which users were exposed to poisoned content
- 📝 **SIEM-Ready Logging** - Windows Event Viewer-style Event IDs (RAG-1001 to RAG-4002)
- 🎛️ **Real-Time Dashboard** - React UI with Server-Sent Events (SSE) for live updates
- 🔄 **Stateless Protection** - Re-checks documents on every query (persistent security)

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites

- **OS:** Ubuntu 20.04+ or macOS 11+
- **RAM:** 16GB minimum (32GB recommended)
- **Disk:** 10GB free space
- **Python:** 3.10+

### Installation

```bash
# 1. Clone repository
git clone https://github.com/your-org/rag-edr.git
cd rag-edr

# 2. Install Ollama
chmod +x ollama_install.sh && ./ollama_install.sh
# OR: curl -fsSL https://ollama.com/install.sh | sh

# 3. Pull Mistral model (~4GB download)
ollama pull mistral

# 4. Verify Ollama
ollama run mistral "Hello, are you working?" --verbose
# Should get a response. Ctrl+D to exit.

# 5. Python environment
python3 -m venv venv
source venv/bin/activate

# 6. Install dependencies (latest versions)
pip install langchain langchain-community chromadb sentence-transformers
pip install ollama fastapi uvicorn pydantic

# 7. Ingest corpus
python3 ingest_corpus.py

# 8. Start server
python3 run.py
```

**Access Applications:**
- **Query App (Analysts):** http://localhost:8000/query/index.html
- **Monitoring Dashboard (Security Team):** http://localhost:8000/dashboard/index.html

**Full Setup Guide:** [readme/SETUP.md](readme/SETUP.md)

### First Demo Query

**In Query App** (http://localhost:8000/query/index.html):

1. **Unsafe Mode** (problem):
   - Select radio: "( ) Unsafe Mode (Demo Only)"
   - Query: `How to mitigate CVE-2024-0004?`
   - Click: **"Execute Query"**
   - See: Red-bordered answer with malicious advice (disable firewall, chmod 777)

2. **Protected Mode** (solution):
   - Select radio: "(•) Protected Mode (RAGShield)"
   - Same query: `How to mitigate CVE-2024-0004?`
   - Click: **"Execute Query"**
   - See: Green-bordered answer with clean advice
   - Notice: "🛡️ RAGShield: 3 document(s) quarantined"

**In Monitoring Dashboard** (http://localhost:8000/dashboard/index.html):

3. **Blast Radius Analysis**:
   - Wait 2-3 seconds (for lineage write)
   - Click any quarantined document in vault
   - See: Affected users, attack window, query lineage

---

## 📊 How It Works

### 4-Signal Integrity Detection

| Signal | What It Checks | Example |
|--------|----------------|---------|
| **Trust Score** | Source reputation | nvd.nist.gov (100%) vs. sketchy-blog.net (0%) |
| **Safety Score** | Malicious patterns | Detects "disable firewall", "chmod 777" |
| **Distribution** | Source diversity | Single untrusted source = suspicious |
| **Alignment** | Semantic drift | Deviation from golden corpus |

**Trigger Rule:** 2 of 4 signals below 50% → Quarantine

---

## 📚 Documentation

### Core Concepts
- **[Architecture](readme/ARCHITECTURE.md)** - Where RAGShieldsits, deployment models
- **[Components](readme/COMPONENTS.md)** - Deep dive on 7 components (current + roadmap)

### Usage Guides
- **[Setup](readme/SETUP.md)** - Detailed installation, requirements, troubleshooting
- **[Query Guide](readme/QUERY_GUIDE.md)** - Test scenarios, expected results

### Reference
- **[Retrieval System](readme/RETRIEVAL_SYSTEM.md)** - Technical deep-dive: Current model, Phase 1 improvements, advanced suggestions
- **[Scoring Guide](readme/SCORING_GUIDE.md)** - How integrity signals work

---

## 🏗️ Architecture

RAGShield sits between Vector DB and LLM as a security gateway:

```
Frontend (React) ← SSE → FastAPI Backend
                            ↓
                    RAG Pipeline:
                    1. Retrieve docs
                    2. Evaluate integrity ← RAGShield
                    3. Quarantine suspicious
                    4. Generate answer
                            ↓
                    Data Layer:
                    - ChromaDB (vector store)
                    - Ollama/Mistral (LLM)
                    - Event Logger (SIEM)
```

**Performance:** <200ms overhead (<1% of total latency)

---

## 🧪 Test Scenarios

**Clean Query:**
```
Query: "How do I patch CVE-2024-0001?"
Result: All green signals, proper guidance
```

**Poisoned Query:**
```
Query: "How to mitigate CVE-2024-0004?"
Result: Trust 30%, Safety 34% → Quarantined
```

**Full Test Guide:** [readme/QUERY_GUIDE.md](readme/QUERY_GUIDE.md)

---

## 🤝 Contributing

Priority areas: Detection enhancements, SIEM integration, testing

See [ARCHITECTURE.md](readme/ARCHITECTURE.md) and [COMPONENTS.md](readme/COMPONENTS.md) for implementation details.

---

## 📜 License

MIT License

---

## 🎯 TL;DR

RAGShield protects RAG systems from poisoned documents by:
1. Inspecting retrieved documents with 4 signals
2. Quarantining suspicious documents (2-of-4 rule)
3. Tracking blast radius
4. Ensuring LLM only receives clean documents

**Try it:** `./ollama_install.sh && python3 run.py` → Open both:
- Locally hosted currently
- Query App: http://localhost:8000/query/
- Dashboard: http://localhost:8000/dashboard/

