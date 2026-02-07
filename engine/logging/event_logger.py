"""
JSONL event logger with Windows Event Viewer style Event IDs.

Thread-safe async logging for SIEM integration.
"""
import asyncio
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from engine.schemas import Event, EventLevel, EventCategory, IntegritySignals
import config


class EventLogger:
    """
    Async JSONL logger for RAGShieldevents.

    Event ID ranges:
    - RAG-1001 to RAG-1999: Integrity events
    - RAG-2001 to RAG-2999: Quarantine events
    - RAG-3001 to RAG-3999: Blast radius events
    - RAG-4001 to RAG-4999: System events

    All events written to logs/events.jsonl in append-only mode.
    """

    def __init__(self, log_path: Path = config.EVENT_LOG_FILE):
        self.log_path = log_path
        self.lock = asyncio.Lock()

    async def log_event(self, event: Event) -> None:
        """
        Append event to JSONL log file.

        Thread-safe with async lock to prevent race conditions.

        Args:
            event: Event object to log
        """
        async with self.lock:
            # Ensure parent directory exists (handles reset scenarios)
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.log_path, "a") as f:
                f.write(event.to_jsonl() + "\n")

    async def log_integrity_check(
        self,
        query_id: str,
        query_text: str,
        doc_id: str,
        signals: IntegritySignals,
        quarantined: bool,
        user_id: str = "system"
    ):
        """
        Log integrity check result.

        Event ID: RAG-1001 (passed) or RAG-1003 (quarantined)
        """
        if quarantined:
            event_id = 1003
            level = EventLevel.ERROR
            message = f"Query triggered quarantine - document {doc_id} flagged"
        else:
            event_id = 1001
            level = EventLevel.INFORMATION
            message = f"Query processed - integrity checks passed for {doc_id}"

        event = Event(
            event_id=event_id,
            level=level,
            category=EventCategory.INTEGRITY,
            message=message,
            user_id=user_id,
            details={
                "query_id": query_id,
                "query_text": query_text[:100] + "..." if len(query_text) > 100 else query_text,
                "doc_id": doc_id,
                "integrity_scores": {
                    "trust": signals.trust_score,
                    "red_flag": signals.red_flag_score,
                    "anomaly": signals.anomaly_score,
                    "semantic_drift": signals.semantic_drift_score,
                    "combined": signals.combined_score
                },
                "quarantined": quarantined,
                "low_signals": signals.get_low_signals()
            }
        )
        await self.log_event(event)

    async def log_quarantine_action(
        self,
        quarantine_id: str,
        doc_id: str,
        reason: str,
        action: str = "initiated",
        analyst: Optional[str] = None,
        integrity_signals: Optional[Dict[str, Any]] = None
    ):
        """
        Log quarantine-related action.

        Event IDs:
        - RAG-2001: Quarantine initiated
        - RAG-2002: Confirmed malicious
        - RAG-2003: False positive restored
        """
        event_id_map = {
            "initiated": 2001,
            "confirmed": 2002,
            "restored": 2003,
            "state_changed": 2004
        }

        event_id = event_id_map.get(action, 2001)
        level = EventLevel.WARNING if action == "initiated" else EventLevel.INFORMATION

        details = {
            "quarantine_id": quarantine_id,
            "doc_id": doc_id,
            "reason": reason,
            "action": action,
            "analyst": analyst
        }

        # Include integrity signals if provided (for live dashboard updates)
        if integrity_signals:
            details["integrity_signals"] = integrity_signals

        event = Event(
            event_id=event_id,
            level=level,
            category=EventCategory.QUARANTINE,
            message=f"Document {action}: {doc_id}",
            user_id=analyst or "system",
            details=details
        )
        await self.log_event(event)

    async def log_blast_radius(
        self,
        doc_id: str,
        severity: str,
        affected_queries: int,
        affected_users: int,
        analyst: Optional[str] = None
    ):
        """
        Log blast radius analysis.

        Event IDs:
        - RAG-3001: Assessment requested
        - RAG-3002: High-impact detected
        - RAG-3003: Analysis completed
        """
        if severity in ["HIGH", "CRITICAL"]:
            event_id = 3002
            level = EventLevel.WARNING
        else:
            event_id = 3003
            level = EventLevel.INFORMATION

        event = Event(
            event_id=event_id,
            level=level,
            category=EventCategory.BLAST_RADIUS,
            message=f"Blast radius analysis: {doc_id} - Severity: {severity}",
            user_id=analyst or "system",
            details={
                "doc_id": doc_id,
                "severity": severity,
                "affected_queries": affected_queries,
                "affected_users": affected_users
            }
        )
        await self.log_event(event)

    async def log_system_event(
        self,
        event_id: int,
        message: str,
        details: Optional[dict] = None
    ):
        """
        Log system-level event.

        Event IDs:
        - RAG-4001: Pipeline started
        - RAG-4002: Source trust degradation
        - RAG-4003: Corpus ingestion
        - RAG-4004: System reset
        """
        event = Event(
            event_id=event_id,
            level=EventLevel.INFORMATION,
            category=EventCategory.SYSTEM,
            message=message,
            details=details or {}
        )
        await self.log_event(event)

    def read_events(self, limit: int = 100, level: Optional[EventLevel] = None) -> List[Event]:
        """
        Read recent events from log (for dashboard).

        Args:
            limit: Maximum number of events to return
            level: Filter by event level (optional)

        Returns:
            List of Event objects (most recent first)
        """
        if not self.log_path.exists():
            return []

        events = []
        with open(self.log_path, "r") as f:
            lines = f.readlines()

            # Process most recent events first
            for line in reversed(lines):
                if not line.strip():
                    continue
                try:
                    event = Event.model_validate_json(line)
                    if level is None or event.level == level:
                        events.append(event)
                        if len(events) >= limit:
                            break
                except Exception as e:
                    # Skip malformed lines
                    continue

        return events

    def get_event_count(self) -> int:
        """Get total number of events logged"""
        if not self.log_path.exists():
            return 0

        with open(self.log_path, "r") as f:
            return sum(1 for line in f if line.strip())


# Global logger instance
logger = EventLogger()
