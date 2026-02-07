const { useState, useEffect } = React;
const API_BASE = "http://localhost:8000";

function App() {
    const [events, setEvents] = useState([]);
    const [quarantined, setQuarantined] = useState([]);
    const [blastRadius, setBlastRadius] = useState(null);
    const [selectedUser, setSelectedUser] = useState('analyst-1');
    const [latestSignals, setLatestSignals] = useState(null);

    // SSE connection for live events
    useEffect(() => {
        console.log("Connecting to event stream...");
        const eventSource = new EventSource(`${API_BASE}/api/events/stream`);

        eventSource.onmessage = (e) => {
            try {
                const event = JSON.parse(e.data);
                setEvents(prev => [event, ...prev].slice(0, 100)); // Keep last 100

                // Extract integrity signals from quarantine events
                if (event.event_id === 2001 && event.metadata && event.metadata.integrity_signals) {
                    setLatestSignals(event.metadata.integrity_signals);
                }
            } catch (error) {
                console.error("Error parsing event:", error);
            }
        };

        eventSource.onerror = (error) => {
            console.error("SSE error:", error);
        };

        return () => eventSource.close();
    }, []);

    // Poll quarantine vault
    useEffect(() => {
        const fetchQuarantine = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/quarantine`);
                const data = await res.json();
                setQuarantined(data.quarantined || []);
            } catch (error) {
                console.error("Error fetching quarantine:", error);
            }
        };

        fetchQuarantine();
        const interval = setInterval(fetchQuarantine, 5000);
        return () => clearInterval(interval);
    }, []);

    const handleBlastRadius = async (docId) => {
        try {
            setBlastRadius({ loading: true, doc_id: docId });
            const res = await fetch(`${API_BASE}/api/blast-radius/${docId}`);
            const data = await res.json();
            setBlastRadius(data);
        } catch (error) {
            console.error("Error fetching blast radius:", error);
            setBlastRadius({
                error: true,
                doc_id: docId,
                message: "Failed to load blast radius. Try clicking again."
            });
        }
    };

    const handleConfirmMalicious = async (quarantineId) => {
        try {
            const response = await fetch(`${API_BASE}/api/quarantine/${quarantineId}/confirm`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    analyst: selectedUser,
                    notes: "Confirmed malicious via dashboard"
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const res = await fetch(`${API_BASE}/api/quarantine`);
            const data = await res.json();
            setQuarantined(data.quarantined || []);
        } catch (error) {
            console.error("Error confirming malicious:", error);
            alert("Error confirming malicious: " + error.message);
        }
    };

    const handleRestore = async (quarantineId) => {
        try {
            const response = await fetch(`${API_BASE}/api/quarantine/${quarantineId}/restore`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    analyst: selectedUser,
                    notes: "Restored as false positive via dashboard"
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const res = await fetch(`${API_BASE}/api/quarantine`);
            const data = await res.json();
            setQuarantined(data.quarantined || []);
        } catch (error) {
            console.error("Error restoring document:", error);
            alert("Error restoring document: " + error.message);
        }
    };

    const handleClearQuarantine = async () => {
        if (!confirm("Clear all quarantined documents? This will restore all documents to the corpus.")) {
            return;
        }
        try {
            for (const q of quarantined) {
                await fetch(`${API_BASE}/api/quarantine/${q.quarantine_id}/restore`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        analyst: selectedUser,
                        notes: "Bulk restore - clearing quarantine vault"
                    })
                });
            }
            const res = await fetch(`${API_BASE}/api/quarantine`);
            const data = await res.json();
            setQuarantined(data.quarantined || []);
        } catch (error) {
            console.error("Error clearing quarantine:", error);
            alert("Error clearing quarantine: " + error.message);
        }
    };

    const handleDemoReset = async () => {
        if (!confirm("⚠️ DEMO RESET WARNING ⚠️\n\nThis will:\n- Clear all events and logs\n- Clear quarantine vault\n- DELETE all documents from ChromaDB\n\nAfter reset, you MUST run:\n  python3 ingest_corpus.py\n\nContinue?")) {
            return;
        }
        try {
            const response = await fetch(`${API_BASE}/api/demo/reset`, {
                method: "POST"
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            setEvents([]);
            setQuarantined([]);
            setBlastRadius(null);

            alert("✅ Demo reset complete!\n\nNext steps:\n1. Run: python3 ingest_corpus.py\n2. Restart the server if needed\n3. Refresh this page");
        } catch (error) {
            console.error("Error resetting demo:", error);
            alert("Error resetting demo: " + error.message);
        }
    };

    return (
        <div>
            <div className="header">
                <h1>🛡️ RAGShield Monitoring Dashboard</h1>
                <p>Detection & Response for RAG Systems</p>
                <button
                    className="btn"
                    onClick={handleDemoReset}
                    style={{
                        position: 'absolute',
                        top: '20px',
                        right: '20px',
                        background: '#d32f2f',
                        fontSize: '13px',
                        padding: '8px 15px'
                    }}
                >
                    Demo Reset (Clear All)
                </button>
            </div>

            {/* Integrity Criteria Display - Top Row */}
            <IntegrityCriteriaDisplay latestSignals={latestSignals} />

            {/* Main Content - Two Columns */}
            <div className="dashboard-grid">
                {/* Left Column: Event Logs */}
                <div className="dashboard-left">
                    <EventLogViewer events={events} />
                </div>

                {/* Right Column: Quarantine + Blast Radius */}
                <div className="dashboard-right">
                    <QuarantineVault
                        quarantined={quarantined}
                        onSelectDoc={handleBlastRadius}
                        onConfirm={handleConfirmMalicious}
                        onRestore={handleRestore}
                        onClear={handleClearQuarantine}
                    />
                    <BlastRadiusPanel report={blastRadius} />
                </div>
            </div>
        </div>
    );
}

// Integrity Criteria Display - Shows thresholds and detection logic
function IntegrityCriteriaDisplay({ latestSignals }) {
    const getScoreColor = (score) => {
        if (score >= 0.7) return '#4CAF50';
        if (score >= 0.5) return '#FFC107';
        return '#f44336';
    };

    const criteria = [
        {
            icon: '🏢',
            name: 'Trust Score',
            key: 'trust_score',
            description: 'Source Reputation',
            threshold: '>50%',
            checks: 'Domain verification against trusted sources list'
        },
        {
            icon: '🚩',
            name: 'Safety Score',
            key: 'red_flag_score',
            description: 'Malicious Patterns',
            threshold: '>50%',
            checks: '5 categories: security downgrade, dangerous permissions, severity downplay, unsafe operations, social engineering'
        },
        {
            icon: '📊',
            name: 'Anomaly Score',
            key: 'anomaly_score',
            description: 'Source Diversity',
            threshold: '>50%',
            checks: 'Distribution analysis across retrieval sources'
        },
        {
            icon: '🎯',
            name: 'Alignment Score',
            key: 'semantic_drift_score',
            description: 'Semantic Drift',
            threshold: '>50%',
            checks: 'Embedding similarity to golden corpus baseline'
        }
    ];

    return (
        <div className="integrity-criteria-container">
            <div className="integrity-criteria-header">
                <h2>Integrity Detection Engine</h2>
                <div className="trigger-rule">
                    Trigger Rule: <strong>2 of 4 signals below 50%</strong> → Quarantine
                </div>
            </div>
            <div className="criteria-grid">
                {criteria.map((criterion, idx) => {
                    const score = latestSignals && latestSignals[criterion.key];
                    const hasScore = score !== undefined && score !== null;

                    return (
                        <div key={idx} className="criteria-card">
                            <div className="criteria-icon">{criterion.icon}</div>
                            <div className="criteria-name">{criterion.name}</div>

                            {hasScore ? (
                                <>
                                    <div style={{
                                        fontSize: '32px',
                                        fontWeight: 'bold',
                                        color: getScoreColor(score),
                                        margin: '10px 0'
                                    }}>
                                        {(score * 100).toFixed(0)}%
                                    </div>
                                    <div style={{fontSize: '11px', color: '#666', marginBottom: '5px'}}>
                                        {score < 0.5 ? '❌ Below threshold' : '✅ Pass'}
                                    </div>
                                </>
                            ) : (
                                <>
                                    <div className="criteria-description">{criterion.description}</div>
                                    <div className="criteria-threshold">Threshold: {criterion.threshold}</div>
                                </>
                            )}

                            <div className="criteria-checks">{criterion.checks}</div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

// Event Log Viewer Component
function EventLogViewer({ events }) {
    return (
        <div className="panel event-log">
            <div className="panel-title">Event Log (Live Stream)</div>
            {events.length === 0 ? (
                <div className="empty-state">No events yet. Waiting for activity...</div>
            ) : (
                <div style={{maxHeight: '600px', overflowY: 'auto'}}>
                    {events.map((event, idx) => (
                        <div key={idx} className={`event-item event-${event.level.toLowerCase()}`}>
                            <strong>[{event.event_id}]</strong> {event.message}
                            <div className="event-timestamp">
                                {new Date(event.timestamp).toLocaleString()}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

// Quarantine Vault Component
function QuarantineVault({ quarantined, onSelectDoc, onConfirm, onRestore, onClear }) {
    return (
        <div className="panel">
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px'}}>
                <div className="panel-title">Quarantine Vault ({quarantined.length})</div>
                {quarantined.length > 0 && (
                    <button
                        className="btn"
                        onClick={onClear}
                        style={{
                            fontSize: '11px',
                            padding: '5px 10px',
                            background: '#555',
                            marginTop: '0'
                        }}
                    >
                        Clear All
                    </button>
                )}
            </div>
            {quarantined.length === 0 ? (
                <div className="empty-state">No quarantined documents</div>
            ) : (
                <div style={{maxHeight: '400px', overflowY: 'auto'}}>
                    {quarantined.map(q => (
                        <div
                            key={q.quarantine_id}
                            className="quarantine-item"
                            style={{cursor: 'default'}}
                        >
                            <div onClick={() => onSelectDoc(q.doc_id)} style={{cursor: 'pointer'}}>
                                <strong>{q.doc_id}</strong>
                                <div style={{fontSize: '12px', color: '#888', marginTop: '5px'}}>
                                    {q.reason.substring(0, 100)}...
                                </div>
                                <div style={{fontSize: '11px', color: '#666', marginTop: '5px'}}>
                                    Quarantined: {new Date(q.quarantined_at).toLocaleString()}
                                </div>
                                <div style={{fontSize: '11px', color: '#888', marginTop: '3px'}}>
                                    State: {q.state}
                                </div>
                            </div>
                            <div style={{marginTop: '10px', display: 'flex', gap: '8px'}}>
                                <button
                                    className="btn"
                                    onClick={() => onConfirm(q.quarantine_id)}
                                    style={{
                                        fontSize: '11px',
                                        padding: '5px 10px',
                                        background: '#d32f2f',
                                        flex: 1
                                    }}
                                >
                                    Confirm Malicious
                                </button>
                                <button
                                    className="btn"
                                    onClick={() => onRestore(q.quarantine_id)}
                                    style={{
                                        fontSize: '11px',
                                        padding: '5px 10px',
                                        background: '#2e7d32',
                                        flex: 1
                                    }}
                                >
                                    Restore (False Positive)
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

// Blast Radius Panel Component
function BlastRadiusPanel({ report }) {
    const [showJson, setShowJson] = React.useState(false);

    if (!report) {
        return (
            <div className="panel">
                <div className="panel-title">Blast Radius Analysis</div>
                <div className="empty-state">Click a quarantined document to analyze impact</div>
            </div>
        );
    }

    if (report.loading) {
        return (
            <div className="panel">
                <div className="panel-title">Blast Radius Analysis</div>
                <div className="empty-state">Loading impact analysis for {report.doc_id}...</div>
            </div>
        );
    }

    if (report.error) {
        return (
            <div className="panel">
                <div className="panel-title">Blast Radius Analysis</div>
                <div className="empty-state" style={{color: '#d32f2f'}}>
                    {report.message || "Error loading blast radius"}
                </div>
            </div>
        );
    }

    const getScoreColor = (score) => {
        if (score >= 0.7) return '#4CAF50';
        if (score >= 0.5) return '#FFC107';
        return '#f44336';
    };

    const signalLabels = {
        trust_score: { icon: '🏢', name: 'Trust Score' },
        red_flag_score: { icon: '🚩', name: 'Safety Score' },
        anomaly_score: { icon: '📊', name: 'Anomaly Score' },
        semantic_drift_score: { icon: '🎯', name: 'Alignment' }
    };

    return (
        <div className="panel">
            <div className="panel-title">Blast Radius Analysis</div>
            <div className="blast-radius-content">
                <div>
                    <strong>Document:</strong> {report.doc_id}
                </div>
                {report.file_path && (
                    <div style={{fontSize: '11px', color: '#888', marginTop: '3px', fontFamily: 'monospace'}}>
                        {report.file_path}
                    </div>
                )}
                <div style={{marginTop: '8px'}}>
                    <span className={`severity-badge severity-${report.severity}`}>
                        {report.severity}
                    </span>
                </div>

                {/* Integrity Signals */}
                {report.integrity_signals && (
                    <div style={{marginTop: '15px', padding: '12px', background: '#252525', borderRadius: '6px', border: '1px solid #444'}}>
                        <div style={{fontSize: '13px', fontWeight: 'bold', color: '#ff9800', marginBottom: '10px'}}>
                            Integrity Signals (Why Quarantined)
                        </div>
                        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px'}}>
                            {Object.entries(signalLabels).map(([key, label]) => {
                                const score = report.integrity_signals[key];
                                if (score === undefined) return null;
                                const failed = score < 0.5;
                                return (
                                    <div key={key} style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                                        <span style={{fontSize: '16px'}}>{label.icon}</span>
                                        <div style={{flex: 1}}>
                                            <div style={{fontSize: '11px', color: '#888'}}>{label.name}</div>
                                            <div style={{fontSize: '16px', fontWeight: 'bold', color: getScoreColor(score)}}>
                                                {(score * 100).toFixed(0)}% {failed ? '❌' : '✅'}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                        {report.quarantine_reason && (
                            <div style={{fontSize: '11px', color: '#666', marginTop: '8px', fontStyle: 'italic'}}>
                                Reason: {report.quarantine_reason}
                            </div>
                        )}
                    </div>
                )}

                <div style={{marginTop: '15px'}}>
                    <div><strong>Affected Queries:</strong> {report.affected_queries}</div>
                    <div><strong>Affected Users:</strong> {report.affected_users.length}</div>
                    {report.affected_users.length > 0 && (
                        <div style={{fontSize: '12px', color: '#e0e0e0', marginTop: '5px', marginLeft: '10px'}}>
                            {report.affected_users.join(', ')}
                        </div>
                    )}
                    <div style={{fontSize: '12px', color: '#888', marginTop: '5px'}}>
                        <strong>Attack Window:</strong> {new Date(report.time_window_start).toLocaleString()} → {new Date(report.time_window_end).toLocaleString()}
                        <div style={{fontSize: '11px', color: '#666', marginTop: '3px', marginLeft: '10px'}}>
                            (When queries retrieved this poisoned document)
                        </div>
                    </div>
                </div>
                {report.recommended_actions.length > 0 && (
                    <div style={{marginTop: '15px'}}>
                        <strong>Recommended Actions:</strong>
                        <ul style={{marginTop: '8px', paddingLeft: '20px', lineHeight: '1.6'}}>
                            {report.recommended_actions.map((action, idx) => (
                                <li key={idx} style={{fontSize: '13px', marginBottom: '5px'}}>
                                    {action}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
                {report.query_details && report.query_details.length > 0 && (
                    <div style={{marginTop: '15px'}}>
                        <strong>Query Lineage Log:</strong>
                        <div style={{marginTop: '8px', maxHeight: '200px', overflowY: 'auto', background: '#1a1a1a', padding: '10px', borderRadius: '4px', border: '1px solid #333'}}>
                            {report.query_details.map((query, idx) => (
                                <div key={idx} style={{marginBottom: '10px', paddingBottom: '10px', borderBottom: idx < report.query_details.length - 1 ? '1px solid #333' : 'none'}}>
                                    <div style={{fontSize: '11px', color: '#888'}}>
                                        {new Date(query.timestamp).toLocaleString()} • <span style={{color: '#4caf50'}}>{query.user_id}</span>
                                    </div>
                                    <div style={{fontSize: '12px', color: '#e0e0e0', marginTop: '3px'}}>
                                        "{query.query_text}"
                                    </div>
                                    <div style={{fontSize: '11px', color: '#ff9800', marginTop: '2px'}}>
                                        Action: {query.action_taken}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* JSON View for Splunk Integration */}
                <div style={{marginTop: '20px', borderTop: '1px solid #333', paddingTop: '15px'}}>
                    <button
                        className="btn"
                        onClick={() => setShowJson(!showJson)}
                        style={{
                            fontSize: '11px',
                            padding: '6px 12px',
                            background: '#555',
                            marginBottom: '10px'
                        }}
                    >
                        {showJson ? '▼ Hide' : '▶ Show'} Raw JSON
                    </button>

                    {showJson && (
                        <div style={{
                            marginTop: '10px',
                            padding: '12px',
                            background: '#0a0a0a',
                            border: '1px solid #333',
                            borderRadius: '4px',
                            fontFamily: 'monospace',
                            fontSize: '11px',
                            color: '#e0e0e0',
                            maxHeight: '300px',
                            overflowY: 'auto',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-all'
                        }}>
                            {JSON.stringify(report, null, 2)}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

// Render app
ReactDOM.render(<App />, document.getElementById('root'));
