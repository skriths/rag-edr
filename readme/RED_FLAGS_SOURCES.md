# Red Flag Detection Sources

This document details the sources and methodology for red flag keyword detection in the RAG-EDR system, providing traceability for production deployment and compliance.

---

## Overview

Red flag detection is a critical signal in the RAG-EDR integrity scoring system. It uses multi-layer keyword matching to identify malicious or insecure advice in retrieved documents. Keywords are sourced from industry-standard security frameworks and vulnerability databases.

**Current Implementation:** `config.py` contains `RED_FLAGS` dictionary with 5 categories
**Production Requirement:** Systematic, asynchronous updates from trusted sources

---

## Current RED_FLAGS (CVE Advisory Domain)

### 1. Security Downgrade
**Definition:** Instructions to disable or weaken security controls

**Keywords:**
- `disable firewall`
- `turn off waf`
- `skip security`
- `bypass firewall`
- `disable antivirus`

**Sources:**
- **NIST SP 800-53** (Rev 5): Security and Privacy Controls for Information Systems
  - Control SC-7: Boundary Protection
  - Control SI-3: Malicious Code Protection
  - URL: https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final

- **CIS Critical Security Controls v8**
  - Control 9: Email and Web Browser Protections
  - Control 10: Malware Defenses
  - URL: https://www.cisecurity.org/controls/v8

- **MITRE ATT&CK Framework**
  - Technique T1562: Impair Defenses
  - Sub-technique T1562.001: Disable or Modify Tools
  - URL: https://attack.mitre.org/techniques/T1562/

### 2. Dangerous Permissions
**Definition:** File system permission changes that violate least privilege principle

**Keywords:**
- `chmod 777`
- `chmod -R 777`
- `world-writable`
- `chmod 666`

**Sources:**
- **CWE-732**: Incorrect Permission Assignment for Critical Resource
  - URL: https://cwe.mitre.org/data/definitions/732.html
  - Rank: #25 in CWE Top 25 Most Dangerous Software Weaknesses (2023)

- **OWASP Top 10** (2021)
  - A01:2021 - Broken Access Control
  - URL: https://owasp.org/Top10/A01_2021-Broken_Access_Control/

- **NIST SP 800-53 Rev 5**
  - Control AC-6: Least Privilege
  - Control AC-3: Access Enforcement

- **Center for Internet Security (CIS) Benchmarks**
  - Section 6: File System Permissions
  - Applies to: Linux, Unix, Windows Server benchmarks
  - URL: https://www.cisecurity.org/cis-benchmarks

### 3. Severity Downplay
**Definition:** Language minimizing the importance of critical vulnerabilities

**Keywords:**
- `low priority`
- `not urgent`
- `ignore cve`
- `defer patching`
- `low impact`

**Sources:**
- **CVSS v3.1 Specification** (Common Vulnerability Scoring System)
  - Defines severity ratings: CRITICAL (9.0-10.0), HIGH (7.0-8.9), MEDIUM (4.0-6.9), LOW (0.1-3.9)
  - URL: https://www.first.org/cvss/v3.1/specification-document
  - Published by: Forum of Incident Response and Security Teams (FIRST)

- **CISA Known Exploited Vulnerabilities (KEV) Catalog**
  - Mandates patching timelines for federal agencies
  - CRITICAL: 15 days, HIGH: 30 days
  - URL: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

- **NIST NVD Severity Distribution Analysis** (2023)
  - Demonstrates correlation between CVSS score and exploitation in the wild
  - URL: https://nvd.nist.gov/general/visualizations/vulnerability-visualizations

### 4. Unsafe Operations
**Definition:** Instructions to skip security verification steps

**Keywords:**
- `skip verification`
- `bypass check`
- `disable validation`
- `ignore warnings`
- `skip gpg`

**Sources:**
- **NIST SP 800-161**: Cybersecurity Supply Chain Risk Management Practices
  - Section 3.3: Verification of Software Integrity
  - Mandates cryptographic verification of software packages
  - URL: https://csrc.nist.gov/publications/detail/sp/800-161/rev-1/final

- **CWE-345**: Insufficient Verification of Data Authenticity
  - URL: https://cwe.mitre.org/data/definitions/345.html

- **ISO/IEC 27001:2022**
  - Control A.8.32: Change Management
  - Requires verification of changes before deployment

