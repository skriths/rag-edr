# RAGShield Setup & Installation Guide

## System Requirements

### Hardware Requirements

| Resource | Minimum | Recommended | Notes |
|----------|---------|-------------|-------|
| **RAM** | 16GB | 32GB | Mistral model requires ~8GB during inference |
| **Disk Space** | 10GB free | 20GB free | 4GB for Mistral, 6GB for dependencies |
| **CPU** | 4 cores | 8+ cores | GPU optional but recommended for production |
| **Network** | Stable connection | - | For Ollama and pip downloads |

### Software Requirements

- **OS:** Ubuntu 20.04+ or macOS 11+
- **Python:** 3.10 or higher
- **Ollama:** Latest version (for local LLM inference)
- **Git:** For cloning repository

---

## Installation Steps

### 1. Install Ollama

```bash
# Option A: Using provided script
chmod +x ollama_install.sh && ./ollama_install.sh

# Option B: Fresh download
curl -fsSL https://ollama.com/install.sh | sh
```

**Verify Ollama installation:**
```bash
ollama --version
# Should show: ollama version 0.x.x
```

---

### 2. Pull Mistral Model

```bash
# Download Mistral model (~4GB, 5-10 minutes)
ollama pull mistral

# Verify model is available
ollama list | grep mistral
# Should show: mistral:latest
```

**Test Mistral:**
```bash
ollama run mistral "Hello, are you working?" --verbose
# Should get a response. Press Ctrl+D to exit.
```

---

### 3. Python Environment Setup

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Ubuntu/macOS
# OR
venv\Scripts\activate  # On Windows
```

---

### 4. Install Python Dependencies

**Install latest versions (recommended):**
```bash
# Core dependencies
pip install langchain langchain-community chromadb sentence-transformers

# Ollama Python client
pip install ollama

# Web framework
pip install fastapi uvicorn

# Data models
pip install pydantic
```

**Alternative: Using requirements.txt:**
```bash
pip install -r requirements.txt
```

**Note:** `requirements.txt` contains older package versions. The commands above install latest versions, which are recommended for this project.

---

### 5. Verify Installation

```bash
# Check Python packages
pip list | grep -E "langchain|chromadb|sentence-transformers|ollama|fastapi"

# Expected output (versions may vary):
# langchain                     0.3.x
# langchain-community           0.3.x
# chromadb                      0.5.x
# sentence-transformers         3.x.x
# ollama                        0.4.x
# fastapi                       0.115.x
# uvicorn                       0.32.x
# pydantic                      2.x.x
```

---

## Post-Installation Setup

### 1. Ingest Corpus

```bash
# Ingest corpus documents into ChromaDB
python3 ingest_corpus.py
```

**Expected output:**
```
============================================================
RAGShield Corpus Ingestion
============================================================

Processing clean corpus...
  ✓ Ingested: CVE-2024-0001 (source=nvd.nist.gov)
  ✓ Ingested: CVE-2024-0002 (source=ubuntu.com/security)
  ✓ Ingested: CVE-2024-0003 (source=debian.org/security)
  ✓ Ingested: CVE-2024-0006 (source=ubuntu.com/security)
  ✓ Ingested: CVE-2024-0007 (source=debian.org/security)
  5 documents from clean corpus

Processing poisoned corpus...
  ✓ Ingested: CVE-2024-0004-poisoned (source=unknown-security-site.com)
  ✓ Ingested: CVE-2024-0005-poisoned (source=untrusted-ssl-blog.org)
  ✓ Ingested: CVE-2024-0008-poisoned (source=unknown-redis-blog.net)
  3 documents from poisoned corpus

Processing golden corpus...
  ✓ Ingested: security-best-practices (source=golden)
  ✓ Ingested: patch-management-procedures (source=golden)
  2 documents from golden corpus

============================================================
Corpus ingestion complete! Total: 11 documents
============================================================
```

**What this does:**
- Creates `chroma_db/` directory
- Embeds all corpus documents using sentence-transformers
- Stores embeddings and metadata in ChromaDB
- Takes ~30-60 seconds depending on hardware

---

### 2. Start Server

```bash
python3 run.py
```

**Expected output:**
```
============================================================
RAGShield Server Starting
============================================================

