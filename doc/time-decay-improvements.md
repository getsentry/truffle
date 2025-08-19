# Time Decay Implementation Strategy

## Overview

This document outlines time decay implementation approaches for the expertise system, from simple query-time calculations to advanced pre-computed optimizations.

## Current Implementation: Query-Time Calculation

**Initial approach**: Simple query-time exponential decay calculation directly on the `expertise_evidence` table.

### Simple Expert Query with Exponential Decay

```sql
-- Current implementation: Query-time calculation with exponential decay
SELECT
    u.display_name,
    u.slack_id,
    s.name as skill_name,
    -- Calculate score with exponential decay
    AVG(
        CASE
            WHEN ee.label = 'positive_expertise' THEN ee.confidence
            WHEN ee.label = 'negative_expertise' THEN -ee.confidence * 0.5
            ELSE 0
        END *
        POWER(0.95, EXTRACT(DAYS FROM (CURRENT_DATE - ee.evidence_date)))
    ) as expertise_score,
    COUNT(*) as evidence_count
FROM expertise_evidence ee
JOIN users u ON ee.user_id = u.user_id
JOIN skills s ON ee.skill_id = s.skill_id
WHERE s.skill_key = 'react'
  AND ee.evidence_date >= CURRENT_DATE - INTERVAL '180 days'  -- Only recent evidence
GROUP BY u.user_id, u.display_name, u.slack_id, s.name
HAVING expertise_score > 0.1  -- Filter out low scores
ORDER BY expertise_score DESC
LIMIT 10;
```

### Required Indexes

```sql
-- Essential indexes for query-time calculation performance
CREATE INDEX idx_evidence_skill_date ON expertise_evidence(skill_id, evidence_date DESC);
CREATE INDEX idx_evidence_user_date ON expertise_evidence(user_id, evidence_date DESC);
```

### Performance Characteristics
- **100K messages**: ~50-200ms queries
- **Implementation time**: 30 minutes
- **Maintenance**: Zero background jobs
- **Complexity**: Low

---

## Future Improvement: Hybrid with Incremental Updates

**When to implement**: If query-time calculation becomes too slow (> 500ms) or we need sub-10ms response times.

### Strategy: Hybrid with Incremental Updates

#### Core Components

1. **Pre-computed scores** in `user_skill_scores` table
2. **Incremental updates** when new evidence arrives
3. **Periodic decay recalculation** (daily/weekly background jobs)
4. **Query-time decay** for real-time accuracy

#### Implementation

##### 1. Fast Expert Queries (< 10ms)

```sql
-- Query pre-computed scores with real-time decay applied
SELECT u.display_name, u.slack_id, s.name,
       uss.score * POWER(0.95, EXTRACT(DAYS FROM (CURRENT_DATE - uss.last_evidence_date))) AS current_score
FROM user_skill_scores uss
JOIN users u ON uss.user_id = u.user_id
JOIN skills s ON uss.skill_id = s.skill_id
WHERE s.skill_key = 'react'
ORDER BY current_score DESC
LIMIT 10;
```

##### 2. Incremental Score Updates

When new evidence arrives from the classifier:

```python
def update_user_skill_score(user_id: int, skill_id: int, new_evidence: Evidence):
    """Update user skill score incrementally when new evidence arrives."""

    # Get current score or initialize new record
    current = get_user_skill_score(user_id, skill_id)
    if not current:
        current = UserSkillScore(score=0.0, evidence_count=0, last_evidence_date=new_evidence.evidence_date)

    # Calculate incremental update using exponential moving average
    alpha = 0.1  # Learning rate - adjust based on evidence frequency
    evidence_value = calculate_evidence_value(new_evidence.label, new_evidence.confidence)
    new_score = (1 - alpha) * current.score + alpha * evidence_value

    # Update or insert record
    upsert_user_skill_score(
        user_id=user_id,
        skill_id=skill_id,
        score=new_score,
        evidence_count=current.evidence_count + 1,
        last_evidence_date=new_evidence.evidence_date,
        updated_at=datetime.utcnow()
    )

def calculate_evidence_value(label: str, confidence: float) -> float:
    """Convert evidence label and confidence to numeric value."""
    multipliers = {
        'positive_expertise': 1.0,
        'neutral': 0.0,
        'negative_expertise': -0.5  # Penalize negative evidence
    }
    return confidence * multipliers.get(label, 0.0)
```

##### 3. Periodic Decay Updates (Background Job)

