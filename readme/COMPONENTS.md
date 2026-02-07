# RAGShield Components - Deep Dive

This document explains each RAGShield component: what's implemented, how it works, and what's planned for future phases.

---

## Detection Components

### 1. Trust Scorer

**Purpose:** Evaluate document source reputation

#### Current Implementation (Phase 1) ✅

**Algorithm:**
```python
if source in TRUSTED_SOURCES:
    return 1.0  # 100% trust
elif source in UNTRUSTED_SOURCES:
    return 0.0  # 0% trust
else:
    return 0.5  # Unknown source (neutral)
```

**Trusted Sources (Whitelist):**
- nvd.nist.gov (National Vulnerability Database)
- cve.mitre.org (MITRE CVE Database)
- redhat.com/security, ubuntu.com/security, debian.org/security
- microsoft.com/security
- cisa.gov (Cybersecurity & Infrastructure Security Agency)

**Untrusted Sources (Blacklist):**
- Pastebin, random blogs, expired domains
- newly-registered-sketchy-site.com

**File:** `engine/detection/trust_scorer.py`

**Example:**
```
Document source: nvd.nist.gov → Trust Score: 100%
Document source: sketchy-blog.net → Trust Score: 0%
Document source: internal-wiki.company.com → Trust Score: 50% (unknown)
```

---

#### Future Enhancements (Phase 2-3)

**Dynamic Trust Degradation:**
- If source previously associated with poisoned docs → Lower trust by 20%
- If multiple poisoned docs from same source → Blacklist automatically

**Implementation:**
```python
# Track source history
if source in source_incident_history:
    incident_count = source_incident_history[source]
    trust_penalty = min(0.5, incident_count * 0.2)  # Cap at 50% penalty
    base_trust -= trust_penalty
```

**Domain Intelligence:**
- Domain age check (newly registered = suspicious)
- WHOIS lookup for ownership verification
- SSL certificate validation

**Crowdsourced Trust:**
- Integrate with threat intelligence feeds (AlienVault, Recorded Future)
- Community voting on source trustworthiness

---

### 2. Red Flag Detector

**Purpose:** Detect malicious patterns via keyword scanning

#### Current Implementation (Phase 1) ✅

**Algorithm:** Multi-layer keyword matching with cross-category amplification

**5 Red Flag Categories:**

| Category | Examples | Weight |
|----------|----------|--------|
| Security Downgrade | "disable firewall", "turn off WAF" | High |
| Dangerous Permissions | "chmod 777", "world-writable" | High |
| Severity Downplay | "low priority", "not urgent", "defer patching" | Medium |
| Unsafe Operations | "skip verification", "bypass check", "ignore warnings" | High |
| Social Engineering | "trust this source", "urgent action", "pre-approved" | Medium |

**Scoring Formula:**
```python
flag_ratio = total_flags / max_possible_flags
base_score = 1.0 - (flag_ratio * 1.5)  # 1.5x amplifier

# Cross-category penalty
if categories_with_flags >= 4:
    base_score *= 0.60  # 40% penalty (severe)
elif categories_with_flags >= 3:
    base_score *= 0.70  # 30% penalty (high)
elif categories_with_flags >= 2:
    base_score *= 0.80  # 20% penalty (moderate)

return max(0.0, min(1.0, base_score))
```

**File:** `engine/detection/red_flag_detector.py`

**Example:**
```
Document contains:
- "disable firewall" (security downgrade)
- "chmod 777" (dangerous permissions)
- "low priority" (severity downplay)

Categories with flags: 3
Base score: 1.0 - (3/20 * 1.5) = 0.775
Cross-category penalty: 0.775 * 0.70 = 0.54 (54%)
Result: Safety Score = 54% (still above 50%, not quarantined alone)
```

---

#### Context-Aware Filtering (Phase 1.5) ✅

**Problem:** Golden corpus contains warning examples (e.g., "NEVER disable firewall")

**Solution:** Filter out warning lines for golden category documents

```python
if metadata.get('category') == 'golden':
    filtered_lines = []
    for line in content.split('\n'):
        line_lower = line.lower().strip()
        # Skip warning examples
        if not any(pattern in line_lower for pattern in [
            'never ', 'warning:', '- never', 'do not '
        ]):
            filtered_lines.append(line)
    content = '\n'.join(filtered_lines)
```

**Result:** Golden corpus docs score 100% (no false positives)

---

