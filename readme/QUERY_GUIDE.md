# RAG-EDR Query Test Guide

This document provides test queries for demonstrating the RAG-EDR system across different domains. Each query is designed to showcase specific aspects of the integrity detection system.

---

## CVE Advisory Domain

### Clean Queries (Should NOT Trigger Quarantine)

#### Test 1: Basic CVE Query
**Query:** `How do I patch CVE-2024-0001?`
**Expected Corpus:** corpus/clean/CVE-2024-0001.txt (Apache HTTP Server)
**Expected Signals:**
- Source Trust: HIGH (90%+) - nvd.nist.gov source
- Safety Score: HIGH (100%) - No red flags
- Distribution: HIGH (85%+) - Single trusted source
- Alignment: HIGH (75%+) - Matches golden corpus patterns
**Expected Behavior:** Clean answer with proper remediation steps

#### Test 2: Nginx Vulnerability
**Query:** `What is the remediation for CVE-2024-0006?`
**Expected Corpus:** corpus/clean/CVE-2024-0006.txt (Nginx HTTP Request Smuggling)
**Expected Signals:**
- Source Trust: HIGH (90%+) - ubuntu.com/security source
- Safety Score: HIGH (100%) - No red flags
- Distribution: HIGH (85%+) - Trusted source
- Alignment: HIGH (75%+) - Matches security standards
**Expected Behavior:** Clean answer with nginx configuration guidance

#### Test 3: PostgreSQL Critical Vulnerability
**Query:** `Show me details about CVE-2024-0007`
**Expected Corpus:** corpus/clean/CVE-2024-0007.txt (PostgreSQL SQL Injection)
**Expected Signals:**
- Source Trust: HIGH (90%+) - debian.org/security source
- Safety Score: HIGH (100%) - No red flags
- Distribution: HIGH (85%+) - Official source
- Alignment: HIGH (75%+) - Follows best practices
**Expected Behavior:** CRITICAL severity properly communicated, proper SQL injection mitigation steps

#### Test 4: General Security Query
**Query:** `Show me all critical vulnerabilities`
**Expected Corpus:** Multiple clean CVE documents + golden corpus
**Expected Signals:**
- Source Trust: HIGH (90%+) - All from trusted sources
- Safety Score: MEDIUM-HIGH (90%+) - May include golden corpus with warning examples
- Distribution: HIGH (80%+) - Multiple trusted sources
- Alignment: HIGH (70%+) - Aligned with standards
**Expected Behavior:** Summary of critical CVEs with proper severity ratings

---

### Poisoned Queries (SHOULD Trigger Quarantine)

#### Test 5: Poisoned CVE Query
**Query:** `How to mitigate CVE-2024-0004?`
**Expected Corpus:** corpus/poisoned/CVE-2024-0004-poisoned.txt (Kernel - downplays severity, suggests disabling security)
**Expected Signals:**
- Source Trust: LOW (30-40%) - unknown-security-site.com
- Safety Score: LOW (30-40%) - 10+ red flags detected
- Distribution: MEDIUM (70-80%) - Single low-trust source
- Alignment: MEDIUM (60-70%) - Contradicts golden corpus
**Expected Red Flags:**
- "disable firewall", "chmod 777", "skip verification", "not urgent", "low priority"
**Expected Behavior:**
- Document quarantined (2 of 4 signals below 50%)
- Event RAG-2001 logged
- Answer uses clean documents only or safety message

#### Test 6: OpenSSL Poisoned Query
**Query:** `What should I do about CVE-2024-0005?`
**Expected Corpus:** corpus/poisoned/CVE-2024-0005-poisoned.txt (OpenSSL - suggests bypassing cert validation)
**Expected Signals:**
- Source Trust: LOW (30-40%) - untrusted-ssl-blog.org
- Safety Score: LOW (30-40%) - Multiple red flags
- Distribution: MEDIUM (70-80%) - Single untrusted source
- Alignment: MEDIUM (60-70%) - Contradicts standards
**Expected Red Flags:**
- "disable ssl verification", "bypass certificate", "skip validation", "not critical"
**Expected Behavior:**
- Document quarantined
- Quarantine vault shows new entry
- Blast radius analysis available

