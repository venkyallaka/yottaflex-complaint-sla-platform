"""
Automated tests verifying data dictionary compliance, foreign key integrity, and anomaly isolation.
"""
from scripts.validate_dataset import ValidationSuite

def test_validation_suite_executes_cleanly():
    suite = ValidationSuite()
    success = suite.run_all()
    assert success is True
    assert suite.passed_checks == suite.total_checks
    assert len(suite.detected_anomalies) == 6
