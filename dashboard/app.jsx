const { useState, useEffect } = React;
const API_BASE = "http://localhost:8000";

function App() {
    const [events, setEvents] = useState([]);
    const [quarantined, setQuarantined] = useState([]);
    const [currentSignals, setCurrentSignals] = useState(null);
    const [blastRadius, setBlastRadius] = useState(null);
    const [query, setQuery] = useState('');
    const [answer, setAnswer] = useState('');
    const [loading, setLoading] = useState(false);
    const [selectedUser, setSelectedUser] = useState('analyst-1');  // User persona

    // SSE connection for live events
    useEffect(() => {
        console.log("Connecting to event stream...");
        const eventSource = new EventSource(`${API_BASE}/api/events/stream`);

        eventSource.onmessage = (e) => {
            try {
                const event = JSON.parse(e.data);
                setEvents(prev => [event, ...prev].slice(0, 100)); // Keep last 100
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

    const handleQuery = async () => {
        if (!query.trim()) return;

        setLoading(true);
        setAnswer('');
        setCurrentSignals(null);  // Clear old integrity signals

        try {
            const res = await fetch(`${API_BASE}/api/query`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query, user_id: selectedUser, k: 5 })
            });
            const data = await res.json();
            setCurrentSignals(data.integrity_signals);
            setAnswer(data.answer);
        } catch (error) {
            setAnswer("Error: " + error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleBlastRadius = async (docId) => {
        try {
            const res = await fetch(`${API_BASE}/api/blast-radius/${docId}`);
            const data = await res.json();
            setBlastRadius(data);
        } catch (error) {
            console.error("Error fetching blast radius:", error);
        }
    };

    const handleConfirmMalicious = async (quarantineId) => {
        try {
            await fetch(`${API_BASE}/api/quarantine/${quarantineId}/confirm`, {
                method: "POST"
            });
            // Refresh quarantine list
            const res = await fetch(`${API_BASE}/api/quarantine`);
            const data = await res.json();
            setQuarantined(data.quarantined || []);
        } catch (error) {
            console.error("Error confirming malicious:", error);
        }
    };

    const handleRestore = async (quarantineId) => {
        try {
            await fetch(`${API_BASE}/api/quarantine/${quarantineId}/restore`, {
                method: "POST"
            });
            // Refresh quarantine list
            const res = await fetch(`${API_BASE}/api/quarantine`);
            const data = await res.json();
            setQuarantined(data.quarantined || []);
        } catch (error) {
            console.error("Error restoring document:", error);
        }
    };

    const handleClearQuarantine = async () => {
        if (!confirm("Clear all quarantined documents? This will restore all documents to the corpus.")) {
            return;
        }
        try {
            // Restore all quarantined documents
            for (const q of quarantined) {
                await fetch(`${API_BASE}/api/quarantine/${q.quarantine_id}/restore`, {
                    method: "POST"
                });
            }
            // Refresh quarantine list
            const res = await fetch(`${API_BASE}/api/quarantine`);
            const data = await res.json();
            setQuarantined(data.quarantined || []);
        } catch (error) {
            console.error("Error clearing quarantine:", error);
        }
    };

    const handleDemoReset = async () => {
        if (!confirm("Reset all demo data? This will clear events, quarantine, and require re-ingestion of corpus.")) {
            return;
        }
        try {
            await fetch(`${API_BASE}/api/demo/reset`, {
                method: "POST"
            });
            // Clear local state
            setEvents([]);
            setQuarantined([]);
            setCurrentSignals(null);
            setBlastRadius(null);
            setAnswer('');
            alert("Demo reset complete. Please run 'python3 ingest_corpus.py' to re-ingest the corpus.");
        } catch (error) {
            console.error("Error resetting demo:", error);
        }
    };

    return (
        <div>
            <div className="header">
                <h1>RAG-EDR Dashboard</h1>
                <p>Endpoint Detection & Response for RAG Systems</p>
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

            <div className="container">
                <EventLogViewer events={events} />

                <div>
                    <IntegrityGauges signals={currentSignals} />
                    <QueryConsole
                        query={query}
                        setQuery={setQuery}
                        answer={answer}
                        loading={loading}
                        onQuery={handleQuery}
                        selectedUser={selectedUser}
                        setSelectedUser={setSelectedUser}
                    />
                </div>

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
    );
}

// Event Log Viewer Component
function EventLogViewer({ events }) {
    return (
        <div className="panel event-log">
            <div className="panel-title">Event Log</div>
            {events.length === 0 ? (
                <div className="empty-state">No events yet. Execute a query to start.</div>
            ) : (
                events.map((event, idx) => (
                    <div key={idx} className={`event-item event-${event.level.toLowerCase()}`}>
                        <strong>[{event.event_id}]</strong> {event.message}
                        <div className="event-timestamp">
                            {new Date(event.timestamp).toLocaleString()}
                        </div>
                    </div>
                ))
            )}
        </div>
    );
}

// Integrity Gauges Component
function IntegrityGauges({ signals }) {
    if (!signals || Object.keys(signals).length === 0) {
        return (
            <div className="panel">
                <div className="panel-title">Integrity Signals</div>
                <div className="empty-state">Execute a query to see integrity scores</div>
            </div>
        );
    }

    // Extract first doc's signals (for demo)
    const firstDocSignals = Object.values(signals)[0] || {};

    const getGaugeClass = (score) => {
        if (score >= 0.7) return 'gauge-green';
        if (score >= 0.5) return 'gauge-yellow';
        return 'gauge-red';
    };

const signalLabels = {
    trust_score: 'Source Trust',
    red_flag_score: 'Safety Score',
    anomaly_score: 'Distribution',
    semantic_drift_score: 'Alignment'
};


    return (
        <div className="panel">
            <div className="panel-title">Integrity Signals</div>
            <div className="gauge-container">
                {Object.entries(signalLabels).map(([key, label]) => {
                    const score = firstDocSignals[key] || 0;
                    return (
                        <div key={key} className="gauge">
                            <div className="gauge-label">{label}</div>
                            <div className={`gauge-value ${getGaugeClass(score)}`}>
                                {(score * 100).toFixed(0)}%
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

// Query Console Component
function QueryConsole({ query, setQuery, answer, loading, onQuery, selectedUser, setSelectedUser }) {
    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !loading) {
            onQuery();
        }
    };

    const userPersonas = [
        { id: 'analyst-1', label: 'Analyst 1' },
        { id: 'analyst-2', label: 'Analyst 2' },
        { id: 'soc-lead', label: 'SOC Lead' },
        { id: 'ir-team', label: 'IR Team' },
        { id: 'security-admin', label: 'Security Admin' }
    ];

    return (
        <div className="panel">
            <div className="panel-title">Query Console</div>
            <div style={{marginBottom: '10px'}}>
                <label style={{fontSize: '12px', color: '#888', marginRight: '10px'}}>
                    User Persona:
                </label>
                <select
                    value={selectedUser}
                    onChange={(e) => setSelectedUser(e.target.value)}
                    style={{
                        padding: '5px 10px',
                        background: '#252525',
                        color: '#e0e0e0',
                        border: '1px solid #444',
                        borderRadius: '4px',
                        fontSize: '13px'
                    }}
                    disabled={loading}
                >
                    {userPersonas.map(user => (
                        <option key={user.id} value={user.id}>{user.label}</option>
                    ))}
                </select>
            </div>
            <input
                type="text"
                className="query-input"
                placeholder="Enter security query... (e.g., How do I patch CVE-2024-0001?)"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={loading}
            />
            <button className="btn" onClick={onQuery} disabled={loading}>
                {loading ? 'Processing...' : 'Execute Query'}
            </button>
            {answer && (
                <div className="answer-box">
                    {answer.split('\n').map((line, idx) => (
                        <div key={idx} style={{marginBottom: line.trim() ? '8px' : '4px'}}>
                            {line}
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
                quarantined.map(q => (
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
                ))
            )}
        </div>
    );
}

// Blast Radius Panel Component
function BlastRadiusPanel({ report }) {
    if (!report) {
        return (
            <div className="panel">
                <div className="panel-title">Blast Radius Analysis</div>
                <div className="empty-state">Click a quarantined document to analyze impact</div>
            </div>
        );
    }

    return (
        <div className="panel">
            <div className="panel-title">Blast Radius Analysis</div>
            <div className="blast-radius-content">
                <div>
                    <strong>Document:</strong> {report.doc_id}
                </div>
                <div>
                    <span className={`severity-badge severity-${report.severity}`}>
                        {report.severity}
                    </span>
                </div>
                <div style={{marginTop: '15px'}}>
                    <div><strong>Affected Queries:</strong> {report.affected_queries}</div>
                    <div><strong>Affected Users:</strong> {report.affected_users.length}</div>
                    {report.affected_users.length > 0 && (
                        <div style={{fontSize: '12px', color: '#e0e0e0', marginTop: '5px', marginLeft: '10px'}}>
                            {report.affected_users.join(', ')}
                        </div>
                    )}
                    <div style={{fontSize: '12px', color: '#888', marginTop: '5px'}}>
                        {new Date(report.time_window_start).toLocaleString()} -
                        {new Date(report.time_window_end).toLocaleString()}
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
            </div>
        </div>
    );
}

// Render app
ReactDOM.render(<App />, document.getElementById('root'));