- **SANS Securing Linux Production Systems (SEC506)**
  - Module 3: Package Management Security
  - Emphasizes GPG signature verification for all packages
  - URL: https://www.sans.org/cyber-security-courses/securing-linux-unix/

### 5. Social Engineering
**Definition:** Manipulative language designed to bypass security processes

**Keywords:**
- `trust this source`
- `urgent action`
- `verify later`
- `pre-approved`
- `already validated`

**Sources:**
- **MITRE ATT&CK Framework**
  - Technique T1566: Phishing
  - Technique T1204: User Execution
  - URL: https://attack.mitre.org/techniques/T1566/

- **NIST SP 800-61 Rev 2**: Computer Security Incident Handling Guide
  - Section 3.2.4: Social Engineering Attacks
  - URL: https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final

- **SANS Security Awareness Training**
  - Identifies urgency, authority, and trust exploitation as top social engineering tactics
  - URL: https://www.sans.org/security-awareness-training/

---

## Planned RED_FLAGS_CODING (Coding Guidance Domain)

### 1. Credential Exposure
**Definition:** Hardcoding secrets, API keys, or credentials in code

**Keywords:**
- `hardcode api key`
- `commit secrets`
- `store password in code`
- `api_key = "sk-`
- `password = "`

**Sources:**
- **OWASP Top 10** (2021)
  - A07:2021 - Identification and Authentication Failures
  - URL: https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/

- **CWE-798**: Use of Hard-coded Credentials
  - Rank: #16 in CWE Top 25 (2023)
  - URL: https://cwe.mitre.org/data/definitions/798.html

- **GitHub Secret Scanning Patterns**
  - Open-source regex patterns for detecting secrets in code
  - URL: https://github.com/gitleaks/gitleaks
  - Source: Gitleaks project (30K+ GitHub stars)

- **NIST SP 800-63B**: Digital Identity Guidelines (Authentication)
  - Section 5.1.1: Memorized Secret Verifiers
  - Prohibits hardcoded secrets

### 2. Security Bypass
**Definition:** Disabling SSL/TLS verification, certificate checks, or authentication

**Keywords:**
- `disable ssl verification`
- `verify=false`
- `skip certificate check`
- `--insecure`
- `--no-verify`

**Sources:**
- **CWE-295**: Improper Certificate Validation
  - Rank: #23 in CWE Top 25 (2023)
  - URL: https://cwe.mitre.org/data/definitions/295.html

- **OWASP Mobile Top 10** (2023)
  - M3: Insecure Communication
  - URL: https://owasp.org/www-project-mobile-top-10/

- **RFC 8446**: The Transport Layer Security (TLS) Protocol Version 1.3
  - Section 4.4.2: Certificate Verification
  - URL: https://datatracker.ietf.org/doc/html/rfc8446

- **MITRE ATT&CK for Enterprise**
  - Technique T1557: Adversary-in-the-Middle
  - Sub-technique T1557.001: LLMNR/NBT-NS Poisoning
  - URL: https://attack.mitre.org/techniques/T1557/

### 3. Dangerous Operations
**Definition:** Code patterns that enable command injection or arbitrary code execution

**Keywords:**
- `eval(`
- `exec(`
- `os.system(`
- `shell=true`
- `subprocess.call(..., shell=True)`

**Sources:**
- **CWE-78**: Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')
  - Rank: #12 in CWE Top 25 (2023)
  - URL: https://cwe.mitre.org/data/definitions/78.html

- **OWASP Top 10** (2021)
  - A03:2021 - Injection
  - URL: https://owasp.org/Top10/A03_2021-Injection/

- **CWE-94**: Improper Control of Generation of Code ('Code Injection')
  - Rank: #18 in CWE Top 25 (2023)
  - URL: https://cwe.mitre.org/data/definitions/94.html

- **CERT Secure Coding Standards**
  - IDS07-J (Java): Sanitize untrusted data passed to the Runtime.exec() method
  - STR02-J: Specify an appropriate locale when comparing locale-dependent data
  - URL: https://wiki.sei.cmu.edu/confluence/display/java/SEI+CERT+Oracle+Coding+Standard+for+Java

### 4. Trust Bypass
**Definition:** Instructions to bypass package verification, ignore warnings, or disable security checks

**Keywords:**
- `--ignore-scripts=false`
- `pip install --trusted-host`
- `npm audit fix --force`
- `--disable-dependency-verification`
- `--skip-integrity-check`