```sql
-- Daily batch job to apply time decay to all scores
UPDATE user_skill_scores
SET score = score * POWER(0.98, 1),  -- Daily decay factor (2% daily decay)
    updated_at = NOW()
WHERE updated_at < CURRENT_DATE;

-- Remove scores that have decayed below threshold
DELETE FROM user_skill_scores
WHERE score < 0.01 AND last_evidence_date < CURRENT_DATE - INTERVAL '365 days';
```

##### 4. Performance Optimizations

###### Materialized View for Ultra-Fast Queries

```sql
-- Materialized view for top experts per skill
CREATE MATERIALIZED VIEW top_experts AS
SELECT skill_id, user_id, score,
       ROW_NUMBER() OVER (PARTITION BY skill_id ORDER BY score DESC) as rank
FROM user_skill_scores
WHERE score > 0.1  -- Only include meaningful scores
ORDER BY skill_id, score DESC;

CREATE INDEX idx_top_experts_skill_rank ON top_experts(skill_id, rank);

-- Refresh daily (can be done concurrently for zero downtime)
REFRESH MATERIALIZED VIEW CONCURRENTLY top_experts;
```

###### Expert Query Using Materialized View

```sql
-- Ultra-fast expert lookup (< 5ms)
SELECT u.display_name, u.slack_id, s.name, te.score
FROM top_experts te
JOIN users u ON te.user_id = u.user_id
JOIN skills s ON te.skill_id = s.skill_id
WHERE s.skill_key = 'react'
  AND te.rank <= 10
ORDER BY te.rank;
```

#### Time Decay Models

##### Exponential Decay (Recommended)

```python
def apply_exponential_decay(base_score: float, days_old: int, half_life_days: int = 90) -> float:
    """Apply exponential decay with configurable half-life."""
    return base_score * (0.5 ** (days_old / half_life_days))
```

##### Linear Decay

```python
def apply_linear_decay(base_score: float, days_old: int, max_age_days: int = 365) -> float:
    """Apply linear decay over specified time period."""
    decay_factor = max(0.0, 1.0 - (days_old / max_age_days))
    return base_score * decay_factor
```

##### Step Decay

```python
def apply_step_decay(base_score: float, days_old: int) -> float:
    """Apply step-based decay with discrete time windows."""
    if days_old <= 30:
        return base_score * 1.0     # 100% for recent (last month)
    elif days_old <= 90:
        return base_score * 0.8     # 80% for medium-old (last quarter)
    elif days_old <= 180:
        return base_score * 0.5     # 50% for old (last 6 months)
    else:
        return base_score * 0.2     # 20% for very old
```

#### Performance Characteristics

| Operation | Strategy | Expected Time | Frequency |
|-----------|----------|---------------|-----------|
| **Expert Query** | Pre-computed + materialized view | < 5ms | Per user request |
| **New Evidence Processing** | Incremental update | < 50ms | Per classified message |
| **Decay Update** | Batch processing | 1-5 minutes | Daily |
| **Materialized View Refresh** | Background refresh | 30 seconds | Daily |

#### Implementation Schedule

##### Phase 1: Basic Pre-computation
1. Implement `user_skill_scores` table population
2. Basic incremental updates on new evidence
3. Simple exponential decay queries

##### Phase 2: Optimization
1. Add materialized views for top experts
2. Implement background decay jobs
3. Query optimization and indexing

##### Phase 3: Advanced Features
1. Configurable decay parameters per skill domain
2. Evidence type-specific decay rates
3. Real-time score recalculation triggers

#### Configuration Parameters

```python
# Decay configuration
DECAY_HALF_LIFE_DAYS = 90           # How quickly expertise decays
LEARNING_RATE = 0.1                 # How much new evidence affects score
MIN_SCORE_THRESHOLD = 0.01          # Minimum score to keep in database
MAX_EVIDENCE_AGE_DAYS = 365         # Maximum age of evidence to consider

# Performance tuning
BATCH_UPDATE_SIZE = 1000            # Records to update per batch
MATERIALIZED_VIEW_REFRESH_HOUR = 2  # Daily refresh time (2 AM)
```

#### Benefits

✅ **Query Speed**: Sub-10ms expert lookups even with millions of messages
✅ **Real-time Updates**: New evidence processed incrementally
✅ **Scalable**: Handles 100,000s of messages efficiently
✅ **Flexible**: Supports multiple decay models
✅ **Memory Efficient**: Only stores aggregated scores, not raw messages
✅ **Privacy Preserving**: No message content in performance-critical tables
