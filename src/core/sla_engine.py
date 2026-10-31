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
        "cycle": 1,
        "target_response_time": target_resp_dt.isoformat(),
        "actual_response_time": None,
        "target_resolution_time": target_resol_dt.isoformat(),
        "actual_resolution_time": None,
        "clock_status": "RUNNING",
        "paused_at": None,
        "paused_duration_minutes": 0,
        "is_response_breached": False,
        "is_resolution_breached": False,
        "is_current": True
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
    complaint_status: str,
    pause_dt_iso: str = None
) -> Dict[str, Any]:
    """
    Transitions SLA clock to PAUSED state and records pause timestamp.
    Enforces the invariant: Complaint must be in PENDING_CUSTOMER state.
    """
    if complaint_status != "PENDING_CUSTOMER":
        raise ValueError("Invalid State: SLA clock can only be PAUSED when complaint is PENDING_CUSTOMER.")
        
    sla_data["clock_status"] = "PAUSED"
    sla_data["paused_at"] = pause_dt_iso or datetime.now(timezone.utc).isoformat()
    return sla_data

def resume_clock(
    sla_data: Dict[str, Any],
    pause_start_dt_iso: str = None,
    resume_dt_iso: str = None
) -> Dict[str, Any]:
    """
    Resumes SLA clock, calculates paused duration, and pushes out resolution deadline.
    """
    now_iso = resume_dt_iso or datetime.now(timezone.utc).isoformat()
    p_start_str = pause_start_dt_iso or sla_data.get("paused_at")
    
    if p_start_str:
        p_start = datetime.fromisoformat(p_start_str)
        p_end = datetime.fromisoformat(now_iso)
        delta_minutes = max(0, int((p_end - p_start).total_seconds() / 60))
        sla_data["paused_duration_minutes"] = (sla_data.get("paused_duration_minutes") or 0) + delta_minutes
        
        # Extend target resolution deadline by paused duration
        curr_target_dt = datetime.fromisoformat(sla_data["target_resolution_time"])
        extended_target_dt = curr_target_dt + timedelta(minutes=delta_minutes)
        sla_data["target_resolution_time"] = extended_target_dt.isoformat()
        
    sla_data["paused_at"] = None
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

def create_reopened_sla_clock(
    complaint_id: str,
    priority: str,
    cycle: int,
    reopen_dt_iso: str
) -> Dict[str, Any]:
    """
    Creates an independent SLA clock record for a reopened lifecycle investigation cycle.
    Resets response targets and resolution deadlines for the new cycle, maintaining complete cycle history.
    """
    from src.generator.rules import SLA_TARGET_MAP
    
    target_info = SLA_TARGET_MAP.get(priority, {"response_hours": 24, "resolution_hours": 96})
    reopen_dt = datetime.fromisoformat(reopen_dt_iso)
    
    target_resp_dt = reopen_dt + timedelta(hours=target_info["response_hours"])
    target_resol_dt = reopen_dt + timedelta(hours=target_info["resolution_hours"])
    
    return {
        "sla_id": f"SLA-{complaint_id}-c{cycle:02d}",
        "complaint_id": complaint_id,
        "cycle": cycle,
        "target_response_time": target_resp_dt.isoformat(),
        "actual_response_time": None,
        "target_resolution_time": target_resol_dt.isoformat(),
        "actual_resolution_time": None,
        "clock_status": "RUNNING",
        "paused_at": None,
        "paused_duration_minutes": 0,
        "is_response_breached": False,
        "is_resolution_breached": False,
        "is_current": True
    }

def reset_clock_for_reopen(
    sla_data: Dict[str, Any],
    priority: str,
    reopen_dt_iso: str = None
) -> Dict[str, Any]:
    """
    Restarts SLA clock for a reopened investigation cycle.
    Clears actual resolution time, resets status to RUNNING,
    and establishes a new target resolution deadline based on priority.
    """
    from src.generator.rules import SLA_TARGET_MAP
    
    reopen_dt = datetime.fromisoformat(reopen_dt_iso or datetime.now(timezone.utc).isoformat())
    target_info = SLA_TARGET_MAP.get(priority, {"response_hours": 24, "resolution_hours": 96})
    new_target_dt = reopen_dt + timedelta(hours=target_info["resolution_hours"])
    
    sla_data["actual_resolution_time"] = None
    sla_data["target_resolution_time"] = new_target_dt.isoformat()
    sla_data["clock_status"] = "RUNNING"
    sla_data["paused_at"] = None
    sla_data["paused_duration_minutes"] = 0
    sla_data["is_resolution_breached"] = False
    return sla_data


