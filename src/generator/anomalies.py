"""
Explicit edge cases, negative scenarios, and ground truth schema.
"""
from typing import List, Dict, Any

ANOMALY_DEFINITIONS = {
    "ERR_ORPHAN_COMPLAINT": {
        "description": "Complaint references a non-existent customer ID.",
        "category": "Referential Integrity",
        "entity": "complaints",
        "expected_behavior": "Foreign key check failure; complaint must reference valid customer."
    },
    "ERR_TEMPORAL_INVERSION": {
        "description": "Resolution timestamp is chronologically prior to complaint creation timestamp.",
        "category": "Temporal Consistency",
        "entity": "resolutions",
        "expected_behavior": "resolved_at must be strictly greater than or equal to created_at."
    },
    "ERR_INVALID_SLA_PAUSE": {
        "description": "SLA clock status is PAUSED while complaint status is not PENDING_CUSTOMER.",
        "category": "State Machine Invariant",
        "entity": "sla_clocks",
        "expected_behavior": "SLA clock can only be PAUSED when complaint is in PENDING_CUSTOMER state."
    },
    "ERR_UNLINKED_RECURRENCE": {
        "description": "Customer filed identical category issue within 7 days, but is_repeat_complaint is False.",
        "category": "Business Rule Invariant",
        "entity": "complaints",
        "expected_behavior": "Prior complaint within 30 days must be flagged is_repeat_complaint=True with parent_complaint_id."
    },
    "ERR_SAFETY_PRIORITY_MISMATCH": {
        "description": "Critical safety issue assigned to P4_LOW priority queue instead of P1_CRITICAL.",
        "category": "Priority Rule Violation",
        "entity": "complaints",
        "expected_behavior": "Product safety issues must evaluate to P1_CRITICAL and route to Safety Board."
    },
    "ERR_PREMATURE_SURVEY": {
        "description": "Customer satisfaction survey submitted before complaint resolution/closure.",
        "category": "Lifecycle Milestone Violation",
        "entity": "surveys",
        "expected_behavior": "Survey can only be created and submitted after complaint is RESOLVED or CLOSED."
    }
}

class GroundTruthTracker:
    """
    Collects ground truth decisions, true labels, and injected anomalies.
    Maintained separately from runtime feature data to prevent leakage.
    """
    def __init__(self):
        self.anomalies: List[Dict[str, Any]] = []
        self.classification_ground_truth: List[Dict[str, Any]] = []

    def record_anomaly(
        self,
        anomaly_code: str,
        entity_id: str,
        entity_type: str,
        field_name: str,
        injected_value: Any,
        expected_value: Any,
        notes: str = ""
    ):
        definition = ANOMALY_DEFINITIONS.get(anomaly_code, {})
        self.anomalies.append({
            "anomaly_id": f"ANO-{len(self.anomalies) + 1:04d}",
            "anomaly_code": anomaly_code,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "field_name": field_name,
            "injected_value": str(injected_value),
            "expected_value": str(expected_value),
            "category": definition.get("category", "General"),
            "description": definition.get("description", ""),
            "notes": notes
        })

    def record_classification(
        self,
        complaint_id: str,
        true_category: str,
        true_priority: str,
        rule_applied: str,
        is_safety: bool,
        is_vulnerable: bool
    ):
        self.classification_ground_truth.append({
            "complaint_id": complaint_id,
            "true_category": true_category,
            "true_priority": true_priority,
            "rule_applied": rule_applied,
            "is_safety": is_safety,
            "is_vulnerable": is_vulnerable
        })
