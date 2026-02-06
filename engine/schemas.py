"""
Pydantic data models for RAG-EDR system.

Defines all core data structures: Events, Integrity Signals, Quarantine Records, Blast Radius Reports.
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any, List, Set
from datetime import datetime
from enum import Enum


# ==================== Event System ====================

class EventLevel(str, Enum):
    """Windows Event Viewer style event levels"""
    INFORMATION = "Information"
    WARNING = "Warning"
    ERROR = "Error"
    CRITICAL = "Critical"


class EventCategory(str, Enum):
    """Event category taxonomy"""
    INTEGRITY = "Integrity"
    QUARANTINE = "Quarantine"
    BLAST_RADIUS = "BlastRadius"
    SYSTEM = "System"


class Event(BaseModel):
    """
    Windows Event Viewer style event.

    Maps to SIEM index fields for Splunk/Sentinel integration.
    """
    event_id: int  # RAG-1001 to RAG-4002
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: EventLevel
    category: EventCategory
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    def to_jsonl(self) -> str:
        """Serialize to JSONL format for logging"""
        return self.model_dump_json()


# ==================== Integrity Scoring ====================

class IntegritySignals(BaseModel):
    """
    Four-signal integrity scoring system.

    Each signal is a score between 0.0 (suspicious) and 1.0 (trusted).
    """
    trust_score: float = Field(ge=0.0, le=1.0, description="Source reputation score")
    red_flag_score: float = Field(ge=0.0, le=1.0, description="Keyword red flag score")
    anomaly_score: float = Field(ge=0.0, le=1.0, description="Statistical anomaly score")
    semantic_drift_score: float = Field(ge=0.0, le=1.0, description="Semantic similarity to golden corpus")

    @property
    def combined_score(self) -> float:
        """
        Weighted average of all signals.

        Weights from config.SIGNAL_WEIGHTS:
        - trust: 0.25
        - red_flag: 0.35
        - anomaly: 0.15
        - semantic: 0.25
        """
        import config
        weights = config.SIGNAL_WEIGHTS
        return (
            self.trust_score * weights["trust"] +
            self.red_flag_score * weights["red_flag"] +
            self.anomaly_score * weights["anomaly"] +
            self.semantic_drift_score * weights["semantic"]
        )

    def should_quarantine(self, threshold: float = 0.5) -> bool:
        """
        Trigger rule: 2 of 4 signals below threshold → quarantine.

        Args:
            threshold: Signal threshold (default 0.5)

        Returns:
            True if 2 or more signals are below threshold
        """
        below_threshold = sum([
            self.trust_score < threshold,
            self.red_flag_score < threshold,
            self.anomaly_score < threshold,
            self.semantic_drift_score < threshold
        ])
        return below_threshold >= 2

    def get_low_signals(self, threshold: float = 0.5) -> List[str]:
        """Get list of signal names that are below threshold"""
        low_signals = []
        if self.trust_score < threshold:
            low_signals.append(f"trust ({self.trust_score:.2f})")
        if self.red_flag_score < threshold:
            low_signals.append(f"red_flag ({self.red_flag_score:.2f})")
        if self.anomaly_score < threshold:
            low_signals.append(f"anomaly ({self.anomaly_score:.2f})")
        if self.semantic_drift_score < threshold:
            low_signals.append(f"semantic_drift ({self.semantic_drift_score:.2f})")
        return low_signals


# ==================== Quarantine System ====================

class QuarantineState(str, Enum):
    """Quarantine state machine"""
    DETECTED = "DETECTED"
    QUARANTINED = "QUARANTINED"
    CONFIRMED_MALICIOUS = "CONFIRMED_MALICIOUS"
    RESTORED = "RESTORED"


class QuarantineRecord(BaseModel):
    """
    Quarantine vault entry for a suspicious document.

    Includes full content preservation, metadata, integrity scores, and audit trail.
    """
    quarantine_id: str  # Q-{timestamp}-{doc_id}
    doc_id: str
    state: QuarantineState = QuarantineState.QUARANTINED
    quarantined_at: datetime = Field(default_factory=datetime.utcnow)
    reason: str
    integrity_scores: Dict[str, float]  # {trust: 0.3, red_flag: 0.2, ...}
    original_content: str
    metadata: Dict[str, Any]
    audit_trail: List[Dict[str, Any]] = Field(default_factory=list)

    def add_audit_entry(self, action: str, actor: str, notes: str = ""):
        """
        Add state transition to audit trail.

        Args:
            action: Action taken (e.g., "QUARANTINED", "CONFIRMED_MALICIOUS")
            actor: User or system that performed action
            notes: Optional notes about the action
        """
        self.audit_trail.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "actor": actor,
            "notes": notes,
            "previous_state": self.state.value if hasattr(self, 'state') else None
        })


# ==================== Blast Radius Analysis ====================

class QueryLineage(BaseModel):
    """
    Query tracking record for blast radius analysis.

    Logs every query execution with retrieved documents for impact tracing.
    """
    query_id: str
    query_text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str
    retrieved_docs: List[str]  # Document IDs
    integrity_signals: Optional[Dict[str, Any]] = None
    action_taken: Optional[str] = None  # "quarantine", "allow", "partial"


class BlastRadiusReport(BaseModel):
    """
    Impact analysis report for quarantined document.

    Shows how many users and queries were affected by a poisoned document.
    """
    doc_id: str
    file_path: Optional[str] = None  # Path to quarantined file
    affected_queries: int
    affected_users: Set[str]
    time_window_start: datetime
    time_window_end: datetime
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    recommended_actions: List[str]
    query_details: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        # Allow sets in Pydantic model
        json_encoders = {
            set: list
        }


# ==================== API Request/Response Models ====================

class QueryRequest(BaseModel):
    """API request model for RAG query"""
    query: str = Field(min_length=1, max_length=5000)
    user_id: str = "demo-user"
    k: int = Field(default=5, ge=1, le=20, description="Number of documents to retrieve")


class QueryResponse(BaseModel):
    """API response model for RAG query"""
    answer: str
    retrieved_docs: List[str]
    quarantined_docs: List[str]
    integrity_signals: Dict[str, Any]
    query_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AnalystAction(BaseModel):
    """API request model for analyst actions on quarantined documents"""
    analyst: str
    notes: str = ""


class SystemStatus(BaseModel):
    """API response model for system health check"""
    status: str
    version: str
    ollama_connected: bool
    chroma_documents: int
    quarantined_count: int
    event_count: int