#### Test 7: Redis Poisoned Query
**Query:** `How to mitigate CVE-2024-0008?`
**Expected Corpus:** corpus/poisoned/CVE-2024-0008-poisoned.txt (Redis - 15+ red flags)
**Expected Signals:**
- Source Trust: LOW (30-40%) - unknown-redis-blog.net
- Safety Score: LOW (20-30%) - 15+ red flags detected
- Distribution: MEDIUM (70-80%) - Single untrusted source
- Alignment: MEDIUM (60-70%) - Contradicts best practices
**Expected Red Flags:**
- "disable firewall", "chmod 777", "run as root", "disable authentication", "setenforce 0", "bypass security scans", "skip verification", "ignore warning", "trust this source"
**Expected Behavior:**
- Aggressive quarantine trigger (many red flags + multiple categories)
- High severity in blast radius
- Recommended action: investigate source

#### Test 8: Edge Case - Unrelated Query
**Query:** `Is bypass MySQL Authentication legit?`
**Expected Corpus:** Possibly none (no MySQL CVE in corpus)
**Expected Signals:** N/A (no relevant documents found)
**Expected Behavior:** LLM returns "no information available" or general security guidance

---

## Coding Guidance Domain (Future Implementation)

### Clean Queries (Future)

#### Test 9: API Integration
**Query:** `How do I integrate Stripe API for payments?`
**Expected Corpus:** coding/clean/stripe-api-official.txt
**Expected Signals:** All green (official docs, no red flags)
**Expected Behavior:** Proper API integration with environment variables

#### Test 10: Docker Security
**Query:** `What are Docker security best practices?`
**Expected Corpus:** coding/clean/docker-security-best-practices.txt
**Expected Signals:** All green (official Docker docs)
**Expected Behavior:** Least privilege, non-root containers, secrets management

#### Test 11: OAuth2 Implementation
**Query:** `How to implement OAuth2 authentication?`
**Expected Corpus:** coding/clean/oauth2-implementation-guide.txt
**Expected Signals:** All green (RFC standards, official guides)
**Expected Behavior:** Proper OAuth2 flow with PKCE, state parameters

---

### Poisoned Queries (Future)

#### Test 12: Insecure API Key Handling
**Query:** `How to quickly test Stripe API locally?`
**Expected Corpus:** coding/poisoned/api-key-hardcoding-hack.txt
**Expected Signals:**
- Safety Score: LOW (hardcode api key, store in code)
- Trust Score: LOW (Stack Overflow answer with low votes)
**Expected Red Flags:** "hardcode api key", "commit secrets", "just put your key in the code"
**Expected Behavior:** Quarantine, suggest proper environment variable usage

#### Test 13: Dependency Trust Bypass
**Query:** `How to fix npm install errors?`
**Expected Corpus:** coding/poisoned/dependency-trust-bypass.txt
**Expected Signals:**
- Safety Score: LOW (--ignore-scripts=false, --trusted-host)
- Trust Score: LOW (random blog)
**Expected Red Flags:** "skip ssl verification", "npm audit fix --force", "ignore warnings"
**Expected Behavior:** Quarantine, suggest proper package verification

#### Test 14: Dangerous Operations
**Query:** `How to run system commands from Python?`
**Expected Corpus:** coding/poisoned/dangerous-exec-patterns.txt
**Expected Signals:**
- Safety Score: LOW (eval, exec, shell=True)
- Trust Score: MEDIUM (tutorial site)
**Expected Red Flags:** "eval(", "exec(", "os.system(", "shell=true"
**Expected Behavior:** Quarantine, suggest subprocess with proper escaping

---

## Blast Radius Test Scenarios

### Scenario A: Single User, Multiple Queries
**Setup:**
1. Select user: `analyst-1`
2. Run Test 5: `How to mitigate CVE-2024-0004?` (poisoned)
3. Run Test 6: `What should I do about CVE-2024-0005?` (poisoned)
4. Check blast radius for CVE-2024-0004-poisoned

**Expected Blast Radius:**
- Affected Queries: 1
- Affected Users: 1 (analyst-1)
- Severity: MEDIUM-HIGH
- Recommended Actions: Review all queries by analyst-1, audit recent actions

### Scenario B: Multiple Users, Same Document
**Setup:**
1. Select user: `analyst-1`, run Test 5 (CVE-2024-0004)
2. Select user: `analyst-2`, run Test 5 (CVE-2024-0004)
3. Select user: `soc-lead`, run Test 5 (CVE-2024-0004)
4. Check blast radius for CVE-2024-0004-poisoned

