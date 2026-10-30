"""
Append-only Audit Event Store for end-to-end traceability.
Captures all lifecycle mutations, role decisions, and state machine changes.
"""
import json
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.database.models import ComplaintEvent

def emit_event(
    db: Session,
    complaint_id: str,
    event_type: str,
    actor_role: str,
    actor_id: str,
    payload: dict,
    timestamp_iso: str = None
) -> ComplaintEvent:
    """Creates and persists an immutable audit event."""
    if timestamp_iso is None:
        timestamp_iso = datetime.now(timezone.utc).isoformat()
        
    # Generate sequential or UUID-based event ID
    event_id = f"EVT-2026-{uuid.uuid4().hex[:7]}"
    
    event = ComplaintEvent(
        event_id=event_id,
        complaint_id=complaint_id,
        event_type=event_type,
        actor_role=actor_role,
        actor_id=actor_id,
        event_payload=json.dumps(payload),
        created_at=timestamp_iso
    )
    db.add(event)
    db.commit()
    return event