**Sources:**
- **NIST SP 800-161 Rev 1**: Cybersecurity Supply Chain Risk Management
  - Section 2.2: Software Supply Chain
  - Mandates verification of software provenance
  - URL: https://csrc.nist.gov/publications/detail/sp/800-161/rev-1/final

- **CWE-494**: Download of Code Without Integrity Check
  - URL: https://cwe.mitre.org/data/definitions/494.html

- **npm Security Best Practices**
  - Recommends `npm ci` over `npm install` for CI/CD
  - Warns against `--force` flag bypassing peer dependency checks
  - URL: https://docs.npmjs.com/cli/v10/commands/npm-audit

- **Python Package Index (PyPI) Security Policy**
  - Requires PGP signatures for critical packages
  - URL: https://pypi.org/security/

---

## Production Implementation Strategy

### Phase 1: Static Configuration (Current)
**Status:** ✅ Implemented in `config.py`
**Approach:** Hardcoded keyword lists sourced from standards above
**Pros:** Fast, deterministic, explainable
**Cons:** Requires manual updates, no adaptive learning

### Phase 2: Periodic Updates (MVP Target)
**Status:** ⚠️ Planned (4-6 weeks)
**Approach:** Asynchronous daily/weekly updates from trusted sources

**Implementation:**
```python
# engine/detection/red_flag_updater.py
import asyncio
import httpx
from bs4 import BeautifulSoup

class RedFlagUpdater:
    """
    Periodically fetches updated red flags from trusted sources.
    """

    SOURCES = {
        "cwe_top_25": "https://cwe.mitre.org/top25/archive/2023/2023_top25_list.json",
        "owasp_top_10": "https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/",
        "mitre_attack": "https://attack.mitre.org/techniques/enterprise/"
    }

    async def fetch_cwe_keywords(self) -> dict:
        """Fetch keywords from CWE Top 25"""
        async with httpx.AsyncClient() as client:
            response = await client.get(self.SOURCES["cwe_top_25"])
            data = response.json()
            # Parse and extract relevant weakness descriptions
            return self.parse_cwe_to_keywords(data)

    async def update_config(self):
        """Update config.py with latest red flags"""
        # Merge with existing keywords
        # Write to config.py with timestamp
        pass

# Scheduled via cron or systemd timer
# Daily: 2 AM UTC
```

**Data Sources for Automated Updates:**
1. **CWE Top 25 JSON Feed**
   - URL: https://cwe.mitre.org/top25/archive/2023/2023_top25_list.json
   - Update frequency: Annually (but we poll weekly)

2. **MITRE ATT&CK STIX/TAXII Feed**
   - URL: https://github.com/mitre-attack/attack-stix-data
   - Update frequency: Quarterly
   - Format: JSON (STIX 2.1)

3. **CISA KEV Catalog JSON**
   - URL: https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
   - Update frequency: Daily
   - Contains CVE IDs with exploitation status

4. **GitHub Advisory Database**
   - URL: https://github.com/github/advisory-database
   - Update frequency: Real-time
   - Contains security advisories for npm, PyPI, etc.

### Phase 3: ML-Based Detection (Production Target)
**Status:** ❌ Not Implemented (6-12 months)
**Approach:** Fine-tuned transformer model for malicious pattern detection

**Implementation:**
```python
# engine/detection/ml_red_flag_detector.py
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class MLRedFlagDetector:
    """
    ML-based red flag detection using fine-tuned BERT.
    """

    def __init__(self, model_path: str):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)

    def predict(self, text: str) -> dict:
        """
        Returns:
            {
                "is_malicious": bool,
                "confidence": float,
                "detected_patterns": list[str],
                "categories": list[str]
            }
        """
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True)
        outputs = self.model(**inputs)
        # Post-process logits
        return self.parse_predictions(outputs)
```

**Training Data Sources:**
1. **Malicious StackOverflow Answers Dataset**
   - Source: Security researchers, honeypot data
   - Size: 10,000+ labeled examples
   - Labels: malicious, insecure, misleading, safe

2. **CVE Advisory Corpus**
   - Source: NVD, Mitre, vendor advisories
   - Size: 50,000+ documents
   - Use for contrastive learning (clean vs poisoned)

3. **GitHub Leaked Secrets Dataset**
   - Source: truffleHog, gitleaks scans
   - Size: 100,000+ examples of hardcoded credentials
   - Labels: credential type, severity