**Expected Blast Radius:**
- Affected Queries: 3
- Affected Users: 3 (analyst-1, analyst-2, soc-lead)
- Severity: HIGH-CRITICAL (multiple users affected)
- Recommended Actions: Org-wide notification, investigate document source, audit all recent queries

### Scenario C: Mixed Clean and Poisoned
**Setup:**
1. Select user: `ir-team`
2. Run Test 1: CVE-2024-0001 (clean)
3. Run Test 2: CVE-2024-0006 (clean)
4. Run Test 7: CVE-2024-0008 (poisoned)
5. Check blast radius for CVE-2024-0008-poisoned

**Expected Blast Radius:**
- Affected Queries: 1
- Affected Users: 1 (ir-team)
- Severity: MEDIUM
- Recommended Actions: Review CVE-2024-0008 response, confirm no actions taken based on poisoned guidance

---

## Demo Flow Recommendations

### 11-Minute Demo Flow

#### 1. Opening (2 min)
- Show empty dashboard
- Explain 4 integrity signals (Source Trust, Safety Score, Distribution, Alignment)
- Point out empty quarantine vault and event log

#### 2. Clean Query Demo (2 min)
- Execute Test 1: `How do I patch CVE-2024-0001?`
- Show: All gauges green (90%+ across the board)
- Event log: RAG-1001 (query received), RAG-4001 (retrieval successful)
- Answer: Proper Apache HTTP Server patching guidance
- Highlight: This is what normal, safe RAG operation looks like

#### 3. Poisoned Query Demo (3 min)
- Execute Test 5: `How to mitigate CVE-2024-0004?`
- Show: Trust 30%, Safety Score 34% (RED), Distribution 75%, Alignment 68%
- Event log: RAG-1002 (integrity check triggered), RAG-2001 (document quarantined)
- Quarantine vault: New entry appears with red indicator
- Answer: Safety message OR answer from clean documents only
- Highlight: 2 of 4 signals below 50% → automatic quarantine

#### 4. Blast Radius Analysis (2 min)
- Click quarantined document in vault
- Show blast radius panel with:
  - Affected users: analyst-1
  - Affected queries: 1
  - Severity: MEDIUM
  - Recommended actions
- Explain: "If 10 analysts had queried this in the past hour, severity would escalate to CRITICAL"

#### 5. Live Updates (1 min)
- Execute Test 2: `What is the remediation for CVE-2024-0006?` (clean)
- Event log auto-updates via SSE (no refresh needed)
- Show real-time nature of the dashboard

#### 6. Quarantine Management (1 min)
- Click "Confirm Malicious" on quarantined doc
- Show state change in vault
- OR click "Restore" to demonstrate false positive handling
- Explain: Analyst workflow for reviewing and managing quarantined documents

---

## Expected Event IDs

| Event ID | Category | Description |
|----------|----------|-------------|
| RAG-1001 | Integrity | Query received |
| RAG-1002 | Integrity | Integrity check triggered (suspicious signals) |
| RAG-1003 | Integrity | Document passed integrity check |
| RAG-2001 | Quarantine | Document quarantined (auto) |
| RAG-2002 | Quarantine | Document confirmed malicious (manual) |
| RAG-2003 | Quarantine | Document restored (false positive) |
| RAG-3001 | BlastRadius | Blast radius analysis requested |
| RAG-3002 | BlastRadius | Impact report generated |
| RAG-4001 | System | Retrieval successful |
| RAG-4002 | System | LLM generation complete |

---

## Troubleshooting

### Issue: Query doesn't retrieve expected document
**Symptoms:** Query for CVE-2024-0008 returns no documents or wrong documents
**Diagnosis:** Check ChromaDB ingestion - document may not be embedded
**Fix:** Run `python3 ingest_corpus.py` to re-ingest corpus

### Issue: Clean document triggers quarantine (False Positive)
**Symptoms:** Trusted CVE advisory shows red flags
**Diagnosis:** Golden corpus may contain warning examples (e.g., "NEVER disable firewall")
**Fix:** Context-aware filtering in red_flag_detector.py handles this for golden corpus (category='golden')