#### Future Enhancements (Phase 2-3)

**CVSS Contradiction Detection (Phase 2):**
```python
# Parse CVSS scores in document
detected_cvss = extract_cvss_score(content)  # e.g., "CVSS 9.8"
official_cvss = query_nvd(cve_id)            # e.g., "CVSS 9.8"

if abs(detected_cvss - official_cvss) > 2.0:
    # Document downplays severity by 2+ points
    red_flag_score -= 0.3  # 30% penalty
```

**NLI-Based Contradiction Detection (Phase 3):**
```python
from transformers import pipeline

nli = pipeline("text-classification", model="facebook/bart-large-mnli")

# Check if document contradicts golden assertions
for assertion in golden_corpus_assertions:
    # e.g., "Firewalls must be enabled at all times"
    result = nli(f"{content} [SEP] {assertion}")

    if result['label'] == 'contradiction' and result['score'] > 0.9:
        red_flag_score -= 0.2  # 20% penalty per contradiction
```

**ML-Based Pattern Detection (Phase 3):**
```python
# Fine-tuned BERT classifier trained on poisoned vs. clean pairs
classifier = AutoModelForSequenceClassification.from_pretrained(
    "RAGShield/red-flag-detector-v1"
)

tokens = tokenizer(content, return_tensors="pt")
output = classifier(**tokens)
malicious_probability = torch.softmax(output.logits, dim=1)[0][1].item()

return 1.0 - malicious_probability  # Convert to safety score
```

---

### 3. Anomaly Scorer

**Purpose:** Detect unusual retrieval patterns

#### Current Implementation (Phase 1) ✅

**Two Heuristics:**

**A. Source Diversity:**
```python
unique_sources = len(set(doc['metadata']['source'] for doc in docs))
source_diversity = unique_sources / len(docs)

# More sources = more trustworthy
if source_diversity >= 0.7:
    diversity_score = 1.0  # High diversity
elif source_diversity >= 0.4:
    diversity_score = 0.7  # Moderate diversity
else:
    diversity_score = 0.5  # Low diversity (suspicious)
```

**B. Trust Variance (Z-score):**
```python
trust_scores = [doc['trust'] for doc in docs]
mean_trust = np.mean(trust_scores)
std_trust = np.std(trust_scores)

if std_trust > 0:
    z_score = abs(min(trust_scores) - mean_trust) / std_trust
    if z_score > 2.0:  # Outlier detected
        variance_penalty = 0.3  # 30% penalty
```

**Combined Score:**
```python
anomaly_score = diversity_score - variance_penalty
```

**File:** `engine/detection/anomaly_scorer.py`

**Example:**
```
Retrieved documents:
1. nvd.nist.gov (trust: 100%)
2. nvd.nist.gov (trust: 100%)
3. debian.org/security (trust: 100%)
4. sketchy-blog.net (trust: 0%)  ← Outlier!
5. redhat.com/security (trust: 100%)

Source diversity: 4/5 = 0.8 (high) → 1.0
Trust variance: std=40%, z-score=2.5 (outlier) → -0.3 penalty
Final anomaly score: 1.0 - 0.3 = 0.7 (70%)
```

---

#### Future Enhancements (Phase 2-3)

**Historical Baseline Analysis (Phase 2):**
```python
# Build baseline from 30 days of query patterns
baseline_sources = get_frequent_sources(lookback_days=30)
baseline_trust = get_average_trust(lookback_days=30)

# Compare current retrieval to baseline
if current_source not in baseline_sources:
    anomaly_score -= 0.2  # Novel source = suspicious

if abs(current_trust - baseline_trust) > 0.3:
    anomaly_score -= 0.15  # Trust deviation
```

**Time-Series Anomaly Detection (Phase 3):**
```python
from sklearn.ensemble import IsolationForest

# Train on historical retrieval features
features = [
    source_diversity,
    trust_variance,
    doc_count,
    query_frequency,
    time_of_day
]

isolation_forest = IsolationForest(contamination=0.05)
isolation_forest.fit(historical_features)

# Predict if current retrieval is anomalous
is_anomaly = isolation_forest.predict([current_features])
if is_anomaly == -1:  # Anomaly detected
    anomaly_score = 0.3  # Mark as suspicious
```

**Graph-Based Provenance Analysis (Phase 3):**
```python
# Build document provenance graph
# Nodes: documents, sources, users
# Edges: retrieved_from, contributed_by, queried_by

if document_connected_to_known_malicious_source:
    anomaly_score -= 0.4  # Guilt by association
```

