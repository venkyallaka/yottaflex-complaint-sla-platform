"""
Business rules, categories, priority rules, and SLA definitions.
"""
from typing import Dict, Any, List

CATEGORIES_DATA = [
    {
        "category_id": "CAT-01",
        "category_name": "Product Safety & Hazard",
        "default_severity": "CRITICAL",
        "assigned_team": "Safety & Regulatory Escalations",
        "is_safety_critical": True
    },
    {
        "category_id": "CAT-02",
        "category_name": "Defective / Damaged Item",
        "default_severity": "HIGH",
        "assigned_team": "Product Quality Team",
        "is_safety_critical": False
    },
    {
        "category_id": "CAT-03",
        "category_name": "Late or Missing Delivery",
        "default_severity": "MEDIUM",
        "assigned_team": "Logistics & Fulfillment",
        "is_safety_critical": False
    },
    {
        "category_id": "CAT-04",
        "category_name": "Billing & Overcharge",
        "default_severity": "HIGH",
        "assigned_team": "Finance & Billing Ops",
        "is_safety_critical": False
    },
    {
        "category_id": "CAT-05",
        "category_name": "Refund & Return Processing",
        "default_severity": "MEDIUM",
        "assigned_team": "Returns & Settlement",
        "is_safety_critical": False
    },
    {
        "category_id": "CAT-06",
        "category_name": "Account Access & Security",
        "default_severity": "HIGH",
        "assigned_team": "Security & Identity",
        "is_safety_critical": False
    },
    {
        "category_id": "CAT-07",
        "category_name": "Poor Customer Service",
        "default_severity": "MEDIUM",
        "assigned_team": "Service Excellence Team",
        "is_safety_critical": False
    },
    {
        "category_id": "CAT-08",
        "category_name": "Missing Parts / Accessories",
        "default_severity": "LOW",
        "assigned_team": "Inventory & Parts Ops",
        "is_safety_critical": False
    },
    {
        "category_id": "CAT-09",
        "category_name": "Misleading Description",
        "default_severity": "LOW",
        "assigned_team": "Catalog & Compliance",
        "is_safety_critical": False
    },
    {
        "category_id": "CAT-10",
        "category_name": "Technical & Software Glitch",
        "default_severity": "MEDIUM",
        "assigned_team": "Technical Support Tier 2",
        "is_safety_critical": False
    }
]

PRIORITY_RULES_DATA = [
    {
        "rule_id": "RUL-01",
        "rule_name": "Safety Hazard Automatic Critical",
        "condition_expression": "is_safety_issue == True OR category == 'Product Safety & Hazard'",
        "target_priority": "P1_CRITICAL",
        "target_response_hours": 1,
        "target_resolution_hours": 4
    },
    {
        "rule_id": "RUL-02",
        "rule_name": "Vulnerable Customer Negative Sentiment",
        "condition_expression": "is_vulnerable == True AND sentiment_score < -0.40",
        "target_priority": "P1_CRITICAL",
        "target_response_hours": 1,
        "target_resolution_hours": 4
    },
    {
        "rule_id": "RUL-03",
        "rule_name": "Vulnerable Customer Standard Escalation",
        "condition_expression": "is_vulnerable == True",
        "target_priority": "P2_HIGH",
        "target_response_hours": 4,
        "target_resolution_hours": 24
    },
    {
        "rule_id": "RUL-04",
        "rule_name": "High Value Recurring Order Complaint",
        "condition_expression": "order_amount >= 1000.00 AND is_repeat_complaint == True",
        "target_priority": "P2_HIGH",
        "target_response_hours": 4,
        "target_resolution_hours": 24
    },
    {
        "rule_id": "RUL-05",
        "rule_name": "Severe Frustration Negative Sentiment",
        "condition_expression": "sentiment_score <= -0.70",
        "target_priority": "P2_HIGH",
        "target_response_hours": 4,
        "target_resolution_hours": 24
    },
    {
        "rule_id": "RUL-06",
        "rule_name": "High Value Standard or Repeat Complaint",
        "condition_expression": "order_amount >= 500.00 OR is_repeat_complaint == True",
        "target_priority": "P3_MEDIUM",
        "target_response_hours": 12,
        "target_resolution_hours": 48
    },
    {
        "rule_id": "RUL-07",
        "rule_name": "Default High Severity",
        "condition_expression": "severity == 'HIGH'",
        "target_priority": "P2_HIGH",
        "target_response_hours": 4,
        "target_resolution_hours": 24
    },
    {
        "rule_id": "RUL-08",
        "rule_name": "Standard Low Priority Baseline",
        "condition_expression": "DEFAULT",
        "target_priority": "P4_LOW",
        "target_response_hours": 24,
        "target_resolution_hours": 96
    }
]

SLA_TARGET_MAP = {
    "P1_CRITICAL": {"response_hours": 1, "resolution_hours": 4},
    "P2_HIGH": {"response_hours": 4, "resolution_hours": 24},
    "P3_MEDIUM": {"response_hours": 12, "resolution_hours": 48},
    "P4_LOW": {"response_hours": 24, "resolution_hours": 96}
}

def evaluate_priority(
    is_safety_issue: bool,
    category_id: str,
    is_vulnerable: bool,
    sentiment_score: float,
    order_amount: float,
    is_repeat_complaint: bool,
    severity: str
) -> Dict[str, Any]:
    """
    Evaluates business priority and corresponding SLA targets deterministically.
    Returns: dict with priority, matched_rule_id, target_response_hours, target_resolution_hours
    """
    if is_safety_issue or category_id == "CAT-01":
        return {
            "priority": "P1_CRITICAL",
            "matched_rule_id": "RUL-01",
            "target_response_hours": 1,
            "target_resolution_hours": 4
        }
    if is_vulnerable and sentiment_score < -0.40:
        return {
            "priority": "P1_CRITICAL",
            "matched_rule_id": "RUL-02",
            "target_response_hours": 1,
            "target_resolution_hours": 4
        }
    if is_vulnerable:
        return {
            "priority": "P2_HIGH",
            "matched_rule_id": "RUL-03",
            "target_response_hours": 4,
            "target_resolution_hours": 24
        }
    if order_amount >= 1000.00 and is_repeat_complaint:
        return {
            "priority": "P2_HIGH",
            "matched_rule_id": "RUL-04",
            "target_response_hours": 4,
            "target_resolution_hours": 24
        }
    if sentiment_score <= -0.70:
        return {
            "priority": "P2_HIGH",
            "matched_rule_id": "RUL-05",
            "target_response_hours": 4,
            "target_resolution_hours": 24
        }
    if severity == "HIGH":
        return {
            "priority": "P2_HIGH",
            "matched_rule_id": "RUL-07",
            "target_response_hours": 4,
            "target_resolution_hours": 24
        }
    if order_amount >= 500.00 or is_repeat_complaint or severity == "MEDIUM":
        return {
            "priority": "P3_MEDIUM",
            "matched_rule_id": "RUL-06",
            "target_response_hours": 12,
            "target_resolution_hours": 48
        }
    return {
        "priority": "P4_LOW",
        "matched_rule_id": "RUL-08",
        "target_response_hours": 24,
        "target_resolution_hours": 96
    }
