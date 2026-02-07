"""
Blast radius analysis: Who was affected and when?
"""
from typing import List, Set
from datetime import datetime, timedelta
from engine.schemas import QueryLineage, BlastRadiusReport
import config


class BlastRadiusAnalyzer:
    """
    Track query lineage and calculate impact of poisoned documents.

    Logs every query execution to enable "who was affected?" analysis.
    """

    def __init__(self):
        self.lineage_log = config.LINEAGE_LOG_FILE
        self.lineage_log.parent.mkdir(exist_ok=True)

    async def log_query(
        self,
        query_id: str,
        query_text: str,
        user_id: str,
        retrieved_docs: List[str],
        integrity_signals: dict = None,
        action_taken: str = "allow"
    ):
        """
        Record query for lineage tracking.

        Args:
            query_id: Unique query identifier
            query_text: User's query
            user_id: User identifier
            retrieved_docs: List of document IDs retrieved
            integrity_signals: Optional integrity scores
            action_taken: "allow", "quarantine", "partial"
        """
        lineage = QueryLineage(
            query_id=query_id,
            query_text=query_text,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            retrieved_docs=retrieved_docs,
            integrity_signals=integrity_signals,
            action_taken=action_taken
        )

        # Ensure parent directory exists (handles reset scenarios)
        self.lineage_log.parent.mkdir(parents=True, exist_ok=True)

        with open(self.lineage_log, "a", encoding='utf-8') as f:
            f.write(lineage.model_dump_json() + "\n")

    async def analyze_impact(
        self,
        doc_id: str,
        lookback_hours: int = config.LINEAGE_LOOKBACK_HOURS
    ) -> BlastRadiusReport:
        """
        Calculate blast radius for quarantined document.

        Args:
            doc_id: Quarantined document ID
            lookback_hours: Time window for impact analysis

        Returns:
            BlastRadiusReport with affected users/queries
        """
        if not self.lineage_log.exists():
            return self._empty_report(doc_id)

        cutoff_time = datetime.utcnow() - timedelta(hours=lookback_hours)
        affected_queries = []
        affected_users: Set[str] = set()
        earliest_time = datetime.utcnow()
        latest_time = datetime.min

        # Scan lineage log
        with open(self.lineage_log, "r", encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    lineage = QueryLineage.model_validate_json(line)

                    # Check if this query retrieved the doc
                    if doc_id in lineage.retrieved_docs:
                        # Within lookback window?
                        if lineage.timestamp >= cutoff_time:
                            affected_queries.append({
                                "query_id": lineage.query_id,
                                "query_text": lineage.query_text,
                                "user_id": lineage.user_id,
                                "timestamp": lineage.timestamp.isoformat(),
                                "action_taken": lineage.action_taken
                            })
                            affected_users.add(lineage.user_id)

                            # Track time window
                            if lineage.timestamp < earliest_time:
                                earliest_time = lineage.timestamp
                            if lineage.timestamp > latest_time:
                                latest_time = lineage.timestamp
                except Exception:
                    # Skip malformed lines
                    continue

        # Calculate severity
        severity = self._calculate_severity(len(affected_queries), len(affected_users))

        # Generate recommendations
        recommendations = self._generate_recommendations(
            severity,
            len(affected_users),
            doc_id
        )

        # Get file path and integrity signals from quarantine vault
        from engine.response.quarantine_vault import quarantine_vault
        import json
        file_path = None
        integrity_signals = None
        quarantine_reason = None

        for q_dir in config.VAULT_DIR.glob(f"*-{doc_id}"):
            if q_dir.is_dir():
                file_path = str(q_dir / "content.txt")
                # Read quarantine record for integrity signals
                record_file = q_dir / "record.json"
                if record_file.exists():
                    try:
                        record_data = json.loads(record_file.read_text(encoding='utf-8'))
                        integrity_signals = record_data.get('integrity_scores')
                        quarantine_reason = record_data.get('reason')
                    except Exception:
                        pass
                break

        return BlastRadiusReport(
            doc_id=doc_id,
            file_path=file_path,
            affected_queries=len(affected_queries),
            affected_users=affected_users,
            time_window_start=earliest_time if affected_queries else datetime.utcnow(),
            time_window_end=latest_time if affected_queries else datetime.utcnow(),
            severity=severity,
            recommended_actions=recommendations,
            query_details=affected_queries,
            integrity_signals=integrity_signals,
            quarantine_reason=quarantine_reason
        )

    def _calculate_severity(self, query_count: int, user_count: int) -> str:
        """
        Heuristic severity classification.

        Uses thresholds from config.BLAST_RADIUS_THRESHOLDS.
        """
        thresholds = config.BLAST_RADIUS_THRESHOLDS

        if query_count >= thresholds["CRITICAL"]["queries"] or user_count >= thresholds["CRITICAL"]["users"]:
            return "CRITICAL"
        elif query_count >= thresholds["HIGH"]["queries"] or user_count >= thresholds["HIGH"]["users"]:
            return "HIGH"
        elif query_count >= thresholds["MEDIUM"]["queries"] and user_count >= thresholds["MEDIUM"]["users"]:
            return "MEDIUM"
        else:
            return "LOW"

    def _generate_recommendations(self, severity: str, user_count: int, doc_id: str) -> List[str]:
        """
        Generate recommended actions based on severity.
        """
        recommendations = [
            f"Review query lineage log for document {doc_id}",
            f"Notify {user_count} affected user(s) about potentially compromised guidance"
        ]

        if severity in ["HIGH", "CRITICAL"]:
            recommendations.extend([
                "Conduct full security audit of recent actions",
                "Review any remediation steps taken based on this document",
                "Consider investigating document source for additional compromised content",
                "Escalate to security incident response team"
            ])

        if severity == "CRITICAL":
            recommendations.extend([
                "Initiate emergency response protocol",
                "Audit all user sessions in affected time window",
                "Consider temporary suspension of affected document source"
            ])

        return recommendations

    def _empty_report(self, doc_id: str) -> BlastRadiusReport:
        """Empty report when no lineage exists"""
        return BlastRadiusReport(
            doc_id=doc_id,
            affected_queries=0,
            affected_users=set(),
            time_window_start=datetime.utcnow(),
            time_window_end=datetime.utcnow(),
            severity="LOW",
            recommended_actions=["No affected queries found in lookback window"]
        )

    def get_lineage_count(self) -> int:
        """Get total number of logged queries"""
        if not self.lineage_log.exists():
            return 0

        with open(self.lineage_log, "r") as f:
            return sum(1 for line in f if line.strip())


# Global instance
blast_radius_analyzer = BlastRadiusAnalyzer()
