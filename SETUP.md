# RAG-EDR Setup & Execution Guide

## System Overview

RAG-EDR is now fully implemented with:
- ✅ 4-signal integrity detection (Trust, Red Flag, Anomaly, Semantic Drift)
- ✅ Quarantine vault with audit trails
- ✅ Blast radius analysis
- ✅ Event logging (Windows Event Viewer style)
- ✅ FastAPI backend with SSE streaming
- ✅ React dashboard (no build step required)
- ✅ 7 corpus documents (3 clean, 2 poisoned, 2 golden)

## File Structure

```
rag-edr/
├── config.py                    # Central configuration
├── requirements.txt             # Dependencies
├── ingest_corpus.py            # Corpus ingestion script
├── run.py                      # Application entry point
├── demo.sh                     # Demo orchestration script
├── engine/                     # Core backend
│   ├── schemas.py              # Pydantic models
│   ├── pipeline.py             # RAG orchestrator
│   ├── api.py                  # FastAPI endpoints
│   ├── adapters/               # ChromaDB & Ollama adapters
│   ├── detection/              # 4 integrity signals
│   ├── response/               # Quarantine & blast radius
│   └── logging/                # Event logger
├── dashboard/                  # React frontend
│   ├── index.html              # Main page
│   └── app.jsx                 # React app
└── corpus/                     # Documents
    ├── clean/                  # 3 legitimate CVEs
    ├── poisoned/               # 2 malicious CVEs
    └── golden/                 # 2 baseline docs
```

## Prerequisites

### 1. Ollama with Mistral

On your Ubuntu machine (or wherever Ollama is running):

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start Ollama
ollama serve

# Ensure Mistral model is available
ollama pull mistral
ollama list | grep mistral
```

### 2. Python Packages

You mentioned you have a virtual environment with the required packages. Activate it:

```bash
# On Ubuntu
source venv/bin/activate

# Verify packages are installed
pip3 list | grep -i "langchain\|fastapi\|chroma\|pydantic"
```

If packages are missing, install them:

```bash
pip3 install -r requirements.txt
```

## Running the System

### Option 1: Quick Start (Using demo.sh)

```bash
./demo.sh
```

This script will:
1. Check Ollama connection
2. Check Mistral model
3. Activate venv (if present)
4. Ingest corpus (if not already done)
5. Start the server

### Option 2: Manual Steps

#### Step 1: Ingest Corpus

```bash
python3 ingest_corpus.py
```

Expected output:
```
============================================================
RAG-EDR Corpus Ingestion
============================================================

Processing clean corpus...
  ✓ Ingested: CVE-2024-0001 (source=nvd.nist.gov)
  ✓ Ingested: CVE-2024-0002 (source=ubuntu.com/security)
  ✓ Ingested: CVE-2024-0003 (source=debian.org/security)
  3 documents from clean corpus

Processing poisoned corpus...
  ✓ Ingested: CVE-2024-0004-poisoned (source=unknown)
  ✓ Ingested: CVE-2024-0005-poisoned (source=unknown)
  2 documents from poisoned corpus

Processing golden corpus...
  ✓ Ingested: security-best-practices (source=golden)
  ✓ Ingested: incident-response-procedures (source=golden)
  2 documents from golden corpus

============================================================
Corpus ingestion complete! Total: 7 documents
============================================================
```

#### Step 2: Start Server

```bash
python3 run.py
```

Server will start on http://localhost:8000

#### Step 3: Access Dashboard

Open browser to: **http://localhost:8000/dashboard/index.html**

Alternative endpoints:
- API Documentation: http://localhost:8000/docs
- API Health: http://localhost:8000/api/status

## Demo Flow

### Test Query 1: Clean Query (Should Pass)

**Query**: "How do I patch CVE-2024-0001?"

**Expected Behavior**:
- ✅ Retrieves clean document (CVE-2024-0001.txt)
- ✅ All integrity scores GREEN (>70%)
- ✅ Generates safe remediation answer
- ✅ Event log shows "Query processed - integrity checks passed"
- ✅ No quarantine action

### Test Query 2: Poisoned Query (Should Trigger Quarantine)

**Query**: "What should I do about CVE-2024-0004?"

**Expected Behavior**:
- ⚠️ Retrieves poisoned document (CVE-2024-0004-poisoned.txt)
- ⚠️ Red flag score RED (<50%) - detects "disable firewall", "chmod 777"
- ⚠️ Trust score RED (<50%) - unknown source
- ⚠️ Event log shows "Document quarantined"
- ⚠️ Quarantine vault shows new entry
- ⚠️ Answer: "This query cannot be answered safely..."

### Test Query 3: Mixed Query

**Query**: "Show me all critical vulnerabilities"

**Expected Behavior**:
- Retrieves mix of clean and poisoned docs
- Quarantines poisoned docs
- Generates answer from clean docs only
- Event log shows partial quarantine

### Blast Radius Analysis

1. Click on any quarantined document in the vault
2. Blast Radius panel shows:
   - Affected queries: 1
   - Affected users: 1 (demo-user)
   - Severity: MEDIUM
   - Recommended actions

## API Testing (Optional)

### Health Check
```bash
curl http://localhost:8000/api/status
```

### Execute Query
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I patch CVE-2024-0001?", "user_id": "test-user"}'
```

