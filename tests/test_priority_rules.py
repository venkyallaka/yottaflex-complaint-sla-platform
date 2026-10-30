"""
Unit tests for deterministic priority rules matrix (RUL-01 through RUL-08).
"""
import pytest
from src.core.priority_matrix import calculate_priority

def test_rule_01_safety_critical():
    res = calculate_priority(
        is_safety_issue=True,
        category_id="CAT-01",
        is_vulnerable=False,
        sentiment_score=0.10,
        order_amount=50.0,
        is_repeat_complaint=False,
        severity="LOW"
    )
    assert res["priority"] == "P1_CRITICAL"
    assert res["matched_rule_id"] == "RUL-01"
    assert res["target_response_hours"] == 1
    assert res["target_resolution_hours"] == 4

def test_rule_02_vulnerable_customer_negative_sentiment():
    res = calculate_priority(
        is_safety_issue=False,
        category_id="CAT-02",
        is_vulnerable=True,
        sentiment_score=-0.65,
        order_amount=100.0,
        is_repeat_complaint=False,
        severity="MEDIUM"
    )
    assert res["priority"] == "P1_CRITICAL"
    assert res["matched_rule_id"] == "RUL-02"
    assert res["target_response_hours"] == 1

def test_rule_03_vulnerable_customer_standard():
    res = calculate_priority(
        is_safety_issue=False,
        category_id="CAT-02",
        is_vulnerable=True,
        sentiment_score=-0.20,
        order_amount=100.0,
        is_repeat_complaint=False,
        severity="MEDIUM"
    )
    assert res["priority"] == "P2_HIGH"
    assert res["matched_rule_id"] == "RUL-03"
    assert res["target_response_hours"] == 4

def test_rule_04_high_value_repeat_order():
    res = calculate_priority(
        is_safety_issue=False,
        category_id="CAT-03",
        is_vulnerable=False,
        sentiment_score=-0.10,
        order_amount=1250.00,
        is_repeat_complaint=True,
        severity="LOW"
    )
    assert res["priority"] == "P2_HIGH"
    assert res["matched_rule_id"] == "RUL-04"

def test_rule_05_severe_frustration_sentiment():
    res = calculate_priority(
        is_safety_issue=False,
        category_id="CAT-07",
        is_vulnerable=False,
        sentiment_score=-0.85,
        order_amount=80.00,
        is_repeat_complaint=False,
        severity="LOW"
    )
    assert res["priority"] == "P2_HIGH"
    assert res["matched_rule_id"] == "RUL-05"

def test_rule_08_standard_low_fallback():
    res = calculate_priority(
        is_safety_issue=False,
        category_id="CAT-08",
        is_vulnerable=False,
        sentiment_score=0.10,
        order_amount=45.00,
        is_repeat_complaint=False,
        severity="LOW"
    )
    assert res["priority"] == "P4_LOW"
    assert res["matched_rule_id"] == "RUL-08"
    assert res["target_response_hours"] == 24
    assert res["target_resolution_hours"] == 96