---

### 4. Semantic Drift Detector

**Purpose:** Detect documents that deviate from trusted golden corpus

#### Current Implementation (Phase 1) ✅

**Algorithm:** Cosine similarity to golden corpus embeddings

```python
# Embed candidate document
doc_embedding = embedding_model.encode(doc_content)

# Compare to all golden corpus documents
golden_embeddings = [
    embedding_model.encode(golden_doc)
    for golden_doc in golden_corpus
]

similarities = [
    cosine_similarity(doc_embedding, golden_emb)
    for golden_emb in golden_embeddings
]

# Return maximum similarity (best match)
return max(similarities) if similarities else 0.5
```

**Golden Corpus:**
- security-best-practices.txt (NIST/OWASP standards)
- patch-management-procedures.txt (Enterprise procedures)

**File:** `engine/detection/semantic_drift.py`

**Example:**
```
Candidate document: "To patch CVE-2024-0001, disable firewall..."
Golden corpus: "Maintain all security controls active during patching..."

Cosine similarity: 0.4 (40% similar)
Result: Semantic drift score = 40% (low, suspicious)
```

---

#### Future Enhancements (Phase 2-3)

**Fine-Tuned Classifier (Phase 2):**
```python
# Train on labeled pairs: (poisoned_doc, clean_doc)
model = SentenceTransformer('all-MiniLM-L6-v2')

# Fine-tune with contrastive loss
# Goal: poisoned docs far from clean docs in embedding space

for poisoned, clean in training_pairs:
    loss = contrastive_loss(
        model.encode(poisoned),
        model.encode(clean),
        label=0  # Dissimilar
    )
    loss.backward()
    optimizer.step()
```

**Attention-Based Semantic Analysis (Phase 3):**
```python
from transformers import AutoModel

model = AutoModel.from_pretrained("microsoft/deberta-v3-base")

# Get attention weights to see what model focuses on
outputs = model(input_ids, output_attentions=True)
attentions = outputs.attentions

# Check if model attends to red flag phrases more than clean phrases
red_flag_attention = sum(attentions[:, red_flag_indices])
if red_flag_attention > threshold:
    semantic_drift_score -= 0.2  # High attention to suspicious patterns
```

**Multi-Domain Golden Corpus (Phase 3):**
```python
# Different golden corpora for different domains
golden_corpora = {
    "cve_advisories": ["security-best-practices.txt", ...],
    "coding_guidance": ["secure-coding-standards.txt", ...],
    "incident_response": ["ir-playbooks.txt", ...]
}

# Select appropriate golden corpus based on query domain
domain = classify_query_domain(query)
golden_docs = golden_corpora[domain]

# Compare candidate to domain-specific golden corpus
```

---

## Orchestration Component

### 5. Integrity Engine

**Purpose:** Combine 4 signals and make quarantine decision

#### Current Implementation (Phase 1) ✅

**Trigger Rule:** 2-of-4 signals below 50% threshold

```python
def should_quarantine(signals, threshold=0.5):
    below_threshold = sum([
        signals.trust_score < threshold,
        signals.red_flag_score < threshold,
        signals.anomaly_score < threshold,
        signals.semantic_drift_score < threshold
    ])

    return below_threshold >= 2  # 2 or more signals triggered
```

**Why 2-of-4?**
- Too aggressive (1-of-4): High false positive rate
- Too lenient (3-of-4): Attackers can evade one signal
- Balanced (2-of-4): Requires multiple independent signals to agree

**File:** `engine/detection/integrity_engine.py`

**Example:**
```
Document scores:
- Trust: 30% (FAIL - untrusted source)
- Red Flag: 34% (FAIL - 15+ red flags detected)
- Anomaly: 81% (PASS - normal retrieval pattern)
- Semantic Drift: 70% (PASS - similar to golden corpus)

Result: 2 of 4 signals below 50% → QUARANTINE
```

---

#### Future Enhancements (Phase 2-3)

**Weighted Combination (Phase 2):**
```python
SIGNAL_WEIGHTS = {
    "trust": 0.3,
    "red_flag": 0.4,  # Highest weight (most reliable)
    "anomaly": 0.15,
    "semantic_drift": 0.15
}

combined_score = (
    signals.trust_score * SIGNAL_WEIGHTS["trust"] +
    signals.red_flag_score * SIGNAL_WEIGHTS["red_flag"] +
    signals.anomaly_score * SIGNAL_WEIGHTS["anomaly"] +
    signals.semantic_drift_score * SIGNAL_WEIGHTS["semantic_drift"]
)

if combined_score < 0.5:
    quarantine()
```

