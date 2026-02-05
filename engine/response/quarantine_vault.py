"""
Quarantine vault with state machine and audit trail.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from engine.schemas import QuarantineRecord, QuarantineState, IntegritySignals
import config


class QuarantineVault:
    """
    Manages quarantined documents with full audit trail.

    Directory structure:
    quarantine_vault/
        Q-{timestamp}-{doc_id}/
            content.txt
            metadata.json
            record.json
            audit.jsonl
    """

    def __init__(self, vault_dir: Path = config.VAULT_DIR):
        self.vault_dir = vault_dir
        self.vault_dir.mkdir(exist_ok=True)

    async def quarantine_document(
        self,
        doc_id: str,
        content: str,
        metadata: dict,
        integrity_signals: IntegritySignals,
        reason: str
    ) -> QuarantineRecord:
        """
        Move document to quarantine vault.

        Creates quarantine directory, saves content/metadata, initializes audit trail.

        Args:
            doc_id: Document identifier
            content: Full document content
            metadata: Document metadata
            integrity_signals: Integrity scores at detection time
            reason: Reason for quarantine

        Returns:
            QuarantineRecord with full details
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        quarantine_id = f"Q-{timestamp}-{doc_id}"

        # Create quarantine directory
        q_dir = self.vault_dir / quarantine_id
        q_dir.mkdir(exist_ok=True)

        # Save content
        (q_dir / "content.txt").write_text(content, encoding='utf-8')

        # Save metadata
        (q_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2, default=str),
            encoding='utf-8'
        )

        # Create record
        record = QuarantineRecord(
            quarantine_id=quarantine_id,
            doc_id=doc_id,
            state=QuarantineState.QUARANTINED,
            quarantined_at=datetime.utcnow(),
            reason=reason,
            integrity_scores=integrity_signals.model_dump(),
            original_content=content,
            metadata=metadata
        )

        # Initialize audit trail
        record.add_audit_entry("QUARANTINED", "system", reason)

        # Save record
        (q_dir / "record.json").write_text(
            record.model_dump_json(indent=2),
            encoding='utf-8'
        )

        # Save audit trail
        self._append_audit(q_dir, record.audit_trail[-1])

        return record

    def _append_audit(self, q_dir: Path, audit_entry: dict):
        """Append audit entry to JSONL"""
        with open(q_dir / "audit.jsonl", "a", encoding='utf-8') as f:
            f.write(json.dumps(audit_entry, default=str) + "\n")

    async def confirm_malicious(self, quarantine_id: str, analyst: str, notes: str = ""):
        """
        Analyst confirms document is malicious.

        Args:
            quarantine_id: Quarantine ID
            analyst: Analyst username
            notes: Optional notes about confirmation
        """
        q_dir = self.vault_dir / quarantine_id
        if not q_dir.exists():
            raise ValueError(f"Quarantine ID not found: {quarantine_id}")

        # Load record
        record = QuarantineRecord.model_validate_json(
            (q_dir / "record.json").read_text(encoding='utf-8')
        )

        # Update state
        record.state = QuarantineState.CONFIRMED_MALICIOUS
        record.add_audit_entry("CONFIRMED_MALICIOUS", analyst, notes)

        # Save updated record
        (q_dir / "record.json").write_text(
            record.model_dump_json(indent=2),
            encoding='utf-8'
        )

        # Append audit
        self._append_audit(q_dir, record.audit_trail[-1])

    async def restore_document(self, quarantine_id: str, analyst: str, notes: str = ""):
        """
        Analyst marks document as false positive and restores.

        Args:
            quarantine_id: Quarantine ID
            analyst: Analyst username
            notes: Optional notes about restoration
        """
        q_dir = self.vault_dir / quarantine_id
        if not q_dir.exists():
            raise ValueError(f"Quarantine ID not found: {quarantine_id}")

        # Load record
        record = QuarantineRecord.model_validate_json(
            (q_dir / "record.json").read_text(encoding='utf-8')
        )

        # Update state
        record.state = QuarantineState.RESTORED
        record.add_audit_entry("RESTORED", analyst, notes)

        # Save updated record
        (q_dir / "record.json").write_text(
            record.model_dump_json(indent=2),
            encoding='utf-8'
        )

        # Append audit
        self._append_audit(q_dir, record.audit_trail[-1])

        # Also restore in vector store
        from engine.adapters.vector_store import vector_store
        await vector_store.restore_document(record.doc_id)

    def list_quarantined(self, state: Optional[QuarantineState] = None) -> List[QuarantineRecord]:
        """
        Get all quarantined documents.

        Args:
            state: Optional filter by state

        Returns:
            List of QuarantineRecord objects
        """
        records = []

        for q_dir in self.vault_dir.glob("Q-*"):
            if not q_dir.is_dir():
                continue

            record_file = q_dir / "record.json"
            if not record_file.exists():
                continue

            try:
                record = QuarantineRecord.model_validate_json(
                    record_file.read_text(encoding='utf-8')
                )

                # Filter by state if specified
                if state is None or record.state == state:
                    records.append(record)
            except Exception:
                # Skip corrupted records
                continue

        # Sort by quarantine time (most recent first)
        records.sort(key=lambda r: r.quarantined_at, reverse=True)

        return records

    def get_record(self, quarantine_id: str) -> Optional[QuarantineRecord]:
        """
        Get detailed quarantine record.

        Args:
            quarantine_id: Quarantine ID

        Returns:
            QuarantineRecord or None if not found
        """
        q_dir = self.vault_dir / quarantine_id
        if not q_dir.exists():
            return None

        record_file = q_dir / "record.json"
        if not record_file.exists():
            return None

        return QuarantineRecord.model_validate_json(
            record_file.read_text(encoding='utf-8')
        )

    def get_quarantine_count(self) -> int:
        """Get total number of quarantined documents"""
        return len(list(self.vault_dir.glob("Q-*")))


# Global instance
quarantine_vault = QuarantineVault()