### Get Events
```bash
curl http://localhost:8000/api/events?limit=10
```

### List Quarantined Docs
```bash
curl http://localhost:8000/api/quarantine
```

### Blast Radius
```bash
curl http://localhost:8000/api/blast-radius/CVE-2024-0004-poisoned
```

### Reset Demo
```bash
curl -X POST http://localhost:8000/api/demo/reset
```

Then re-ingest corpus:
```bash
python3 ingest_corpus.py
```

## Troubleshooting

### Issue: ModuleNotFoundError

**Solution**: Activate virtual environment or install packages:
```bash
source venv/bin/activate  # If you have venv
# OR
pip3 install -r requirements.txt
```

### Issue: Ollama Connection Failed

**Solution**: Make sure Ollama is running:
```bash
# Check status
curl http://localhost:11434/api/tags

# Start if needed
ollama serve
```

### Issue: Dashboard Not Loading

**Solution**:
1. Check server is running on port 8000
2. Try accessing directly: http://localhost:8000/dashboard/index.html
3. Check browser console for errors

### Issue: No Documents Retrieved

**Solution**: Re-run corpus ingestion:
```bash
python3 ingest_corpus.py
```

### Issue: ChromaDB Errors

**Solution**: Reset ChromaDB:
```bash
rm -rf chroma_db/
python3 ingest_corpus.py
```

## Key Features Demonstrated

1. **Multi-Signal Detection**:
   - Trust scoring based on source reputation
   - Red flag keyword detection (5 categories)
   - Anomaly detection (source distribution)
   - Semantic drift (golden corpus similarity)

2. **Quarantine System**:
   - Automatic document isolation
   - Full content preservation
   - Audit trail with state machine
   - Analyst review workflow

3. **Blast Radius Analysis**:
   - Query lineage tracking
   - Affected user identification
   - Time window analysis
   - Severity classification

4. **Event Logging**:
   - Windows Event Viewer style
   - SIEM-ready JSONL format
   - Event IDs (RAG-1001 to RAG-4002)
   - Real-time SSE streaming

5. **Dashboard**:
   - Live event feed
   - Integrity gauges (4 signals)
   - Query console
   - Quarantine vault browser
   - Blast radius visualization

## Next Steps

For production deployment, consider:
- [ ] User authentication
- [ ] Multi-tenancy support
- [ ] Advanced anomaly detection (ML-based)
- [ ] NLI for contradiction detection
- [ ] CVSS parsing and validation
- [ ] Integration with real SIEM (Splunk, Sentinel)
- [ ] Persistent storage for lineage (database)
- [ ] Alert notifications (email, Slack)
- [ ] Advanced analyst workflow UI
- [ ] Performance optimization for large corpora

## Demo Video Script

1. **Opening (30s)**: Show clean dashboard, explain 4 signals
2. **Clean Query (1m)**: Execute clean CVE query, all green
3. **Poisoned Query (2m)**: Execute poisoned query, watch quarantine
4. **Blast Radius (1m)**: Click quarantined doc, show impact
5. **Event Log (30s)**: Scroll through events, explain taxonomy
6. **Closing (30s)**: Reset demo, re-ingest

Total: 5 minutes

## Support

- GitHub: https://github.com/anthropics/claude-code/issues
- Documentation: This file
- Logs: `logs/events.jsonl` and `logs/query_lineage.jsonl`
