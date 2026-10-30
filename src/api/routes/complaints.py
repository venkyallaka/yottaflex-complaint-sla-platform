"""
FastAPI route handlers for Complaint management, omnichannel messaging, and resolutions.
"""
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.database.session import get_db
from src.database.models import (
    Customer, Order, Product, Category, Complaint,
    ComplaintMessage, Assignment, SLAClock, Resolution,
    Survey, ComplaintEvent
)
from src.api.schemas import (
    ComplaintCreateRequest, MessageCreateRequest,
    PauseSLARequest, ResolutionProposeRequest,
    ResolutionApproveRequest, SurveySubmitRequest,
    ReopenRequest
)
from src.core.classifier import classify_text
from src.core.priority_matrix import calculate_priority
from src.core.routing import determine_team_and_agent
from src.core.sla_engine import (
    initialize_sla_clock, record_first_response,
    pause_clock, resume_clock, complete_clock
)
from src.core.event_store import emit_event

router = APIRouter(prefix="/api/v1/complaints", tags=["Complaints Workflow"])

@router.get("")
def list_complaints(
    status: Optional[str] = Query(None, description="Filter by complaint status"),
    priority: Optional[str] = Query(None, description="Filter by priority tier"),
    category_id: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by complaint ID or customer ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Lists complaints with optional filtering and pagination."""
    query = db.query(Complaint)
    if status:
        query = query.filter(Complaint.status == status)
    if priority:
        query = query.filter(Complaint.priority == priority)
    if category_id:
        query = query.filter(Complaint.category_id == category_id)
    if search:
        query = query.filter(
            (Complaint.complaint_id.contains(search)) |
            (Complaint.customer_id.contains(search))
        )
    
    total = query.count()
    records = query.order_by(desc(Complaint.created_at)).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "complaint_id": c.complaint_id,
                "customer_id": c.customer_id,
                "order_id": c.order_id,
                "category_id": c.category_id,
                "intake_channel": c.intake_channel,
                "severity": c.severity,
                "priority": c.priority,
                "status": c.status,
                "sentiment_score": c.sentiment_score,
                "is_safety_issue": c.is_safety_issue,
                "is_repeat_complaint": c.is_repeat_complaint,
                "created_at": c.created_at,
                "updated_at": c.updated_at
            }
            for c in records
        ]
    }

@router.post("", status_code=201)
def create_complaint(
    payload: ComplaintCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Ingests and processes a new complaint:
    1. Validates Customer (and Order if given)
    2. Runs Text Classification & Sentiment Scoring
    3. Evaluates Dynamic Priority Matrix
    4. Routes & Assigns to Specialized Team / Agent
    5. Starts SLA Clock
    6. Appends Audit Events
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # 1. Customer validation
    customer = db.query(Customer).filter(Customer.customer_id == payload.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer '{payload.customer_id}' not found.")
        
    order_amount = 0.0
    if payload.order_id:
        order = db.query(Order).filter(Order.order_id == payload.order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail=f"Order '{payload.order_id}' not found.")
        order_amount = order.order_amount
        
    # 2. Classification
    classification = classify_text(payload.message_body)
    category_id = payload.category_id or classification["category_id"]
    is_safety_issue = classification["is_safety_issue"]
    sentiment_score = classification["sentiment_score"]
    severity = classification["severity"]
    
    # Check repeat issue
    recent_complaints = db.query(Complaint).filter(
        Complaint.customer_id == payload.customer_id
    ).order_by(desc(Complaint.created_at)).all()
    
    is_repeat = False
    parent_id = None
    if recent_complaints:
        last_c = recent_complaints[0]
        # within 30 days
        dt_last = datetime.fromisoformat(last_c.created_at)
        if (datetime.now(timezone.utc) - dt_last.replace(tzinfo=timezone.utc)).days <= 30:
            is_repeat = True
            parent_id = last_c.complaint_id
            
    # 3. Priority evaluation
    prio_result = calculate_priority(
        is_safety_issue=is_safety_issue,
        category_id=category_id,
        is_vulnerable=customer.is_vulnerable,
        sentiment_score=sentiment_score,
        order_amount=order_amount,
        is_repeat_complaint=is_repeat,
        severity=severity
    )
    priority = prio_result["priority"]
    
    # Generate ID
    count = db.query(Complaint).count() + 1
    complaint_id = f"CMP-2026-{count:06d}"
    
    # 4. Routing
    routing_info = determine_team_and_agent(category_id=category_id, priority=priority)
    
    # Persist Complaint
    new_complaint = Complaint(
        complaint_id=complaint_id,
        customer_id=customer.customer_id,
        order_id=payload.order_id,
        category_id=category_id,
        intake_channel=payload.intake_channel,
        severity=severity,
        priority=priority,
        status="ASSIGNED",
        sentiment_score=sentiment_score,
        is_safety_issue=is_safety_issue,
        is_repeat_complaint=is_repeat,
        parent_complaint_id=parent_id,
        created_at=now_iso,
        updated_at=now_iso
    )
    db.add(new_complaint)
    
    # Persist Initial Message
    initial_msg = ComplaintMessage(
        message_id=f"MSG-{complaint_id}-001",
        complaint_id=complaint_id,
        sender_type="CUSTOMER",
        sender_id=customer.customer_id,
        channel=payload.intake_channel,
        message_body=payload.message_body,
        sentiment_score=sentiment_score,
        timestamp=now_iso
    )
    db.add(initial_msg)
    
    # Persist Assignment
    assignment = Assignment(
        assignment_id=f"ASN-{complaint_id}-001",
        complaint_id=complaint_id,
        team_name=routing_info["team_name"],
        agent_id=routing_info["agent_id"],
        assigned_by="SYS_AUTO_ROUTER",
        assigned_at=now_iso
    )
    db.add(assignment)
    
    # Persist SLA Clock
    sla_data = initialize_sla_clock(
        complaint_id=complaint_id,
        priority=priority,
        created_at_iso=now_iso
    )
    sla_clock = SLAClock(**sla_data)
    db.add(sla_clock)
    db.commit()
    
    # Audit events
    emit_event(
        db, complaint_id, "CREATED", "BUSINESS_REQUESTER", customer.customer_id,
        {"category_id": category_id, "channel": payload.intake_channel, "severity": severity}
    )
    emit_event(
        db, complaint_id, "ASSIGNED", "SYSTEM_ADMIN", "SYS_AUTO_ROUTER",
        {"team": routing_info["team_name"], "agent_id": routing_info["agent_id"], "priority": priority}
    )
    
    return {
        "complaint_id": complaint_id,
        "priority": priority,
        "category_id": category_id,
        "assigned_team": routing_info["team_name"],
        "assigned_agent": routing_info["agent_id"],
        "target_response_time": sla_data["target_response_time"],
        "target_resolution_time": sla_data["target_resolution_time"],
        "status": "ASSIGNED"
    }

@router.get("/{complaint_id}")
def get_complaint_detail(
    complaint_id: str,
    db: Session = Depends(get_db)
):
    """Retrieves complete 360-degree timeline and operational state for a complaint."""
    c = db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail=f"Complaint '{complaint_id}' not found.")
        
    return {
        "complaint": {
            "complaint_id": c.complaint_id,
            "customer_id": c.customer_id,
            "order_id": c.order_id,
            "category_id": c.category_id,
            "intake_channel": c.intake_channel,
            "severity": c.severity,
            "priority": c.priority,
            "status": c.status,
            "sentiment_score": c.sentiment_score,
            "is_safety_issue": c.is_safety_issue,
            "is_repeat_complaint": c.is_repeat_complaint,
            "parent_complaint_id": c.parent_complaint_id,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "closed_at": c.closed_at
        },
        "customer": {
            "name": f"{c.customer.first_name} {c.customer.last_name}" if c.customer else "Unknown",
            "tier": c.customer.customer_tier if c.customer else "STANDARD",
            "is_vulnerable": c.customer.is_vulnerable if c.customer else False
        },
        "sla_clock": {
            "clock_status": c.sla_clock.clock_status if c.sla_clock else "NONE",
            "target_response_time": c.sla_clock.target_response_time if c.sla_clock else None,
            "actual_response_time": c.sla_clock.actual_response_time if c.sla_clock else None,
            "target_resolution_time": c.sla_clock.target_resolution_time if c.sla_clock else None,
            "actual_resolution_time": c.sla_clock.actual_resolution_time if c.sla_clock else None,
            "paused_duration_minutes": c.sla_clock.paused_duration_minutes if c.sla_clock else 0,
            "is_response_breached": c.sla_clock.is_response_breached if c.sla_clock else False,
            "is_resolution_breached": c.sla_clock.is_resolution_breached if c.sla_clock else False
        },
        "resolution": {
            "resolution_id": c.resolution.resolution_id if c.resolution else None,
            "resolution_type": c.resolution.resolution_type if c.resolution else None,
            "root_cause": c.resolution.root_cause if c.resolution else None,
            "compensation_amount": c.resolution.compensation_amount if c.resolution else 0.0,
            "requires_approval": c.resolution.requires_approval if c.resolution else False,
            "approval_status": c.resolution.approval_status if c.resolution else "NONE",
            "approver_id": c.resolution.approver_id if c.resolution else None,
            "resolved_at": c.resolution.resolved_at if c.resolution else None
        } if c.resolution else None,
        "survey": {
            "survey_id": c.survey.survey_id if c.survey else None,
            "csat_score": c.survey.csat_score if c.survey else None,
            "nps_score": c.survey.nps_score if c.survey else None,
            "effort_score": c.survey.effort_score if c.survey else None,
            "feedback_comments": c.survey.feedback_comments if c.survey else None,
            "submitted_at": c.survey.submitted_at if c.survey else None
        } if c.survey else None,
        "messages": [
            {
                "message_id": m.message_id,
                "sender_type": m.sender_type,
                "sender_id": m.sender_id,
                "channel": m.channel,
                "message_body": m.message_body,
                "sentiment_score": m.sentiment_score,
                "timestamp": m.timestamp
            }
            for m in sorted(c.messages, key=lambda x: x.timestamp)
        ],
        "events": [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "actor_role": e.actor_role,
                "actor_id": e.actor_id,
                "payload": e.event_payload,
                "created_at": e.created_at
            }
            for e in sorted(c.events, key=lambda x: x.created_at)
        ]
    }

@router.post("/{complaint_id}/messages")
def append_message(
    complaint_id: str,
    payload: MessageCreateRequest,
    db: Session = Depends(get_db)
):
    """Appends an omnichannel message and updates response metrics."""
    c = db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found.")
        
    now_iso = datetime.now(timezone.utc).isoformat()
    seq = len(c.messages) + 1
    msg_id = f"MSG-{complaint_id}-{seq:03d}"
    
    # Calculate simple sentiment
    sentiment = 0.35 if payload.sender_type == "AGENT" else -0.20
    
    new_msg = ComplaintMessage(
        message_id=msg_id,
        complaint_id=complaint_id,
        sender_type=payload.sender_type,
        sender_id=payload.sender_id,
        channel=payload.channel,
        message_body=payload.message_body,
        sentiment_score=sentiment,
        timestamp=now_iso
    )
    db.add(new_msg)
    
    # If agent responds and first response time is empty, record response time
    if payload.sender_type == "AGENT" and c.sla_clock and c.sla_clock.actual_response_time is None:
        c.sla_clock.actual_response_time = now_iso
        target_resp = datetime.fromisoformat(c.sla_clock.target_response_time)
        c.sla_clock.is_response_breached = datetime.now(timezone.utc) > target_resp.replace(tzinfo=timezone.utc)
        if c.status == "ASSIGNED":
            c.status = "IN_INVESTIGATION"
            
    # If customer responds while pending, auto-resume
    if payload.sender_type == "CUSTOMER" and c.status == "PENDING_CUSTOMER":
        c.status = "IN_INVESTIGATION"
        if c.sla_clock and c.sla_clock.clock_status == "PAUSED":
            c.sla_clock.clock_status = "RUNNING"
            emit_event(db, complaint_id, "SLA_RESUMED", "SYSTEM_ADMIN", "SYS_AUTO_RESUME", {"reason": "Customer responded"})

    c.updated_at = now_iso
    db.commit()
    
    emit_event(
        db, complaint_id, "MESSAGE_SENT", payload.sender_type, payload.sender_id,
        {"message_id": msg_id, "channel": payload.channel}
    )
    return {"message_id": msg_id, "status": "Message appended successfully"}

@router.post("/{complaint_id}/sla/pause")
def pause_sla(
    complaint_id: str,
    payload: PauseSLARequest,
    db: Session = Depends(get_db)
):
    """Transitions complaint to PENDING_CUSTOMER and pauses the SLA clock."""
    c = db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
    if not c or not c.sla_clock:
        raise HTTPException(status_code=404, detail="Complaint or SLA clock not found.")
        
    c.status = "PENDING_CUSTOMER"
    c.sla_clock.clock_status = "PAUSED"
    c.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    
    emit_event(
        db, complaint_id, "SLA_PAUSED", "OPERATIONS_ANALYST", "AGT-PAUSE",
        {"reason": payload.reason}
    )
    return {"status": "PAUSED", "complaint_status": "PENDING_CUSTOMER"}

@router.post("/{complaint_id}/sla/resume")
def resume_sla(
    complaint_id: str,
    db: Session = Depends(get_db)
):
    """Resumes the SLA clock and recalculates resolution deadline."""
    c = db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
    if not c or not c.sla_clock:
        raise HTTPException(status_code=404, detail="Complaint or SLA clock not found.")
        
    if c.sla_clock.clock_status != "PAUSED":
        raise HTTPException(status_code=400, detail="SLA clock is not currently paused.")
        
    c.status = "IN_INVESTIGATION"
    c.sla_clock.clock_status = "RUNNING"
    c.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    
    emit_event(
        db, complaint_id, "SLA_RESUMED", "OPERATIONS_ANALYST", "AGT-RESUME",
        {"new_status": "IN_INVESTIGATION"}
    )
    return {"status": "RUNNING", "complaint_status": "IN_INVESTIGATION"}

@router.post("/{complaint_id}/resolution")
def propose_resolution(
    complaint_id: str,
    payload: ResolutionProposeRequest,
    db: Session = Depends(get_db)
):
    """Proposes a resolution and checks whether Approver sign-off is mandatory."""
    c = db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found.")
        
    now_iso = datetime.now(timezone.utc).isoformat()
    
    requires_approval = (payload.compensation_amount > 250.00) or c.is_safety_issue
    approval_status = "PENDING_REVIEW" if requires_approval else "NOT_REQUIRED"
    
    res = db.query(Resolution).filter(Resolution.complaint_id == complaint_id).first()
    if not res:
        res = Resolution(
            resolution_id=f"RES-{complaint_id}",
            complaint_id=complaint_id,
            resolution_type=payload.resolution_type,
            root_cause=payload.root_cause,
            compensation_amount=payload.compensation_amount,
            requires_approval=requires_approval,
            approval_status=approval_status,
            resolved_at=now_iso
        )
        db.add(res)
    else:
        res.resolution_type = payload.resolution_type
        res.root_cause = payload.root_cause
        res.compensation_amount = payload.compensation_amount
        res.requires_approval = requires_approval
        res.approval_status = approval_status
        res.resolved_at = now_iso
        
    if requires_approval:
        c.status = "RESOLUTION_PENDING"
    else:
        c.status = "RESOLVED"
        if c.sla_clock:
            c.sla_clock.clock_status = "COMPLETED"
            c.sla_clock.actual_resolution_time = now_iso
            
    c.updated_at = now_iso
    db.commit()
    
    emit_event(
        db, complaint_id, "RESOLUTION_PROPOSED", "PROCESS_OWNER", "AGENT_RESOLUTION",
        {"resolution_type": payload.resolution_type, "requires_approval": requires_approval}
    )
    return {
        "resolution_id": res.resolution_id,
        "requires_approval": requires_approval,
        "approval_status": approval_status,
        "complaint_status": c.status
    }

@router.post("/{complaint_id}/resolution/approve")
def approve_resolution(
    complaint_id: str,
    payload: ResolutionApproveRequest,
    db: Session = Depends(get_db)
):
    """Approver sign-off for financial payouts > $250 or safety-critical resolutions."""
    c = db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
    if not c or not c.resolution:
        raise HTTPException(status_code=404, detail="Complaint or proposed resolution not found.")
        
    now_iso = datetime.now(timezone.utc).isoformat()
    if payload.approved:
        c.resolution.approval_status = "APPROVED"
        c.resolution.approver_id = payload.approver_id
        c.status = "RESOLVED"
        if c.sla_clock:
            c.sla_clock.clock_status = "COMPLETED"
            c.sla_clock.actual_resolution_time = now_iso
    else:
        c.resolution.approval_status = "REJECTED"
        c.resolution.approver_id = payload.approver_id
        c.status = "IN_INVESTIGATION"
        
    c.updated_at = now_iso
    db.commit()
    
    emit_event(
        db, complaint_id, "RESOLUTION_APPROVED" if payload.approved else "RESOLUTION_REJECTED",
        "APPROVER", payload.approver_id,
        {"approved": payload.approved, "notes": payload.notes}
    )
    return {"approval_status": c.resolution.approval_status, "complaint_status": c.status}

@router.post("/{complaint_id}/reopen")
def reopen_complaint(
    complaint_id: str,
    payload: ReopenRequest,
    db: Session = Depends(get_db)
):
    """Reopens a resolved or closed complaint, preserving all prior history."""
    c = db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found.")
        
    if c.status not in ["RESOLVED", "CLOSED"]:
        raise HTTPException(status_code=400, detail="Only RESOLVED or CLOSED complaints can be reopened.")
        
    now_iso = datetime.now(timezone.utc).isoformat()
    c.status = "REOPENED"
    c.updated_at = now_iso
    if c.sla_clock:
        c.sla_clock.clock_status = "RUNNING"
        
    db.commit()
    
    emit_event(
        db, complaint_id, "REOPENED", "BUSINESS_REQUESTER", c.customer_id,
        {"reason": payload.reason}
    )
    return {"complaint_id": complaint_id, "status": "REOPENED"}

@router.post("/{complaint_id}/survey")
def submit_survey(
    complaint_id: str,
    payload: SurveySubmitRequest,
    db: Session = Depends(get_db)
):
    """Records post-resolution customer experience survey."""
    c = db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found.")
        
    if c.status not in ["RESOLVED", "CLOSED"]:
        raise HTTPException(
            status_code=400,
            detail="Lifecycle violation: Surveys can only be submitted after complaint is RESOLVED or CLOSED."
        )
        
    now_iso = datetime.now(timezone.utc).isoformat()
    existing_srv = db.query(Survey).filter(Survey.complaint_id == complaint_id).first()
    if existing_srv:
        raise HTTPException(status_code=400, detail="Survey already submitted for this complaint.")
        
    survey = Survey(
        survey_id=f"SRV-{complaint_id}",
        complaint_id=complaint_id,
        csat_score=payload.csat_score,
        nps_score=payload.nps_score,
        effort_score=payload.effort_score,
        feedback_comments=payload.feedback_comments,
        submitted_at=now_iso
    )
    db.add(survey)
    
    # Auto-close complaint upon survey completion
    c.status = "CLOSED"
    c.closed_at = now_iso
    c.updated_at = now_iso
    db.commit()
    
    emit_event(
        db, complaint_id, "CLOSED", "BUSINESS_REQUESTER", c.customer_id,
        {"survey_id": survey.survey_id, "csat": payload.csat_score}
    )
    return {"survey_id": survey.survey_id, "status": "Survey submitted; complaint closed."}

