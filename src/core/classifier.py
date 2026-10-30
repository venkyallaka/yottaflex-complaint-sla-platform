"""
Complaint Text Classification & Sentiment Scoring Engine.
Extracts category, safety hazard signals, and sentiment polarity.
"""
import re
from typing import Dict, Any, Tuple

SAFETY_KEYWORDS = {
    "smoke", "smoking", "fire", "spark", "sparks", "burning", "burn", "melt", "melting",
    "exploded", "explosion", "shock", "electric shock", "hazard", "dangerous", "injury",
    "injured", "hospital", "poison", "toxic", "leaking acid", "choking"
}

CATEGORY_KEYWORD_MAP = {
    "CAT-01": ["smoke", "fire", "spark", "burning", "melt", "hazard", "shock", "explosion", "safety"],
    "CAT-02": ["broken", "damaged", "shattered", "crack", "cracked", "defective", "dead pixels", "scratch"],
    "CAT-03": ["late", "delay", "missing delivery", "never arrived", "lost package", "tracking", "courier", "porch"],
    "CAT-04": ["double charge", "charged twice", "billing", "overcharge", "tax", "fee", "unauthorized charge"],
    "CAT-05": ["refund", "return", "restocking fee", "money back", "return label", "warehouse refund"],
    "CAT-06": ["password", "hacked", "unauthorized login", "2fa", "two-factor", "locked out", "security alert"],
    "CAT-07": ["rude", "unprofessional", "dismissive", "hung up", "worst customer service", "bad attitude"],
    "CAT-08": ["missing part", "missing parts", "screws", "adapter", "missing accessories", "manual"],
    "CAT-09": ["misleading", "wrong color", "fake", "counterfeit", "wrong size", "different than picture"],
    "CAT-10": ["app crash", "firmware", "bluetooth", "glitch", "bricked", "software error", "wifi disconnect"]
}

NEGATIVE_WORDS = {"terrible", "awful", "horrible", "broken", "unusable", "furious", "unacceptable", "disaster", "garbage", "trash", "scam", "worst"}
POSITIVE_WORDS = {"thanks", "great", "excellent", "helpful", "good", "appreciate", "quick", "resolved"}

def classify_text(text: str) -> Dict[str, Any]:
    """
    Classifies customer message body into category, severity, safety flag, and sentiment score.
    """
    text_lower = text.lower()
    
    # Check safety signals
    words = set(re.findall(r"\b\w+\b", text_lower))
    is_safety_issue = bool(words.intersection(SAFETY_KEYWORDS))
    
    # Match category scores
    best_cat = "CAT-02"
    best_score = 0
    if is_safety_issue:
        best_cat = "CAT-01"
    else:
        for cat_id, kws in CATEGORY_KEYWORD_MAP.items():
            matches = sum(1 for kw in kws if kw in text_lower)
            if matches > best_score:
                best_score = matches
                best_cat = cat_id
                
    # Sentiment scoring heuristic (-1.0 to +1.0)
    neg_count = sum(1 for w in NEGATIVE_WORDS if w in text_lower)
    pos_count = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    
    if is_safety_issue:
        sentiment = -0.85
        severity = "CRITICAL"
    else:
        sentiment = round(max(-1.0, min(1.0, 0.0 - (neg_count * 0.25) + (pos_count * 0.25) - 0.20)), 2)
        if sentiment <= -0.60:
            severity = "HIGH"
        elif sentiment <= -0.20:
            severity = "MEDIUM"
        else:
            severity = "LOW"
            
    return {
        "category_id": best_cat,
        "is_safety_issue": is_safety_issue,
        "severity": severity,
        "sentiment_score": sentiment
    }

