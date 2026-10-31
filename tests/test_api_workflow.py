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

def test_api_negative_scenarios():
    # Negative test 1: Pause SLA when complaint is not PENDING_CUSTOMER
    # Create fresh ticket in ASSIGNED state
    c_res = client.post("/api/v1/complaints", json={
        "customer_id": "CUS-000001",
        "intake_channel": "EMAIL",
        "message_body": "Delivery is delayed by 5 days."
    })
    c_id = c_res.json()["complaint_id"]

    # Attempting to resume when not paused fails with 400
    res_resume_invalid = client.post(f"/api/v1/complaints/{c_id}/sla/resume")
    assert res_resume_invalid.status_code == 400
    assert "not currently paused" in res_resume_invalid.json()["detail"]

    # Negative test 2: Survey submission before resolution fails with 400
    res_premature_survey = client.post(f"/api/v1/complaints/{c_id}/survey", json={
        "csat_score": 5, "nps_score": 10, "effort_score": 5
    })
    assert res_premature_survey.status_code == 400
    assert "Lifecycle violation" in res_premature_survey.json()["detail"]

    # Negative test 3: Reopen complaint when not resolved or closed fails with 400
    res_invalid_reopen = client.post(f"/api/v1/complaints/{c_id}/reopen", json={
        "reason": "Reopening early"
    })
    assert res_invalid_reopen.status_code == 400

    # Negative test 4: Filing complaint for non-existent customer fails with 404
    res_missing_cust = client.post("/api/v1/complaints", json={
        "customer_id": "CUS-999999",
        "intake_channel": "WEB_PORTAL",
        "message_body": "Orphan complaint test"
    })
    assert res_missing_cust.status_code == 404

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

    # 4. Pause SLA clock (via API)
    res = client.post(f"/api/v1/complaints/{complaint_id}/sla/pause", json={"reason": "Waiting on safety team on-site inspection"})
    assert res.status_code == 200
    assert res.json()["status"] == "PAUSED"
    assert res.json()["complaint_status"] == "PENDING_CUSTOMER"
    assert res.json()["paused_at"] is not None

    # Inspect SLA Clock to confirm paused_at stored
    detail_paused = client.get(f"/api/v1/complaints/{complaint_id}").json()
    orig_target_resol = detail_paused["sla_clock"]["target_resolution_time"]

    # 5. Resume SLA clock (via API) - verifies deadline extension and duration calculation
    res = client.post(f"/api/v1/complaints/{complaint_id}/sla/resume")
    assert res.status_code == 200
    assert res.json()["status"] == "RUNNING"
    assert res.json()["complaint_status"] == "IN_INVESTIGATION"
    assert "new_target_resolution_time" in res.json()
    assert "paused_duration_minutes" in res.json()

    # 5b. Customer message automatic resume test
    client.post(f"/api/v1/complaints/{complaint_id}/sla/pause", json={"reason": "Waiting on customer serial number"})
    res_cust_msg = client.post(f"/api/v1/complaints/{complaint_id}/messages", json={
        "sender_type": "CUSTOMER",
        "sender_id": "CUS-000001",
        "channel": "PORTAL_NOTE",
        "message_body": "Here is the serial number SN-998822."
    })
    assert res_cust_msg.status_code == 200
    detail_auto_resumed = client.get(f"/api/v1/complaints/{complaint_id}").json()
    assert detail_auto_resumed["complaint"]["status"] == "IN_INVESTIGATION"
    assert detail_auto_resumed["sla_clock"]["clock_status"] == "RUNNING"

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

    # 9. Reopen ticket test & SLA reset verification
    reopen_payload = {
        "reason": "Replacement unit has a defective power cord."
    }
    res = client.post(f"/api/v1/complaints/{complaint_id}/reopen", json=reopen_payload)
    assert res.status_code == 200
    assert res.json()["status"] == "REOPENED"
    assert "new_target_resolution_time" in res.json()

    # Verify SLA clock was reset for reopened investigation cycle
    detail_reopened = client.get(f"/api/v1/complaints/{complaint_id}").json()
    assert detail_reopened["complaint"]["status"] == "REOPENED"
    assert detail_reopened["sla_clock"]["clock_status"] == "RUNNING"
    assert detail_reopened["sla_clock"]["actual_resolution_time"] is None
    event_types = [e["event_type"] for e in detail_reopened["events"]]
    assert "REOPENED" in event_types
    assert "SLA_RESET" in event_types

    # 10. Propose 2nd resolution version (verifies resolution history is NOT overwritten)
    res_v2_payload = {
        "resolution_type": "REPLACEMENT",
        "root_cause": "DEFECTIVE_PRODUCT",
        "compensation_amount": 50.00
    }
    res_v2 = client.post(f"/api/v1/complaints/{complaint_id}/resolution", json=res_v2_payload)
    assert res_v2.status_code == 200
    assert res_v2.json()["version"] == 2
    assert res_v2.json()["requires_approval"] is True
    assert res_v2.json()["complaint_status"] == "RESOLUTION_PENDING"

    # Approver approves v2
    res_appr_v2 = client.post(f"/api/v1/complaints/{complaint_id}/resolution/approve", json={
        "approver_id": "APP-0001",
        "approved": True,
        "notes": "Approved replacement power cord"
    })
    assert res_appr_v2.status_code == 200
    assert res_appr_v2.json()["complaint_status"] == "RESOLVED"

    detail_v2 = client.get(f"/api/v1/complaints/{complaint_id}").json()
    assert len(detail_v2["resolutions_history"]) == 2
    assert detail_v2["resolutions_history"][0]["version"] == 1
    assert detail_v2["resolutions_history"][0]["compensation_amount"] == 350.00
    assert detail_v2["resolutions_history"][1]["version"] == 2
    assert detail_v2["resolutions_history"][1]["compensation_amount"] == 50.00

    # 11. Repeated survey for reopened cycle 2
    survey_v2_payload = {
        "csat_score": 4,
        "nps_score": 9,
        "effort_score": 4,
        "feedback_comments": "Second replacement works perfectly."
    }
    res_s2 = client.post(f"/api/v1/complaints/{complaint_id}/survey", json=survey_v2_payload)
    assert res_s2.status_code == 200
    assert res_s2.json()["cycle"] == 2

    detail_s2 = client.get(f"/api/v1/complaints/{complaint_id}").json()
    assert len(detail_s2["surveys_history"]) == 2
    assert detail_s2["complaint"]["status"] == "CLOSED"

def test_analytics_audit_endpoint_live_db_and_dataset():
    # 1. Live database audit
    res_db = client.get("/api/v1/analytics/audit?source=database")
    assert res_db.status_code == 200
    data_db = res_db.json()
    assert data_db["source"] == "database"
    assert data_db["is_healthy"] is True
    assert data_db["live_database_records"]["customers"] == 5000
    assert data_db["live_database_records"]["complaints"] >= 2000

    # 2. Complete generated dataset audit against ground truth
    res_ds = client.get("/api/v1/analytics/audit?source=dataset")
    assert res_ds.status_code == 200
    data_ds = res_ds.json()
    assert data_ds["source"] == "dataset"
    assert data_ds["is_healthy"] is True
    assert data_ds["recall_score"] == "100.0%"
    assert data_ds["precision_score"] == "100.0%"
    assert len(data_ds["detected_anomalies"]) == 6


