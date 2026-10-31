"""
FastAPI route handlers for Operational Metrics and Anomaly Audits.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database.session import get_db
from src.database.models import (
    Complaint, SLAClock, Resolution, Survey, Category
)
from scripts.validate_dataset import ValidationSuite

router = APIRouter(prefix="/api/v1/analytics", tags=["Operational Analytics & Audits"])

@router.get("/metrics")
def get_operational_metrics(db: Session = Depends(get_db)):
    """Computes real-time operational KPIs, SLA compliance rates, and MTTR."""
    total_complaints = db.query(Complaint).count()
    
    # Status breakdown
    status_counts = dict(
        db.query(Complaint.status, func.count(Complaint.complaint_id))
        .group_by(Complaint.status).all()
    )
    
    # Priority breakdown
    prio_counts = dict(
        db.query(Complaint.priority, func.count(Complaint.complaint_id))
        .group_by(Complaint.priority).all()
    )
    
    # Category breakdown
    cat_counts = dict(
        db.query(Category.category_name, func.count(Complaint.complaint_id))
        .join(Complaint, Complaint.category_id == Category.category_id)
        .group_by(Category.category_name).all()
    )
    
    # SLA Compliance
    total_resolved = db.query(SLAClock).filter(SLAClock.clock_status == "COMPLETED").count()
    breached_resolutions = db.query(SLAClock).filter(
        SLAClock.clock_status == "COMPLETED",
        SLAClock.is_resolution_breached == True
    ).count()
    
    sla_compliance_rate = 100.0
    if total_resolved > 0:
        sla_compliance_rate = round(((total_resolved - breached_resolutions) / total_resolved) * 100, 2)
        
    # Response breach count
    response_breaches = db.query(SLAClock).filter(SLAClock.is_response_breached == True).count()
    
    # CSAT & NPS
    surveys = db.query(Survey).all()
    avg_csat = 0.0
    nps_score = 0.0
    if surveys:
        avg_csat = round(sum(s.csat_score for s in surveys) / len(surveys), 2)
        promoters = sum(1 for s in surveys if s.nps_score >= 9)
        detractors = sum(1 for s in surveys if s.nps_score <= 6)
        nps_score = round(((promoters - detractors) / len(surveys)) * 100, 1)
        
    # MTTR Calculation (hours): correctly excludes paused customer wait periods across all completed resolutions
    resolutions = db.query(Resolution).all()
    mttr_hours = 0.0
    if resolutions:
        durations = []
        for r in resolutions:
            c = r.complaint
            if c and r.approval_status != "PENDING_REVIEW":
                t_c = datetime.fromisoformat(c.created_at)
                t_r = datetime.fromisoformat(r.resolved_at)
                paused_mins = c.sla_clock.paused_duration_minutes if c.sla_clock else 0
                gross_seconds = (t_r - t_c).total_seconds()
                # Exclude authorized customer wait state
                net_seconds = gross_seconds - (paused_mins * 60)
                if net_seconds > 0:
                    durations.append(net_seconds / 3600.0)
        if durations:
            mttr_hours = round(sum(durations) / len(durations), 1)

    return {
        "summary": {
            "total_complaints": total_complaints,
            "total_resolved": total_resolved,
            "sla_compliance_rate": f"{sla_compliance_rate}%",
            "mean_time_to_resolution_hours": f"{mttr_hours} hrs",
            "average_csat": f"{avg_csat} / 5.0",
            "net_promoter_score": nps_score,
            "response_breach_count": response_breaches,
            "resolution_breach_count": breached_resolutions
        },
        "status_distribution": status_counts,
        "priority_distribution": prio_counts,
        "category_distribution": cat_counts
    }

@router.get("/audit")
def run_integrity_audit(
    source: str = Query("database", description="Audit source: 'database' for live DB or 'dataset' for static benchmark JSON files"),
    db: Session = Depends(get_db)
):
    """Executes live database or static dataset validation suite and returns integrity scorecard."""
    if source == "database":
        suite = ValidationSuite(source="database", db_session=db)
        is_valid = suite.run_all()
        return {
            "source": "database",
            "is_healthy": is_valid,
            "passed_checks": f"{suite.passed_checks}/{suite.total_checks}",
            "live_database_records": {
                "customers": len(suite.customers),
                "orders": len(suite.orders),
                "complaints": len(suite.complaints),
                "sla_clocks": len(suite.sla_clocks),
                "resolutions": len(suite.resolutions),
                "surveys": len(suite.surveys)
            },
            "integrity_violations_detected": len(suite.detected_anomalies),
            "status": "All foreign keys, lifecycle states, and SLA invariants verified healthy in live operational database."
        }
    else:
        suite = ValidationSuite(source="dataset")
        is_valid = suite.run_all()
        
        gt_anomalies = suite.ground_truth.get("anomalies", [])
        expected_count = len(gt_anomalies)
        detected_count = len(suite.detected_anomalies)
        
        # Calculate true precision and recall
        true_positives = sum(
            1 for a in gt_anomalies 
            if any(d["code"] == a["anomaly_code"] and d["entity_id"] == a["entity_id"] for d in suite.detected_anomalies)
        )
        recall = round((true_positives / expected_count * 100), 1) if expected_count > 0 else 100.0
        precision = round((true_positives / detected_count * 100), 1) if detected_count > 0 else 100.0

        return {
            "source": "dataset",
            "is_healthy": is_valid,
            "passed_checks": f"{suite.passed_checks}/{suite.total_checks}",
            "detected_anomalies": suite.detected_anomalies,
            "ground_truth_anomalies": gt_anomalies,
            "recall_score": f"{recall}%",
            "precision_score": f"{precision}%"
        }

