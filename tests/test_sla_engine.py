"""
Unit tests for SLA Clock state machine, pause/resume, and breach detection.
"""
import pytest
from datetime import datetime, timedelta, timezone
from src.core.sla_engine import (
    initialize_sla_clock, record_first_response,
    pause_clock, resume_clock, complete_clock
)

def test_sla_clock_initialization():
    base_time = datetime(2026, 10, 24, 10, 0, 0, tzinfo=timezone.utc).isoformat()
    sla = initialize_sla_clock("CMP-2026-000001", "P1_CRITICAL", base_time)
    
    assert sla["sla_id"] == "SLA-CMP-2026-000001"
    assert sla["clock_status"] == "RUNNING"
    assert sla["paused_duration_minutes"] == 0
    assert sla["is_response_breached"] is False
    assert sla["is_resolution_breached"] is False
    
    # P1 has 1h response and 4h resolution
    target_resp = datetime.fromisoformat(sla["target_response_time"])
    target_resol = datetime.fromisoformat(sla["target_resolution_time"])
    created = datetime.fromisoformat(base_time)
    
    assert int((target_resp - created).total_seconds() / 3600) == 1
    assert int((target_resol - created).total_seconds() / 3600) == 4

def test_sla_response_recording():
    base_time = datetime(2026, 10, 24, 10, 0, 0, tzinfo=timezone.utc).isoformat()
    sla = initialize_sla_clock("CMP-2026-000002", "P2_HIGH", base_time) # 4h response
    
    # Compliant response within 2 hours
    resp_time_compliant = datetime(2026, 10, 24, 12, 0, 0, tzinfo=timezone.utc).isoformat()
    sla = record_first_response(sla, resp_time_compliant)
    assert sla["is_response_breached"] is False
    assert sla["actual_response_time"] == resp_time_compliant

    # Breached response after 5 hours
    sla2 = initialize_sla_clock("CMP-2026-000003", "P2_HIGH", base_time)
    resp_time_breached = datetime(2026, 10, 24, 15, 30, 0, tzinfo=timezone.utc).isoformat()
    sla2 = record_first_response(sla2, resp_time_breached)
    assert sla2["is_response_breached"] is True

def test_sla_pause_and_resume_extension():
    base_time = datetime(2026, 10, 24, 10, 0, 0, tzinfo=timezone.utc).isoformat()
    sla = initialize_sla_clock("CMP-2026-000004", "P3_MEDIUM", base_time) # 48h resolution
    initial_target_resol = datetime.fromisoformat(sla["target_resolution_time"])
    
    # Invariant: Pause requires PENDING_CUSTOMER
    with pytest.raises(ValueError):
        pause_clock(sla, "IN_INVESTIGATION")
        
    sla = pause_clock(sla, "PENDING_CUSTOMER")
    assert sla["clock_status"] == "PAUSED"
    
    # Resume after 180 minutes (3 hours)
    pause_start = datetime(2026, 10, 24, 12, 0, 0, tzinfo=timezone.utc).isoformat()
    pause_end = datetime(2026, 10, 24, 15, 0, 0, tzinfo=timezone.utc).isoformat()
    
    sla = resume_clock(sla, pause_start, pause_end)
    assert sla["clock_status"] == "RUNNING"
    assert sla["paused_duration_minutes"] == 180
    
    new_target_resol = datetime.fromisoformat(sla["target_resolution_time"])
    # Target resolution deadline extended by exactly 3 hours (180 minutes)
    assert int((new_target_resol - initial_target_resol).total_seconds() / 60) == 180

