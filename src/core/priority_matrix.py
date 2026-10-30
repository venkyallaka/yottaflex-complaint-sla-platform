"""
Priority Matrix Engine implementing deterministic priority calculation.
"""
from typing import Dict, Any
from src.generator.rules import evaluate_priority, SLA_TARGET_MAP

def calculate_priority(
    is_safety_issue: bool,
    category_id: str,
    is_vulnerable: bool,
    sentiment_score: float,
    order_amount: float,
    is_repeat_complaint: bool,
    severity: str
) -> Dict[str, Any]:
    """
    Evaluates priority tier and associated SLA clock thresholds.
    """
    return evaluate_priority(
        is_safety_issue=is_safety_issue,
        category_id=category_id,
        is_vulnerable=is_vulnerable,
        sentiment_score=sentiment_score,
        order_amount=order_amount,
        is_repeat_complaint=is_repeat_complaint,
        severity=severity
    )