**Model Architecture:**
- Base: `sentence-transformers/all-MiniLM-L6-v2` (fine-tuned)
- Task: Multi-label classification (5 categories)
- Training: 3 epochs, learning rate 2e-5
- Validation: 80/20 train/test split, F1 score >0.92

---

## Maintenance and Updates

### Quarterly Review Cycle
**Responsible Team:** Security Engineering + Data Science
**Cadence:** Every 3 months

**Review Checklist:**
- [ ] Review CWE Top 25 updates
- [ ] Check OWASP Top 10 revisions
- [ ] Analyze false positive rate from production logs
- [ ] Incorporate analyst feedback from quarantine reviews
- [ ] Add keywords from newly discovered attack patterns
- [ ] Remove deprecated patterns (e.g., Flash-related vulnerabilities)

### Audit Trail
All changes to red flag keywords must be logged with:
- Timestamp
- Source (e.g., "CWE-798 added from CWE Top 25 2024 update")
- Justification (e.g., "Seen in 3 production poisoning attempts")
- Approver (e.g., "Approved by Security Lead")

**Implementation:**
```python
# config.py
RED_FLAGS_AUDIT = [
    {
        "date": "2025-02-05",
        "category": "credential_exposure",
        "keyword": "hardcode api key",
        "source": "CWE-798 (CWE Top 25 2023)",
        "justification": "Common pattern in API integration poisoning",
        "approver": "security-lead@company.com"
    }
]
```

---

## Compliance Mapping

### NIST Cybersecurity Framework v1.1
- **Identify (ID)**: ID.RA-5 (Threats, vulnerabilities, and risks are identified)
- **Protect (PR)**: PR.DS-6 (Integrity checking mechanisms verify software integrity)
- **Detect (DE)**: DE.CM-4 (Malicious code is detected)

### ISO/IEC 27001:2022
- **A.8.31**: Separation of development, test, and production environments
- **A.8.32**: Change management (verification of changes)
- **A.5.7**: Threat intelligence (incorporating threat data)

### SOC 2 Type II
- **CC6.1**: Logical and Physical Access Controls
- **CC6.6**: Reporting of Security Incidents
- **CC7.2**: Monitoring of System Components

---

## References

1. **NIST Special Publications**
   - SP 800-53 Rev 5: Security and Privacy Controls
   - SP 800-61 Rev 2: Computer Security Incident Handling
   - SP 800-161 Rev 1: Cybersecurity Supply Chain Risk Management

2. **OWASP Resources**
   - OWASP Top 10 (2021)
   - OWASP Mobile Top 10 (2023)
   - OWASP API Security Top 10

3. **CWE/MITRE Resources**
   - CWE Top 25 Most Dangerous Software Weaknesses
   - MITRE ATT&CK Framework for Enterprise
   - CAPEC (Common Attack Pattern Enumeration and Classification)

4. **Industry Standards**
   - CIS Critical Security Controls v8
   - SANS Top 25 Software Errors
   - CVSS v3.1 Specification

5. **Government Resources**
   - CISA Known Exploited Vulnerabilities Catalog
   - NSA/CISA Kubernetes Hardening Guide
   - UK NCSC Cloud Security Guidance

---

## Appendix: Example Red Flag Detection

### Example 1: Security Downgrade
**Input Document:**
```
To troubleshoot the firewall issue, temporarily disable firewall rules:
sudo systemctl stop firewalld
```

**Detection:**
- Keyword matched: "disable firewall"
- Category: security_downgrade
- Score impact: -0.35 (red flag score drops to 65%)
- Action: If combined with other signals, triggers quarantine

### Example 2: Dangerous Permissions
**Input Document:**
```
If you encounter permission errors, run:
chmod -R 777 /var/www/html
```

**Detection:**
- Keyword matched: "chmod -R 777"
- Category: dangerous_permissions
- Score impact: -0.40 (red flag score drops to 60%)
- Action: High severity flag

### Example 3: Multiple Categories (Cross-Category Amplification)
**Input Document:**
```
Quick fix for Redis:
1. chmod 777 /var/lib/redis
2. Disable firewall temporarily
3. Skip gpg verification for faster install
```

**Detection:**
- Keywords matched: "chmod 777", "disable firewall", "skip gpg"
- Categories: dangerous_permissions, security_downgrade, unsafe_operations (3 categories)
- Score impact: Base -0.45, amplified by 0.70x = 31% final score
- Action: Immediate quarantine (multiple red flags across 3+ categories)

---

Last Updated: 2025-02-05
Version: 1.0
