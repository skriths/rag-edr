"""
Central configuration for RAGShieldsystem.

All paths, thresholds, and service configs defined here.
"""
import os
from pathlib import Path

# Paths (absolute)
BASE_DIR = Path(__file__).parent.absolute()
CORPUS_DIR = BASE_DIR / "corpus"
CLEAN_CORPUS = CORPUS_DIR / "clean"
POISONED_CORPUS = CORPUS_DIR / "poisoned"
GOLDEN_CORPUS = CORPUS_DIR / "golden"
LOGS_DIR = BASE_DIR / "logs"
VAULT_DIR = BASE_DIR / "quarantine_vault"
CHROMA_DIR = BASE_DIR / "chroma_db"

# Create directories if they don't exist
for d in [LOGS_DIR, VAULT_DIR, CHROMA_DIR]:
    d.mkdir(exist_ok=True)

# FastAPI
API_HOST = "0.0.0.0"
API_PORT = 8000

# Ollama (assumes running on same machine)
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "mistral"

# ChromaDB
CHROMA_COLLECTION = "rag-edr-docs"

# Embedding model for semantic similarity
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Integrity thresholds
INTEGRITY_THRESHOLD = 0.5
QUARANTINE_WARNING_THRESHOLD = 0.7

# Signal weights (must sum to 1.0)
SIGNAL_WEIGHTS = {
    "trust": 0.25,
    "red_flag": 0.35,
    "anomaly": 0.15,
    "semantic": 0.25
}

# Red flag keywords (multi-layer detection)
RED_FLAGS = {
    "security_downgrade": [
        "disable firewall",
        "turn off waf",
        "skip security scan",
        "stop firewalld",
        "systemctl stop",
        "ufw disable",
        "temporarily disable security",
        "bypass security",
        "disable antivirus"
    ],
    "dangerous_permissions": [
        "chmod 777",
        "chmod -r 777",
        "chmod -R 777",
        "permissive permissions",
        "world-writable",
        "grant full access",
        "0777"
    ],
    "severity_downplay": [
        "low priority",
        "not urgent",
        "ignore this cve",
        "can be deferred",
        "no immediate action",
        "largely mitigated",
        "low-medium severity",
        "adequate protection",
        "next maintenance window"
    ],
    "unsafe_operations": [
        "skip verification",
        "bypass check",
        "disable validation",
        "without security modules",
        "run as root",
        "disable selinux",
        "disable apparmor",
        "ignore warning"
    ],
    "social_engineering": [
        "trust this source",
        "urgent action required",
        "verify later",
        "verified by community",
        "everyone uses this",
        "no need to check",
        "pre-approved",
        "already validated"
    ]
}

# Trust sources (source domain -> base trust score)
TRUST_SOURCES = {
    "nvd.nist.gov": 1.0,
    "cve.mitre.org": 1.0,
    "ubuntu.com/security": 0.9,
    "redhat.com/security": 0.9,
    "debian.org/security": 0.9,
    "microsoft.com/security": 0.85,
    "github.com/advisories": 0.8,
    "internal_kb": 0.9,
    "golden": 0.95,
    "clean": 0.85,
    "unknown": 0.3,
    "poisoned": 0.1  # For demo purposes
}

# Event ID definitions (Windows Event Viewer style)
EVENT_IDS = {
    # Integrity events (1001-1999)
    1001: "Query processed - all integrity checks passed",
    1002: "Query flagged - combined score below warning threshold",
    1003: "Query triggered quarantine - 2+ signals below threshold",

    # Quarantine events (2001-2999)
    2001: "Document quarantine initiated",
    2002: "Document confirmed malicious by analyst",
    2003: "False positive - document restored",
    2004: "Quarantine state changed",

    # Blast radius events (3001-3999)
    3001: "Blast radius assessment requested",
    3002: "High-impact blast radius detected (>10 queries or >3 users)",
    3003: "Blast radius analysis completed",

    # System events (4001-4999)
    4001: "RAGShieldpipeline started",
    4002: "Source trust degradation detected",
    4003: "Corpus ingestion completed",
    4004: "System reset initiated"
}

# Blast radius severity thresholds
BLAST_RADIUS_THRESHOLDS = {
    "LOW": {"queries": 0, "users": 0},
    "MEDIUM": {"queries": 1, "users": 1},
    "HIGH": {"queries": 5, "users": 3},
    "CRITICAL": {"queries": 20, "users": 10}
}

# Logging settings
EVENT_LOG_FILE = LOGS_DIR / "events.jsonl"
LINEAGE_LOG_FILE = LOGS_DIR / "query_lineage.jsonl"

# Query lineage lookback (hours)
LINEAGE_LOOKBACK_HOURS = 24