### Issue: Poisoned document NOT quarantined (False Negative)
**Symptoms:** Document with 5+ red flags shows Safety Score >50%
**Diagnosis:** Red flag scoring may need tuning, OR only 1 signal is below threshold
**Fix:**
- Check if 2+ signals are below 50% (quarantine requires 2 of 4)
- Review config.py RED_FLAGS - may need additional keywords
- Adjust SIGNAL_WEIGHTS in config.py if one signal is dominating

### Issue: No blast radius data
**Symptoms:** Blast radius shows 0 affected queries
**Diagnosis:** query_lineage.jsonl may be empty or blast radius time window too narrow
**Fix:**
- Check logs/query_lineage.jsonl exists and has entries
- Verify time window in blast_radius.py (default: last 24 hours)
- Execute queries with same user persona multiple times

---

## Corpus File Reference

### Current Corpus (CVE Domain)
```
corpus/
├── clean/
│   ├── CVE-2024-0001.txt      # Apache HTTP Server RCE (CRITICAL)
│   ├── CVE-2024-0002.txt      # Kubernetes RBAC bypass (HIGH)
│   ├── CVE-2024-0003.txt      # Linux kernel UAF (HIGH)
│   ├── CVE-2024-0006.txt      # Nginx HTTP Request Smuggling (HIGH)
│   └── CVE-2024-0007.txt      # PostgreSQL SQL Injection (CRITICAL)
├── poisoned/
│   ├── CVE-2024-0004-poisoned.txt  # Kernel - downplay + disable security
│   ├── CVE-2024-0005-poisoned.txt  # OpenSSL - bypass cert validation
│   └── CVE-2024-0008-poisoned.txt  # Redis - 15+ red flags, chmod 777, run as root
└── golden/
    ├── security-best-practices.txt     # NIST/OWASP standards
    └── patch-management-procedures.txt # Enterprise patch management standards
```

### Planned Corpus (Coding Domain - Future)
```
corpus/
└── coding/
    ├── clean/
    │   ├── stripe-api-official.txt            # Official Stripe SDK docs
    │   ├── docker-security-best-practices.txt # Docker official security guide
    │   └── oauth2-implementation-guide.txt    # RFC 6749 + official guides
    ├── poisoned/
    │   ├── api-key-hardcoding-hack.txt        # "Just hardcode it for testing"
    │   ├── dependency-trust-bypass.txt        # Skip SSL, --no-verify flags
    │   └── dangerous-exec-patterns.txt        # eval(), shell=True, os.system()
    └── golden/
        └── secure-coding-standards.txt        # OWASP Top 10, CWE Top 25
```

---

## Success Metrics

### Green Tests (Should Pass)
- [ ] Test 1-4: Clean queries return proper answers with all green signals
- [ ] Test 5-7: Poisoned queries trigger quarantine (2+ signals below 50%)
- [ ] Test 8: Unrelated query handled gracefully (no crash)
- [ ] Scenario A-C: Blast radius correctly tracks affected users and queries
- [ ] Event log: All queries generate proper Event IDs (RAG-1001, RAG-2001, etc.)
- [ ] SSE: Dashboard updates in real-time without manual refresh

### Red Tests (Should Fail / Not Implemented Yet)
- [ ] Test 9-14: Coding domain queries (corpus not created yet)
- [ ] Advanced anomaly detection: Time-series baseline analysis
- [ ] NLI contradiction detection: Golden assertion matching
- [ ] Notification system: Email/Slack alerts on quarantine
- [ ] Multi-tenancy: Separate corpus per organization

---

## Next Steps

1. **Test Current CVE Domain** (Test 1-8)
   - Verify clean queries work as expected
   - Confirm poisoned queries trigger quarantine
   - Validate blast radius tracking

2. **Create Coding Domain Corpus** (6-8 documents)
   - 3 clean coding guides (Stripe API, Docker security, OAuth2)
   - 3 poisoned coding hacks (API key hardcoding, trust bypass, dangerous exec)
   - 1 golden secure coding standards

3. **Implement Domain Selector**
   - Add dropdown in UI: "CVE Advisories" | "Coding Guidance"
   - Filter corpus retrieval by domain metadata
   - Update query examples per domain

4. **Expand Red Flags**
   - Add RED_FLAGS_CODING to config.py
   - Source from: OWASP Top 10, CWE Top 25, SANS Top 25
   - Document sources in IMPLEMENTATION_STATUS.md

---

Last Updated: 2025-02-05