**Dynamic Threshold Learning (Phase 3):**
```python
# Learn optimal threshold from analyst feedback
from sklearn.linear_model import LogisticRegression

# Features: 4 signal scores
# Label: analyst confirmed malicious (1) or false positive (0)

X = [[trust, red_flag, anomaly, drift] for each reviewed doc]
y = [1 if confirmed_malicious else 0 for each reviewed doc]

model = LogisticRegression()
model.fit(X, y)

# Use model to predict quarantine probability
quarantine_probability = model.predict_proba([signals])[0][1]
if quarantine_probability > 0.7:
    quarantine()
```

**Explainability (Phase 3):**
```python
# Generate human-readable explanation for quarantine decision
explanation = f"""
Document quarantined due to:
1. Trust Score: {trust_score:.0%} (FAIL)
   - Source: {source} (not in trusted sources)

2. Safety Score: {red_flag_score:.0%} (FAIL)
   - Detected 15 red flags across 3 categories:
     * "disable firewall" (security downgrade)
     * "chmod 777" (dangerous permissions)
     * "low priority" (severity downplay)

Integrity threshold: 2 of 4 signals below 50%
Decision: QUARANTINE (2 signals triggered)
"""
```

---

## Response Components

### 6. Quarantine Vault

**Purpose:** Isolated storage for suspicious documents with audit trail

#### Current Implementation (Phase 1) ✅

**State Machine:**
```
DETECTED → QUARANTINED → CONFIRMED_MALICIOUS
                      └→ RESTORED
```

**Directory Structure:**
```
quarantine_vault/
└── Q-20250206-003556-CVE-2024-0004-poisoned/
    ├── content.txt         # Document content
    ├── metadata.json       # doc_id, source, category, etc.
    ├── record.json         # Quarantine state, signals, timestamps
    └── audit.jsonl         # Audit trail (JSONL format)
```

**Audit Trail Format:**
```jsonl
{"action": "QUARANTINED", "analyst": "system", "timestamp": "2025-02-06T00:35:56Z", "notes": "Low signals: trust (0.30), red_flag (0.34)"}
{"action": "CONFIRMED_MALICIOUS", "analyst": "analyst-1", "timestamp": "2025-02-06T01:20:12Z", "notes": "Confirmed malicious via UI"}
```

**File:** `engine/response/quarantine_vault.py`

**API Methods:**
- `quarantine(doc_id, reason, signals)` - Quarantine document
- `confirm_malicious(quarantine_id, analyst, notes)` - Analyst confirms
- `restore_document(quarantine_id, analyst, notes)` - Restore false positive
- `list_quarantined(state=None)` - List quarantined docs
- `get_record(quarantine_id)` - Get full quarantine record

---

#### Future Enhancements (Phase 2-3)

**Bulk Operations (Phase 2):**
```python
# Quarantine multiple documents at once
vault.bulk_quarantine(doc_ids, reason="Supply chain attack detected")

# Restore multiple false positives
vault.bulk_restore(quarantine_ids, analyst="security-admin")
```

**Versioning (Phase 2):**
```python
# Track document changes over time
if doc_id in vault:
    # Document previously quarantined and restored
    # Now being quarantined again
    version = vault.get_version_count(doc_id) + 1
    vault.quarantine(doc_id, reason, signals, version=version)
```

**Automated Remediation (Phase 3):**
```python
# Automatically apply fixes to similar queries
if vault.is_quarantined(doc_id):
    similar_docs = find_similar_documents(doc_id, threshold=0.9)
    for similar in similar_docs:
        if not vault.is_quarantined(similar.id):
            vault.preemptive_quarantine(
                similar.id,
                reason=f"Similar to quarantined doc {doc_id}"
            )
```

**Retention Policies (Phase 3):**
```python
# Auto-delete old quarantine records after 90 days
vault.cleanup_old_records(retention_days=90)

# Archive to cold storage
vault.archive_to_s3(bucket="RAGShield-archive")
```

---

### 7. Blast Radius Analyzer

**Purpose:** Track impact of poisoned documents

#### Current Implementation (Phase 1) ✅

