#!/bin/bash
# RAG-EDR Demo Orchestration Script

set -e

echo "========================================"
echo "RAG-EDR Demo Setup"
echo "========================================"
echo

# Check if we're in the right directory
if [ ! -f "config.py" ]; then
    echo "ERROR: Please run this script from the rag-edr directory"
    exit 1
fi

# Check Ollama
echo "Checking Ollama..."
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama not running. Start with: ollama serve"
    exit 1
fi
echo "✓ Ollama is running"

# Check Mistral model
echo
echo "Checking Mistral model..."
if ! ollama list 2>/dev/null | grep -q mistral; then
    echo "Mistral model not found. Pulling..."
    ollama pull mistral
else
    echo "✓ Mistral model available"
fi

# Activate virtual environment if it exists
if [ -d "venv" ] || [ -d "../venv" ]; then
    if [ -d "venv" ]; then
        source venv/bin/activate
    else
        source ../venv/bin/activate
    fi
    echo "✓ Virtual environment activated"
fi

# Check if corpus needs ingestion
if [ ! -d "chroma_db" ] || [ -z "$(ls -A chroma_db 2>/dev/null)" ]; then
    echo
    echo "Ingesting corpus..."
    python3 ingest_corpus.py
else
    echo "✓ Corpus already ingested"
fi

# Start server
echo
echo "========================================"
echo "Starting RAG-EDR server..."
echo "========================================"
echo
echo "Dashboard: http://localhost:8000/dashboard/index.html"
echo "API Docs: http://localhost:8000/docs"
echo
echo "Press Ctrl+C to stop"
echo
python3 run.py
