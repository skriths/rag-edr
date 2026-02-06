const { useState } = React;
const API_BASE = "http://localhost:8000";

function App() {
    const [messages, setMessages] = useState([]);
    const [query, setQuery] = useState('');
    const [mode, setMode] = useState('protected'); // 'protected' or 'unsafe'
    const [loading, setLoading] = useState(false);
    const [selectedUser, setSelectedUser] = useState('analyst-1');

    const userPersonas = [
        { id: 'analyst-1', label: 'Analyst 1' },
        { id: 'analyst-2', label: 'Analyst 2' },
        { id: 'soc-lead', label: 'SOC Lead' },
        { id: 'ir-team', label: 'IR Team' },
        { id: 'security-admin', label: 'Security Admin' }
    ];

    const handleExecuteQuery = async () => {
        if (!query.trim() || loading) return;

        const userMessage = {
            type: 'user',
            text: query,
            persona: selectedUser,
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMessage]);
        setLoading(true);

        try {
            if (mode === 'unsafe') {
                // Execute unsafe query
                const res = await fetch(`${API_BASE}/api/query/unsafe`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ query, user_id: selectedUser, k: 5 })
                });

                if (!res.ok) {
                    const errorData = await res.json().catch(() => ({}));
                    throw new Error(`HTTP ${res.status}: ${errorData.detail || "Unknown error"}`);
                }

                const data = await res.json();

                const answerMessage = {
                    type: 'answer',
                    mode: 'unsafe',
                    text: data.answer,
                    timestamp: new Date()
                };

                setMessages(prev => [...prev, answerMessage]);
            } else {
                // Execute protected query
                const res = await fetch(`${API_BASE}/api/query`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ query, user_id: selectedUser, k: 5 })
                });

                if (!res.ok) {
                    const errorData = await res.json().catch(() => ({}));
                    if (res.status === 500 && errorData.detail && errorData.detail.includes("No documents")) {
                        throw new Error("No documents in vector store. Please run: python3 ingest_corpus.py");
                    }
                    throw new Error(`HTTP ${res.status}: ${errorData.detail || "Unknown error"}`);
                }

                const data = await res.json();

                const answerMessage = {
                    type: 'answer',
                    mode: 'protected',
                    text: data.answer,
                    integritySignals: data.integrity_signals,
                    quarantinedDocs: data.quarantined_docs || [],
                    timestamp: new Date()
                };

                setMessages(prev => [...prev, answerMessage]);
            }

            setQuery('');
        } catch (error) {
            const errorMessage = {
                type: 'error',
                text: error.message,
                timestamp: new Date()
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey && !loading) {
            e.preventDefault();
            handleExecuteQuery();
        }
    };

    return (
        <div>
            <div className="header">
                <h1>RAG Query Application</h1>
                <p>Ask questions about security vulnerabilities and patches</p>
            </div>

            <div className="chat-container">
                <div className="message-history">
                    {messages.length === 0 ? (
                        <div className="empty-state">
                            <div className="empty-state-icon">💬</div>
                            <div className="empty-state-text">No messages yet</div>
                            <div className="empty-state-hint">
                                Enter a security query below to get started
                            </div>
                        </div>
                    ) : (
                        messages.map((msg, idx) => (
                            <MessageComponent key={idx} message={msg} />
                        ))
                    )}

                    {loading && (
                        <div className="loading-indicator">
                            Analyzing query...
                        </div>
                    )}
                </div>
            </div>

            <div className="input-container">
                <div className="mode-selector">
                    <div
                        className={`radio-option radio-unsafe`}
                        onClick={() => setMode('unsafe')}
                    >
                        <input
                            type="radio"
                            id="unsafe-mode"
                            name="mode"
                            value="unsafe"
                            checked={mode === 'unsafe'}
                            onChange={() => setMode('unsafe')}
                        />
                        <label htmlFor="unsafe-mode">
                            Unsafe Mode (Demo Only)
                        </label>
                    </div>

                    <div
                        className={`radio-option radio-protected`}
                        onClick={() => setMode('protected')}
                    >
                        <input
                            type="radio"
                            id="protected-mode"
                            name="mode"
                            value="protected"
                            checked={mode === 'protected'}
                            onChange={() => setMode('protected')}
                        />
                        <label htmlFor="protected-mode">
                            Protected Mode (RAG-EDR)
                        </label>
                    </div>
                </div>

                <div className="query-input-group">
                    <textarea
                        className="query-input"
                        placeholder="Enter your security query... (e.g., How do I patch CVE-2024-0001?)"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyPress={handleKeyPress}
                        disabled={loading}
                        rows="2"
                    />

                    <div className="input-footer">
                        <div className="persona-selector">
                            <label>User:</label>
                            <select
                                value={selectedUser}
                                onChange={(e) => setSelectedUser(e.target.value)}
                                disabled={loading}
                            >
                                {userPersonas.map(user => (
                                    <option key={user.id} value={user.id}>
                                        {user.label}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <button
                            className="btn"
                            onClick={handleExecuteQuery}
                            disabled={loading || !query.trim()}
                        >
                            {loading ? 'Processing...' : 'Execute Query'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

// Message Component
function MessageComponent({ message }) {
    if (message.type === 'user') {
        return (
            <div className="message">
                <div className="message-user">
                    <div className="message-user-label">
                        {message.persona} • {message.timestamp.toLocaleTimeString()}
                    </div>
                    <div className="message-user-text">{message.text}</div>
                </div>
            </div>
        );
    }

    if (message.type === 'error') {
        return (
            <div className="message">
                <div className="message-answer answer-unsafe">
                    <div className="answer-badge badge-unsafe">❌ ERROR</div>
                    <div className="answer-text">
                        <div>{message.text}</div>
                    </div>
                </div>
            </div>
        );
    }

    if (message.type === 'answer') {
        const isUnsafe = message.mode === 'unsafe';

        return (
            <div className="message">
                <div className={`message-answer ${isUnsafe ? 'answer-unsafe' : 'answer-protected'}`}>
                    <div className={`answer-badge ${isUnsafe ? 'badge-unsafe' : 'badge-protected'}`}>
                        {isUnsafe ? '⚠️ UNPROTECTED' : '✅ PROTECTED'}
                    </div>

                    <div className="answer-text">
                        {message.text.split('\n').map((line, idx) => (
                            <div key={idx}>{line || '\u00A0'}</div>
                        ))}
                    </div>

                    {!isUnsafe && message.quarantinedDocs && message.quarantinedDocs.length > 0 && (
                        <div className="answer-metadata">
                            🛡️ RAG-EDR: {message.quarantinedDocs.length} document(s) quarantined
                        </div>
                    )}
                </div>
            </div>
        );
    }

    return null;
}

// Render app
ReactDOM.render(<App />, document.getElementById('root'));
