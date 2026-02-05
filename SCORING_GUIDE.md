# RAG-EDR Scoring System Guide

## Critical UX Issue: Score Display Semantics

### The Problem

**Current Display:**
```
Trust: 100%        (Green)
Red Flag: 100%     (Green)
Anomaly: 78%       (Yellow)
Semantic: 70%      (Yellow)
```

**User Interpretation:**
- "Red Flag 100%" sounds like "100% red flags detected" = BAD ❌
- Even with green color, the semantics contradict the visual

**Reality:**
- 100% = CLEAN (no issues)
- 0% = PROBLEMATIC (maximum issues)

### The Solution: Invert the Display

**Option 1: Show Risk Instead of Score (RECOMMENDED)**
```
Trust Risk: 0%        (Green)  ← Inverted
Red Flags: 0%         (Green)  ← Inverted
Anomaly Risk: 22%     (Green)  ← Inverted
Semantic Drift: 30%   (Yellow) ← Inverted
```

**Option 2: Rename Metrics**
```
Source Trust: 100%         (Green)
Safety Score: 100%         (Green)
Distribution: Normal       (Green)
Corpus Alignment: 70%      (Yellow)
```

**Option 3: Use Status Labels**
```
Source: TRUSTED       (Green badge)
Content: CLEAN        (Green badge)
Distribution: NORMAL  (Green badge)
Semantics: ALIGNED    (Yellow badge)
```

### Implementation

For the hackathon demo, **quick fix in dashboard**:

**File: `dashboard/app.jsx`**

Change the `IntegrityGauges` component:

```jsx
// OLD (Confusing):
const signalLabels = {
    trust_score: 'Trust',
    red_flag_score: 'Red Flag',
    anomaly_score: 'Anomaly',
    semantic_drift_score: 'Semantic'
};

// NEW (Clear):
const signalLabels = {
    trust_score: 'Source Trust',
    red_flag_score: 'Safety Score',    // Or 'Content Safety'
    anomaly_score: 'Distribution',
    semantic_drift_score: 'Alignment'
};
```

**OR use risk display (invert values):**

```jsx
// Display as risk percentage
const displayValue = (score, key) => {
    if (key === 'red_flag_score' || key === 'anomaly_score') {
        return ((1 - score) * 100).toFixed(0) + '%';  // Invert
    }
    return (score * 100).toFixed(0) + '%';  // Normal
};

const signalLabels = {
    trust_score: 'Trust Level',
    red_flag_score: 'Red Flags',        // Now 0% = clean, 100% = bad
    anomaly_score: 'Anomaly Risk',      // Now 0% = normal, 100% = anomalous
    semantic_drift_score: 'Alignment'
};
```

---

## Score Interpretation Reference

### How Scores Work

**All scores are 0.0 to 1.0 (displayed as 0% to 100%)**

| Score | Meaning | Color | Status |
|-------|---------|-------|--------|
| **0.9 - 1.0** | Excellent - No issues detected | Green | PASS |
| **0.7 - 0.9** | Good - Minor concerns | Green/Yellow | PASS |
| **0.5 - 0.7** | Concerning - Multiple signals | Yellow | WARNING |
| **0.3 - 0.5** | Problematic - Significant issues | Orange | QUARANTINE CANDIDATE |
| **0.0 - 0.3** | Critical - Severe issues detected | Red | QUARANTINE |

### Signal-Specific Meanings

#### 1. Trust Score (0-100%)
- **100%:** Fully trusted source (nvd.nist.gov, cve.mitre.org)
- **90%:** Verified source (Ubuntu Security, Red Hat)
- **50%:** Unverified source
- **30%:** Unknown/suspicious source
- **0%:** Known malicious source

**Calculation:** Direct lookup from config.TRUST_SOURCES

#### 2. Red Flag Score (0-100%)
- **100%:** No red flags detected (clean content)
- **80%:** 1-2 minor flags (acceptable)
- **60%:** Multiple flags in 1 category (concerning)
- **40%:** Flags in 2-3 categories (problematic)
- **20%:** Flags in 4+ categories (critical)
- **0%:** Maximum red flags (malicious)

**What Lowers the Score:**
- Detected keywords: "disable firewall", "chmod 777", "skip verification"
- Multiple categories hit: Security downgrade + dangerous permissions
- Cross-category amplification: More categories = exponential penalty

**Calculation:**
```python
flag_ratio = detected_flags / total_possible_flags
base_score = 1.0 - (flag_ratio * 1.5)  # 1.5x amplifier
if 4+ categories: base_score *= 0.60
if 3+ categories: base_score *= 0.70
if 2+ categories: base_score *= 0.80
```

#### 3. Anomaly Score (0-100%)
- **100%:** Common source (>20% of corpus)
- **80%:** Moderately common source
- **60%:** Rare source (<20% of corpus)
- **40%:** Very rare source, trust variance high
- **20%:** Extreme outlier
- **0%:** Never seen before, very low trust

**What Lowers the Score:**
- Source appears rarely in corpus
- Trust score differs significantly from corpus average
- High Z-score deviation

**Calculation:**
```python
frequency_score = min(source_frequency / 0.2, 1.0)
variance_score = max(0.0, 1.0 - (z_score / 3.0))
combined = (frequency * 0.6) + (variance * 0.4)
```

#### 4. Semantic Drift Score (0-100%)
- **100%:** Perfect match to golden corpus
- **80%:** High similarity to golden corpus
- **60%:** Moderate similarity
- **40%:** Low similarity, drifting from baseline
- **20%:** Very different from golden corpus
- **0%:** Complete semantic divergence