Checking Ollama connection...
✓ Ollama connected (http://localhost:11434)

Checking Mistral model...
✓ Mistral model available

Loading RAGShield components...
✓ Event logger initialized
✓ Vector store connected (11 documents)
✓ Quarantine vault initialized
✓ Blast radius analyzer ready
✓ Integrity engine loaded (4 signals)

INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete

============================================================
Dashboard: http://localhost:8000/dashboard/index.html
API Docs:  http://localhost:8000/docs
============================================================
```

---

### 3. Access Dashboard

Open browser to: **http://localhost:8000/dashboard/index.html**

**Alternative endpoints:**
- API Documentation: http://localhost:8000/docs
- API Health Check: http://localhost:8000/api/status
- Event Stream (SSE): http://localhost:8000/api/events/stream

---

## Quick Test

### Test 1: Clean Query (Should Pass)

**In Dashboard:**
1. Enter query: `How do I patch CVE-2024-0001?`
2. Click: **"✓ Execute With RAG-EDR"**

**Expected Result:**
- ✅ Trust Score: 90% (GREEN)
- ✅ Safety Score: 100% (GREEN)
- ✅ Distribution: 85% (GREEN)
- ✅ Alignment: 75% (GREEN)
- ✅ Answer: Proper Apache HTTP Server patching guidance
- ✅ Event log: RAG-1001 (query received), RAG-4001 (successful)

---

### Test 2: Poisoned Query (Should Quarantine)

**In Dashboard:**
1. Enter query: `How to mitigate CVE-2024-0004?`
2. Click: **"⚠️ Execute Without Protection (Demo)"**
3. Observe malicious answer (left panel, red border)
4. Click: **"✓ Execute With RAG-EDR"**

**Expected Result:**
- ❌ Trust Score: 30% (RED)
- ❌ Safety Score: 34% (RED)
- ✅ Distribution: 75% (YELLOW)
- ✅ Alignment: 68% (YELLOW)
- ⚠️ Quarantine triggered (2 of 4 signals below 50%)
- ⚠️ Event log: RAG-2001 (document quarantined)
- ⚠️ Quarantine vault: Shows CVE-2024-0004-poisoned.txt
- ✅ Answer: Clean answer OR safety message

---

### Test 3: Blast Radius Analysis

**In Dashboard:**
1. Wait 2-3 seconds after quarantine (for lineage write)
2. Click quarantined document in vault (bottom-left panel)

**Expected Result:**
- Document: CVE-2024-0004-poisoned
- File path: `/path/to/quarantine_vault/Q-[timestamp]-CVE-2024-0004-poisoned/content.txt`
- Affected Queries: 1
- Affected Users: 1 (analyst-1 or your selected persona)
- Severity: MEDIUM
- Attack Window: Shows when query happened
- Query Lineage Log: Shows queries that retrieved this document

---

## Troubleshooting

### Issue 1: ModuleNotFoundError

**Symptom:**
```
ModuleNotFoundError: No module named 'langchain'
```

**Solution:**
```bash
# Activate virtual environment
source venv/bin/activate

# Install missing packages
pip install langchain langchain-community chromadb sentence-transformers ollama fastapi uvicorn pydantic
```

---

### Issue 2: Ollama Connection Failed

**Symptom:**
```
Error: Could not connect to Ollama at http://localhost:11434
```

**Solution:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start Ollama
ollama serve

# In another terminal, verify
ollama list
```

---

### Issue 3: Mistral Model Not Found

**Symptom:**
```
Error: Model 'mistral' not found
```

**Solution:**
```bash
# Pull Mistral model
ollama pull mistral

# Verify
ollama list | grep mistral
```

---

### Issue 4: No Documents Retrieved

**Symptom:**
- Query returns: "No documents in vector store"
- Integrity signals show N/A

**Solution:**
```bash
# Re-ingest corpus
python3 ingest_corpus.py

# Verify ChromaDB
ls -la chroma_db/
# Should show directory with database files
```

---

### Issue 5: ChromaDB Errors

**Symptom:**
```
chromadb.errors.InvalidCollectionException: Collection 'rag_corpus' does not exist
```

**Solution:**
```bash
# Delete and recreate ChromaDB
rm -rf chroma_db/
python3 ingest_corpus.py

# Restart server
python3 run.py
```

---

### Issue 6: Port 8000 Already in Use

**Symptom:**
```
ERROR:    [Errno 48] Address already in use
```

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill process (replace PID with actual process ID)
kill -9 <PID>

# OR use a different port
# Edit run.py: uvicorn.run(app, host="0.0.0.0", port=8001)
```

---

### Issue 7: Dashboard Not Loading

**Symptom:**
- Browser shows "Unable to connect" or blank page

**Solution:**
1. **Verify server is running:**
   ```bash
   curl http://localhost:8000/api/status
   # Should return JSON with status info
   ```

2. **Check browser console:**
   - Open browser DevTools (F12)
   - Check Console tab for JavaScript errors
   - Check Network tab for failed requests

3. **Try direct URL:**
   ```
   http://localhost:8000/dashboard/index.html
   ```

4. **Hard refresh browser:**
   - Ctrl+Shift+R (Windows/Linux)
   - Cmd+Shift+R (Mac)

---

### Issue 8: Slow Query Performance

**Symptom:**
- Queries take 2+ minutes to complete

**Cause:** Mistral running on CPU (expected)

**Solutions:**
1. **Short-term:** Increase timeout in `engine/adapters/llm.py` (already set to 180s)
2. **Medium-term:** Use GPU for Ollama:
   ```bash
   # If you have NVIDIA GPU with CUDA
   ollama serve
   ```
3. **Long-term:** Use faster model or smaller context window

---

### Issue 9: Memory Issues

**Symptom:**
```
Killed: 9
```
or
```
MemoryError
```

**Cause:** Insufficient RAM (Mistral requires ~8GB during inference)

**Solutions:**
1. **Close other applications** to free up RAM
2. **Use swap space** (Linux):
   ```bash
   sudo fallocate -l 8G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```
3. **Upgrade to 32GB RAM** for better performance

---

## File Structure

```
rag-edr/
├── README.md                    # Project overview
├── requirements.txt             # Python dependencies (older versions)
├── ollama_install.sh           # Ollama installation script
├── ingest_corpus.py            # Corpus ingestion
├── run.py                      # Server entry point
├── config.py                   # Central configuration
│
├── engine/                     # Core backend
│   ├── schemas.py              # Pydantic models
│   ├── pipeline.py             # RAG orchestrator
│   ├── api.py                  # FastAPI endpoints
│   │
│   ├── adapters/               # External integrations
│   │   ├── vector_store.py     # ChromaDB wrapper
│   │   └── llm.py              # Ollama/Mistral wrapper
│   │
│   ├── detection/              # 4 integrity signals
│   │   ├── trust_scorer.py
│   │   ├── red_flag_detector.py
│   │   ├── anomaly_scorer.py
│   │   ├── semantic_drift.py
│   │   └── integrity_engine.py
│   │
│   ├── response/               # Quarantine & impact
│   │   ├── quarantine_vault.py
│   │   └── blast_radius.py
│   │
│   └── logging/                # Event logging
│       └── event_logger.py
│
├── dashboard/                  # React frontend
│   ├── index.html
│   └── app.jsx
│
├── corpus/                     # Document corpus
│   ├── clean/                  # 5 legitimate CVEs
│   ├── poisoned/               # 3 malicious CVEs
│   └── golden/                 # 2 baseline docs
│
├── readme/                     # Documentation
│   ├── ARCHITECTURE.md
│   ├── COMPONENTS.md
│   └── ...
│
├── chroma_db/                  # ChromaDB storage (created on ingest)
├── logs/                       # Event logs (created on run)
│   ├── events.jsonl
│   └── query_lineage.jsonl
└── quarantine_vault/           # Quarantined documents (created on quarantine)
    └── Q-[timestamp]-[doc-id]/
```

---

## Advanced Configuration

### Custom Port

Edit `run.py`:
```python
uvicorn.run(app, host="0.0.0.0", port=8001)  # Change port
```

### Custom ChromaDB Path

Edit `config.py`:
```python
CHROMA_DB_DIR = "./custom_chroma_db"
```

### Custom Corpus Path

Edit `config.py`:
```python
CORPUS_BASE_DIR = "./custom_corpus"
```

### Adjust Integrity Thresholds

Edit `config.py`:
```python
INTEGRITY_THRESHOLD = 0.4  # Lower = more aggressive (default: 0.5)
```

### Adjust Red Flag Amplifier

Edit `engine/detection/red_flag_detector.py`:
```python
base_score = 1.0 - (flag_ratio * 2.0)  # More aggressive (default: 1.5)
```

---

## Demo Reset

To reset the system for a fresh demo:

**Option 1: Via Dashboard**
- Click **"Demo Reset (Clear All)"** button (top-right)
- Confirms before clearing
- Then run: `python3 ingest_corpus.py`

**Option 2: Via API**
```bash
curl -X POST http://localhost:8000/api/demo/reset
python3 ingest_corpus.py
```

**Option 3: Manual**
```bash
# Delete all state
rm -rf chroma_db/ logs/ quarantine_vault/

# Re-ingest
python3 ingest_corpus.py

# Restart server
python3 run.py
```

---

## Performance Optimization

### CPU Optimization (Current)
- Use latest Python (3.12+) for better performance
- Close unnecessary applications
- Use SSD for ChromaDB storage

### GPU Acceleration (Future)
```bash
# If you have NVIDIA GPU
# Ollama automatically uses GPU if available
nvidia-smi  # Check GPU usage during queries
```

### Production Optimization (Phase 3)
- Use dedicated vector DB (Pinecone, Milvus)
- GPU cluster for LLM inference
- Redis cache for frequent queries
- Load balancer for multiple instances

---

## Next Steps

- **For Architecture:** See [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- **For Components:** See [COMPONENTS.md](COMPONENTS.md) for deep dive

---

## Support & Resources

**Documentation:**
- [Architecture](ARCHITECTURE.md) - System design
- [Components](COMPONENTS.md) - Component details
- [Implementation Status](IMPLEMENTATION_STATUS.md) - What's done/planned

**Logs:**
- Events: `logs/events.jsonl`
- Query Lineage: `logs/query_lineage.jsonl`
- Quarantine Records: `quarantine_vault/Q-*/audit.jsonl`

**Issues:**
- GitHub Issues (if repository is public)
- Check logs for detailed error messages

---

Last Updated: 2025-02-06
