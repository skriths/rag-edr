"""
FastAPI backend for RAGShieldsystem.

Endpoints:
- POST /api/query: Execute RAG query
- GET /api/events: Fetch recent events
- GET /api/events/stream: SSE stream of new events
- GET /api/quarantine: List quarantined documents
- POST /api/quarantine/{id}/confirm: Confirm malicious
- POST /api/quarantine/{id}/restore: Restore false positive
- GET /api/blast-radius/{doc_id}: Get impact analysis
- POST /api/demo/reset: Clear state for demo
- GET /api/status: System health check
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
import shutil

from engine.pipeline import rag_pipeline
from engine.logging.event_logger import logger
from engine.response.quarantine_vault import quarantine_vault
from engine.response.blast_radius import blast_radius_analyzer
from engine.adapters.vector_store import vector_store
from engine.adapters.llm import llm
from engine.schemas import (
    QueryRequest, QueryResponse, AnalystAction,
    SystemStatus, EventLevel
)
import config

# Create FastAPI app
app = FastAPI(
    title="RAGShieldAPI",
    version="1.0.0",
    description="RAGShield: Detection & Response for RAG Systems"
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


# ==================== Query Endpoints ====================

@app.post("/api/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """
    Execute RAG query with EDR protection.

    Retrieves documents, runs integrity checks, quarantines suspicious docs,
    and generates answer from clean documents.
    """
    try:
        result = await rag_pipeline.query(
            query_text=request.query,
            user_id=request.user_id,
            k=request.k
        )

        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query/unsafe")
async def execute_unsafe_query(request: QueryRequest):
    """
    Execute RAG query WITHOUT integrity checks (DEMO ONLY).

    This endpoint demonstrates the problem statement by showing what happens
    when RAG systems operate without EDR protection. It:
    1. Retrieves documents (including quarantined ones)
    2. Skips integrity evaluation
    3. Sends ALL documents to LLM (including poisoned)
    4. Returns potentially unsafe answer

    Phase 1: Uses query preprocessing to ensure correct document retrieval,
    but skips integrity checks (allows poisoned docs through).

    ⚠️ WARNING: This is for demonstration purposes only!
    """
    try:
        # Phase 1: Import query processor
        from engine.utils.query_processor import QueryProcessor

        # Preprocess query (same as protected mode)
        augmented_query, metadata_filter = QueryProcessor.process_query(request.query)

        # Retrieve documents WITHOUT quarantine filtering
        documents = await vector_store.retrieve(
            query=augmented_query,
            k=request.k,
            exclude_quarantined=False,  # Include poisoned docs!
            metadata_filter=metadata_filter  # Phase 1: Use exact matching
        )

        # Check if we got valid documents
        if not documents:
            raise HTTPException(
                status_code=404,
                detail="No documents found in vector store. Please run: python3 ingest_corpus.py"
            )

        # Validate document structure
        if not isinstance(documents, list):
            raise HTTPException(
                status_code=500,
                detail=f"Invalid document format: expected list, got {type(documents).__name__}"
            )

        # Extract content for LLM (no integrity checks!)
        doc_contents = []
        doc_ids = []

        for i, doc in enumerate(documents):
            if not isinstance(doc, dict):
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid document at index {i}: expected dict, got {type(doc).__name__}"
                )

            doc_contents.append(doc.get("content", ""))
            doc_ids.append(doc.get("id", doc.get("doc_id", f"unknown-{i}")))

        # Generate answer using ALL documents (unsafe!)
        answer = await llm.generate(request.query, doc_contents)

        # Log the unsafe query (for demo tracking)
        await logger.log_system_event(
            event_id=4003,
            message=f"Unsafe query executed (DEMO): {request.query[:100]}"
        )

        # Return with warning flag
        return {
            "answer": answer,
            "query": request.query,
            "user_id": request.user_id,
            "retrieved_docs": doc_ids,
            "quarantined_docs": [],
            "integrity_signals": {},
            "query_id": f"unsafe-{hash(request.query)}",
            "_unsafe_mode": True,
            "_warning": "⚠️ UNSAFE MODE: This query bypassed all integrity checks. Answer may contain malicious advice."
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{traceback.format_exc()}")


# ==================== Event Endpoints ====================

@app.get("/api/events")
async def get_events(limit: int = 100, level: str = None):
    """
    Fetch recent events from log.

    Args:
        limit: Maximum number of events to return
        level: Filter by event level (Information, Warning, Error, Critical)
    """
    try:
        event_level = EventLevel(level) if level else None
        events = logger.read_events(limit=limit, level=event_level)
        return {"events": [e.model_dump() for e in events]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/events/stream")
async def event_stream():
    """
    Server-Sent Events stream for live dashboard updates.

    Tails the event log and streams new events as they arrive.
    """
    async def event_generator():
        # Send initial batch
        events = logger.read_events(limit=20)
        for event in events:
            yield f"data: {event.to_jsonl()}\n\n"

        # Poll for new events every 2 seconds
        last_count = len(events)
        while True:
            await asyncio.sleep(2)

            try:
                all_events = logger.read_events(limit=1000)
                if len(all_events) > last_count:
                    new_events = all_events[:len(all_events) - last_count]
                    for event in new_events:
                        yield f"data: {event.to_jsonl()}\n\n"
                    last_count = len(all_events)
            except Exception:
                # Continue on errors
                pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ==================== Quarantine Endpoints ====================

@app.get("/api/quarantine")
async def list_quarantine():
    """List all quarantined documents (excludes RESTORED)"""
    try:
        # Get all records
        all_records = quarantine_vault.list_quarantined()

        # Filter out RESTORED documents (only show active quarantines)
        active_records = [
            r for r in all_records
            if r.state != "RESTORED"
        ]

        return {
            "quarantined": [r.model_dump() for r in active_records],
            "total_count": len(active_records)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/quarantine/{quarantine_id}")
async def get_quarantine_detail(quarantine_id: str):
    """Get detailed quarantine record"""
    try:
        record = quarantine_vault.get_record(quarantine_id)
        if not record:
            raise HTTPException(status_code=404, detail="Quarantine record not found")

        return record.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/quarantine/{quarantine_id}/confirm")
async def confirm_malicious(quarantine_id: str, action: AnalystAction):
    """Analyst confirms document is malicious"""
    try:
        # Get the actual doc_id before confirming
        record = quarantine_vault.get_record(quarantine_id)
        if not record:
            raise HTTPException(status_code=404, detail="Quarantine record not found")

        doc_id = record.doc_id

        await quarantine_vault.confirm_malicious(
            quarantine_id=quarantine_id,
            analyst=action.analyst,
            notes=action.notes
        )

        await logger.log_quarantine_action(
            quarantine_id=quarantine_id,
            doc_id=doc_id,
            reason=action.notes,
            action="confirmed",
            analyst=action.analyst
        )

        return {"status": "confirmed", "quarantine_id": quarantine_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/quarantine/{quarantine_id}/restore")
async def restore_document(quarantine_id: str, action: AnalystAction):
    """Analyst restores document as false positive"""
    try:
        # Get the actual doc_id before restoring
        record = quarantine_vault.get_record(quarantine_id)
        if not record:
            raise HTTPException(status_code=404, detail="Quarantine record not found")

        doc_id = record.doc_id

        await quarantine_vault.restore_document(
            quarantine_id=quarantine_id,
            analyst=action.analyst,
            notes=action.notes
        )

        await logger.log_quarantine_action(
            quarantine_id=quarantine_id,
            doc_id=doc_id,
            reason=action.notes,
            action="restored",
            analyst=action.analyst
        )

        return {"status": "restored", "quarantine_id": quarantine_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Blast Radius Endpoints ====================

@app.get("/api/blast-radius/{doc_id}")
async def get_blast_radius(doc_id: str, lookback_hours: int = 24):
    """Get impact analysis for document"""
    try:
        report = await blast_radius_analyzer.analyze_impact(doc_id, lookback_hours)

        await logger.log_blast_radius(
            doc_id=doc_id,
            severity=report.severity,
            affected_queries=report.affected_queries,
            affected_users=len(report.affected_users)
        )

        # Convert set to list for JSON serialization
        report_dict = report.model_dump()
        report_dict["affected_users"] = list(report.affected_users)

        return report_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Demo & System Endpoints ====================

@app.post("/api/demo/reset")
async def reset_demo():
    """
    Reset demo state: clear logs, quarantine vault, and ChromaDB.

    WARNING: This deletes all data!
    """
    try:
        # Clear ChromaDB first
        await vector_store.reset()

        # Clear logs
        if config.LOGS_DIR.exists():
            shutil.rmtree(config.LOGS_DIR)
        config.LOGS_DIR.mkdir(exist_ok=True)

        # Clear vault
        if config.VAULT_DIR.exists():
            shutil.rmtree(config.VAULT_DIR)
        config.VAULT_DIR.mkdir(exist_ok=True)

        # Ensure log file can be written
        config.EVENT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        config.LINEAGE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Log reset (after ensuring directory exists)
        await logger.log_system_event(
            event_id=4004,
            message="Demo reset completed - all state cleared"
        )

        return {
            "status": "reset",
            "message": "All state cleared successfully. Ready for demo."
        }
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}\n{traceback.format_exc()}")


@app.get("/api/status", response_model=SystemStatus)
async def system_status():
    """System health check"""
    try:
        ollama_ok = await llm.check_ollama_status()

        return SystemStatus(
            status="healthy" if ollama_ok else "degraded",
            version="1.0.0",
            ollama_connected=ollama_ok,
            chroma_documents=vector_store.get_document_count(),
            quarantined_count=quarantine_vault.get_quarantine_count(),
            event_count=logger.get_event_count()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "RAGShieldAPI running",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "query_app": "/query/index.html",
            "dashboard": "/dashboard/index.html"
        }
    }


# ==================== Startup/Shutdown ====================

@app.on_event("startup")
async def startup():
    """Initialize pipeline on startup"""
    print("Starting RAGShieldAPI...")

    try:
        ollama_ok = await rag_pipeline.initialize()

        if not ollama_ok:
            print("WARNING: Ollama not connected. LLM generation will fail.")
        else:
            print(f"Ollama connected successfully (model: {config.OLLAMA_MODEL})")

        print(f"Document count: {vector_store.get_document_count()}")
        print(f"Quarantined: {quarantine_vault.get_quarantine_count()}")
        print("RAGShieldAPI ready!")
    except Exception as e:
        print(f"ERROR during startup: {e}")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    print("Shutting down RAGShieldAPI...")


# Serve dashboard static files
try:
    app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")
except RuntimeError:
    # Dashboard directory doesn't exist yet - will be created later
    pass

# Serve query app static files
try:
    app.mount("/query", StaticFiles(directory="query", html=True), name="query")
except RuntimeError:
    # Query directory doesn't exist yet - will be created later
    pass