**What Lowers the Score:**
- Low cosine similarity to golden documents
- Content semantically far from security best practices
- Language patterns unlike trusted advisories

**Calculation:**
```python
max_similarity = max(cosine_similarity(doc, golden_doc) for golden_doc in golden_corpus)
score = (max_similarity + 1.0) / 2.0  # Normalize from [-1,1] to [0,1]
```

---

## Quarantine Decision Logic

### Trigger Rule: 2 of 4 Signals Below Threshold

**Threshold:** 0.5 (50%)

**Examples:**

**Case 1: Quarantine Triggered ⚠️**
```
Trust: 30% (BELOW)     ← Red
Red Flag: 40% (BELOW)  ← Red
Anomaly: 70%           ← Yellow
Semantic: 65%          ← Yellow

Result: 2 signals below 50% → QUARANTINE
```

**Case 2: Warning (No Quarantine) ⚠️**
```
Trust: 30% (BELOW)     ← Red
Red Flag: 55%          ← Yellow
Anomaly: 80%           ← Green
Semantic: 70%          ← Yellow

Result: 1 signal below 50% → WARNING (no action)
```

**Case 3: Clean ✅**
```
Trust: 100%            ← Green
Red Flag: 100%         ← Green
Anomaly: 85%           ← Green
Semantic: 75%          ← Yellow

Result: 0 signals below 50% → CLEAN (pass)
```

---

## Why These Thresholds?

### 50% Threshold
- **Industry standard** for binary decision boundaries
- **Balanced:** Not too sensitive (false positives) or permissive (false negatives)
- **Tunable:** Can adjust based on security posture

### 2-of-4 Rule
- **Prevents single-signal false positives**
- **Requires correlation** across multiple detection methods
- **Reduces noise** from imperfect heuristics
- **Mimics EDR logic** (multiple indicators = higher confidence)

### Signal Weights
```python
trust: 0.25        # Source matters
red_flag: 0.35     # Content is most important (highest weight)
anomaly: 0.15      # Statistical outlier detection (supplementary)
semantic: 0.25     # Alignment to golden corpus
```

**Why red_flag has highest weight:**
- Most direct evidence of malicious content
- Keyword detection is reliable (low false positive rate)
- Multi-category detection is strong signal

---

## Evolution Path (Phase 2+)

### Current: Heuristic-Based (Phase 1)
- ✅ Keyword matching
- ✅ Statistical analysis
- ✅ Embedding similarity
- ✅ Fixed thresholds

### Future: ML-Based (Phase 2)
- 🔲 Trained classifier for red flag detection
- 🔲 Dynamic threshold adjustment
- 🔲 NLI (Natural Language Inference) for contradiction detection
- 🔲 Contextual anomaly detection with baselines
- 🔲 Adversarial robustness testing

### Future: Adaptive (Phase 3)
- 🔲 Per-organization tuning
- 🔲 Feedback loop from analyst actions
- 🔲 A/B testing framework
- 🔲 Real-time threshold optimization

---

## Recommendations for Demo/Presentation

### What to Say:

**Good:**
> "Higher scores indicate better security posture. When multiple signals drop below 50%, we quarantine the document."

**Better:**
> "We use four complementary signals - source trust, content safety, statistical distribution, and semantic alignment. If two or more signals indicate concern, automatic quarantine is triggered."

**Best:**
> "Think of these as health scores - 100% means perfectly healthy, 0% means critically compromised. Our system requires corroboration: at least two independent signals must agree before taking action, reducing false positives while maintaining security."

### What NOT to Say:
- ❌ "Red Flag 100% means 100% red flags" (inverted logic)
- ❌ "This is a completely novel algorithm" (it's adapted from proven methods)
- ❌ "The threshold is scientifically derived" (it's heuristically tuned)

### Visual Aids for Presentation:
1. **Before/After comparison** showing score changes
2. **Traffic light metaphor** (Green/Yellow/Red zones)
3. **Dashboard screenshot** with annotations
4. **Example quarantine decision** with clear logic flow

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────┐
│ RAG-EDR Score Quick Reference                       │
├─────────────────────────────────────────────────────┤
│ GREEN  (70-100%): PASS - No action needed          │
│ YELLOW (50-70%):  WARN - Monitor closely           │
│ RED    (0-50%):   FAIL - Quarantine candidate      │
├─────────────────────────────────────────────────────┤
│ Quarantine Rule: 2+ signals in RED zone            │
└─────────────────────────────────────────────────────┘

📊 Signal Weights:
   Red Flag: 35% (highest - content analysis)
   Trust:    25% (source reputation)
   Semantic: 25% (alignment to golden corpus)
   Anomaly:  15% (statistical outlier)

⚡ Trigger: 2 of 4 signals below 50% threshold
```

---

## Context for Future Development

As the system evolves, remember:

1. **Current scoring is MVP** - Heuristic-based, tuned for demo
2. **Threshold (50%) is configurable** - Adjust per deployment
3. **Signal weights are tunable** - Based on false positive tolerance
4. **Phase 2 will add ML** - Trained models, dynamic thresholds
5. **Display semantics matter** - UX must match user mental model

**Key Design Decision:** We chose score=1.0 as "good" to match:
- Standard ML conventions (accuracy, precision, recall)
- Quality score metaphors (100% = perfect)
- Health score analogies

**Trade-off:** Less intuitive for "Red Flag" metric specifically, hence the recommendation to rename or invert display.
