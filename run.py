"""
Application entry point.

Starts FastAPI server.
"""
import uvicorn
import sys


if __name__ == "__main__":
    print("=" * 60)
    print("RAG-EDR - Endpoint Detection & Response for RAG Systems")
    print("=" * 60)
    print()
    print("Starting server...")
    print(f"API: http://localhost:8000")
    print(f"API Docs: http://localhost:8000/docs")
    print(f"Dashboard: http://localhost:8000/dashboard/index.html")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()

    try:
        uvicorn.run(
            "engine.api:app",
            host="0.0.0.0",
            port=8000,
            reload=False,  # Disable for demo stability
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        sys.exit(0)