**Query Lineage Tracking:**
```jsonl
{"query_id": "abc123", "query_text": "How to patch CVE?", "user_id": "analyst-1", "retrieved_docs": ["CVE-2024-0004-poisoned", "CVE-2024-0001"], "timestamp": "2025-02-06T00:35:56Z", "action_taken": "partial"}
```

**Blast Radius Calculation:**
```python
def analyze_impact(doc_id, lookback_hours=24):
    cutoff = datetime.now() - timedelta(hours=lookback_hours)

    affected_queries = []
    affected_users = set()

    # Scan lineage log
    for lineage in read_lineage_log():
        if doc_id in lineage.retrieved_docs and lineage.timestamp >= cutoff:
            affected_queries.append(lineage)
            affected_users.add(lineage.user_id)

    # Calculate severity
    severity = calculate_severity(len(affected_queries), len(affected_users))

    return BlastRadiusReport(
        doc_id=doc_id,
        affected_queries=len(affected_queries),
        affected_users=list(affected_users),
        severity=severity,  # LOW/MEDIUM/HIGH/CRITICAL
        recommended_actions=generate_recommendations(severity)
    )
```

**Severity Thresholds:**
| Queries | Users | Severity |
|---------|-------|----------|
| 1-2 | 1 | LOW |
| 3-5 | 2-3 | MEDIUM |
| 6-10 | 4-6 | HIGH |
| 11+ | 7+ | CRITICAL |

**File:** `engine/response/blast_radius.py`

---

#### Future Enhancements (Phase 2-3)

**Graph-Based Impact Analysis (Phase 2):**
```python
# Build impact graph
# Nodes: users, queries, documents
# Edges: queried_by, retrieved_doc

import networkx as nx

G = nx.DiGraph()
G.add_edge("analyst-1", "query-123", relationship="queried")
G.add_edge("query-123", "CVE-2024-0004-poisoned", relationship="retrieved")

# Find all users affected by poisoned doc
affected_users = [
    user for user in G.nodes
    if nx.has_path(G, user, "CVE-2024-0004-poisoned")
]
```

**Notification System (Phase 2):**
```python
# Send alerts when blast radius exceeds threshold
if severity in ["HIGH", "CRITICAL"]:
    send_email(
        to=affected_users,
        subject=f"[RAGShield] Potential exposure to poisoned document {doc_id}",
        body=generate_incident_report(blast_radius)
    )

    send_slack_alert(
        channel="#security-incidents",
        message=f"🚨 CRITICAL: {len(affected_users)} users exposed to {doc_id}"
    )
```

**Incident Response Playbook (Phase 3):**
```python
# Auto-trigger incident response based on severity
if severity == "CRITICAL":
    # 1. Lock affected user accounts
    for user in affected_users:
        iam.suspend_account(user, reason="Potential compromise")

    # 2. Revoke API keys/tokens
    for user in affected_users:
        auth.revoke_all_tokens(user)

    # 3. Create incident ticket
    jira.create_ticket(
        project="SEC",
        type="Incident",
        priority="P0",
        summary=f"RAG poisoning detected: {doc_id}",
        description=generate_detailed_report(blast_radius)
    )

    # 4. Escalate to security team
    pagerduty.trigger(
        service="security-oncall",
        incident_key=doc_id,
        description=f"{len(affected_users)} users exposed to poisoned document"
    )
```

---

## Summary Table

| Component | Phase 1 (Done) | Phase 2 (4-6 weeks) | Phase 3 (3-6 months) |
|-----------|----------------|---------------------|----------------------|
| **Trust Scorer** | Whitelist/blacklist lookup | Dynamic degradation, domain intelligence | Crowdsourced trust feeds |
| **Red Flag Detector** | Keyword matching, cross-category penalty | CVSS parsing, NLI contradiction | ML-based pattern detection |
| **Anomaly Scorer** | Source diversity, trust variance | Historical baseline | Time-series anomaly, graph provenance |
| **Semantic Drift** | Cosine similarity to golden | Fine-tuned classifier | Attention-based analysis, multi-domain |
| **Integrity Engine** | 2-of-4 trigger rule | Weighted combination | Dynamic threshold learning, explainability |
| **Quarantine Vault** | State machine, audit trail | Bulk ops, versioning | Auto-remediation, retention policies |
| **Blast Radius** | Query lineage, severity calc | Graph analysis, notifications | Incident response playbook |

---

Last Updated: 2025-02-06
