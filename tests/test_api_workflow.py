"""
Integration tests for FastAPI end-to-end complaint lifecycle endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.database.session import init_db_and_seed

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db_and_seed()

client = TestClient(app)

def test_api_health_check():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "HEALTHY"

def test_end_to_end_complaint_lifecycle():
    # 1. Ingest complaint
    create_payload = {
        "customer_id": "CUS-000001",
        "intake_channel": "WEB_PORTAL",
        "message_body": "The lithium battery started smoking and overheating. Severe hazard!"
    }
    res = client.post("/api/v1/complaints", json=create_payload)
    assert res.status_code == 201
    data = res.json()
    complaint_id = data["complaint_id"]
    assert complaint_id.startswith("CMP-2026-")
    assert data["priority"] == "P1_CRITICAL"
    assert data["assigned_team"] == "Safety & Regulatory Escalations"

    # 2. Inspect details
    res = client.get(f"/api/v1/complaints/{complaint_id}")
    assert res.status_code == 200
    detail = res.json()
    assert detail["complaint"]["status"] == "ASSIGNED"
    assert detail["sla_clock"]["clock_status"] == "RUNNING"
    assert len(detail["messages"]) >= 1

    # 3. Agent response message
    msg_payload = {
        "sender_type": "AGENT",
        "sender_id": "AGT-0015",
        "channel": "PORTAL_NOTE",
        "message_body": "Safety board has received your incident report and quarantined product stock."
    }
    res = client.post(f"/api/v1/complaints/{complaint_id}/messages", json=msg_payload)
    assert res.status_code == 200

    # 4. Pause SLA clock
    res = client.post(f"/api/v1/complaints/{complaint_id}/sla/pause", json={"reason": "Waiting on safety team on-site inspection"})
    assert res.status_code == 200
    assert res.json()["status"] == "PAUSED"
    assert res.json()["complaint_status"] == "PENDING_CUSTOMER"

    # 5. Resume SLA clock
    res = client.post(f"/api/v1/complaints/{complaint_id}/sla/resume")
    assert res.status_code == 200
    assert res.json()["status"] == "RUNNING"
    assert res.json()["complaint_status"] == "IN_INVESTIGATION"

    # 6. Propose resolution requiring approval (> $250 or safety)
    res_payload = {
        "resolution_type": "FULL_REFUND",
        "root_cause": "DEFECTIVE_PRODUCT",
        "compensation_amount": 350.00
    }
    res = client.post(f"/api/v1/complaints/{complaint_id}/resolution", json=res_payload)
    assert res.status_code == 200
    assert res.json()["requires_approval"] is True
    assert res.json()["approval_status"] == "PENDING_REVIEW"
    assert res.json()["complaint_status"] == "RESOLUTION_PENDING"

    # 7. Approver signs off
    appr_payload = {
        "approver_id": "APP-0001",
        "approved": True,
        "notes": "Approved safety recall compensation payout"
    }
    res = client.post(f"/api/v1/complaints/{complaint_id}/resolution/approve", json=appr_payload)
    assert res.status_code == 200
    assert res.json()["approval_status"] == "APPROVED"
    assert res.json()["complaint_status"] == "RESOLVED"

    # 8. Post-resolution CSAT survey
    survey_payload = {
        "csat_score": 5,
        "nps_score": 10,
        "effort_score": 5,
        "feedback_comments": "Handled with extreme care and urgency."
    }
    res = client.post(f"/api/v1/complaints/{complaint_id}/survey", json=survey_payload)
    assert res.status_code == 200
    assert res.json()["survey_id"] == f"SRV-{complaint_id}"

    # 9. Reopen ticket test
    reopen_payload = {
        "reason": "Replacement unit has a defective power cord."
    }
    res = client.post(f"/api/v1/complaints/{complaint_id}/reopen", json=reopen_payload)
    assert res.status_code == 200
    assert res.json()["status"] == "REOPENED"

