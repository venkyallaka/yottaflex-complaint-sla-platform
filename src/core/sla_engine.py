"""
SLA Clock Engine managing timers, pause/resume state machine, and breach tracking.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

def initialize_sla_clock(
    complaint_id: str,
    priority: str,
    created_at_iso: str
) -> Dict[str, Any]:
    """Creates a new active SLA clock record linked 1:1 with a complaint."""
    from src.generator.rules import SLA_TARGET_MAP
    
    target_info = SLA_TARGET_MAP.get(priority, {"response_hours": 24, "resolution_hours": 96})
    created_dt = datetime.fromisoformat(created_at_iso)
    
    target_resp_dt = created_dt + timedelta(hours=target_info["response_hours"])
    target_resol_dt = created_dt + timedelta(hours=target_info["resolution_hours"])
    
    return {
        "sla_id": f"SLA-{complaint_id}",
        "complaint_id": complaint_id,
        "target_response_time": target_resp_dt.isoformat(),
        "actual_response_time": None,
        "target_resolution_time": target_resol_dt.isoformat(),
        "actual_resolution_time": None,
        "clock_status": "RUNNING",
        "paused_duration_minutes": 0,
        "is_response_breached": False,
        "is_resolution_breached": False
    }

def record_first_response(
    sla_data: Dict[str, Any],
    response_dt_iso: str
) -> Dict[str, Any]:
    """Records the timestamp of the first outbound response and computes response breach."""
    resp_dt = datetime.fromisoformat(response_dt_iso)
    target_dt = datetime.fromisoformat(sla_data["target_response_time"])
    
    sla_data["actual_response_time"] = response_dt_iso
    sla_data["is_response_breached"] = resp_dt > target_dt
    return sla_data

def pause_clock(
    sla_data: Dict[str, Any],
    complaint_status: str
) -> Dict[str, Any]:
    """
    Transitions SLA clock to PAUSED state.
    Enforces the invariant: Complaint must be in PENDING_CUSTOMER state.
    """
    if complaint_status != "PENDING_CUSTOMER":
        raise ValueError("Invalid State: SLA clock can only be PAUSED when complaint is PENDING_CUSTOMER.")
        
    sla_data["clock_status"] = "PAUSED"
    return sla_data

def resume_clock(
    sla_data: Dict[str, Any],
    pause_start_dt_iso: str,
    resume_dt_iso: str
) -> Dict[str, Any]:
    """
    Resumes SLA clock, calculates paused duration, and pushes out resolution deadline.
    """
    p_start = datetime.fromisoformat(pause_start_dt_iso)
    p_end = datetime.fromisoformat(resume_dt_iso)
    
    delta_minutes = max(0, int((p_end - p_start).total_seconds() / 60))
    sla_data["paused_duration_minutes"] = sla_data.get("paused_duration_minutes", 0) + delta_minutes
    
    # Extend target resolution deadline by paused duration
    curr_target_dt = datetime.fromisoformat(sla_data["target_resolution_time"])
    extended_target_dt = curr_target_dt + timedelta(minutes=delta_minutes)
    sla_data["target_resolution_time"] = extended_target_dt.isoformat()
    sla_data["clock_status"] = "RUNNING"
    return sla_data

def complete_clock(
    sla_data: Dict[str, Any],
    resolution_dt_iso: str
) -> Dict[str, Any]:
    """Marks clock as COMPLETED and evaluates resolution SLA breach."""
    res_dt = datetime.fromisoformat(resolution_dt_iso)
    target_dt = datetime.fromisoformat(sla_data["target_resolution_time"])
    
    sla_data["actual_resolution_time"] = resolution_dt_iso
    sla_data["clock_status"] = "COMPLETED"
    sla_data["is_resolution_breached"] = res_dt > target_dt
    return sla_data
