"""
Unit and integration tests for Alembic schema migrations and legacy database upgrades.
"""
import os
import tempfile
import pytest
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command

def test_legacy_database_migration_upgrade():
    """
    Tests upgrading a legacy database (revision 0001) to the latest schema (revision 0002),
    verifying that versioning, cycle tracking, and active flags are populated cleanly without data loss.
    """
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        test_db_path = os.path.join(tmp_dir, "legacy_test.db")
        test_db_url = f"sqlite:///{test_db_path}"

        alembic_ini_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        alembic_cfg = Config(alembic_ini_path)
        alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)

        # 1. Migrate to legacy baseline (0001_initial_schema)
        command.upgrade(alembic_cfg, "0001_initial_schema")

        # 2. Insert sample legacy records into old schema
        engine = create_engine(test_db_url)
        with engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO customers (customer_id, first_name, last_name, email, customer_tier, is_vulnerable, account_created_at) "
                "VALUES ('CUS-0001', 'Test', 'User', 'test@example.com', 'STANDARD', 0, '2026-01-01T00:00:00')"
            ))
            conn.execute(text(
                "INSERT INTO categories (category_id, category_name, default_severity, assigned_team, is_safety_critical) "
                "VALUES ('CAT-01', 'Hardware', 'MEDIUM', 'Hardware Support', 0)"
            ))
            conn.execute(text(
                "INSERT INTO complaints (complaint_id, customer_id, category_id, intake_channel, severity, priority, status, sentiment_score, is_safety_issue, is_repeat_complaint, created_at, updated_at) "
                "VALUES ('CMP-0001', 'CUS-0001', 'CAT-01', 'WEB_PORTAL', 'MEDIUM', 'P3_MEDIUM', 'RESOLVED', 0.2, 0, 0, '2026-01-02T10:00:00', '2026-01-02T12:00:00')"
            ))
            conn.execute(text(
                "INSERT INTO sla_clocks (sla_id, complaint_id, target_response_time, actual_response_time, target_resolution_time, actual_resolution_time, clock_status, paused_duration_minutes, is_response_breached, is_resolution_breached) "
                "VALUES ('SLA-CMP-0001', 'CMP-0001', '2026-01-02T14:00:00', '2026-01-02T11:00:00', '2026-01-04T10:00:00', '2026-01-02T12:00:00', 'COMPLETED', 0, 0, 0)"
            ))
            conn.execute(text(
                "INSERT INTO resolutions (resolution_id, complaint_id, resolution_type, root_cause, compensation_amount, requires_approval, approval_status, resolved_at) "
                "VALUES ('RES-CMP-0001', 'CMP-0001', 'FULL_REFUND', 'DEFECTIVE_PRODUCT', 120.0, 0, 'NOT_REQUIRED', '2026-01-02T12:00:00')"
            ))
            conn.execute(text(
                "INSERT INTO surveys (survey_id, complaint_id, csat_score, nps_score, effort_score, feedback_comments, submitted_at) "
                "VALUES ('SRV-CMP-0001', 'CMP-0001', 5, 10, 5, 'Great support', '2026-01-02T14:00:00')"
            ))

        # 3. Upgrade to head revision (0002_add_versioning_and_cycles)
        engine.dispose()
        command.upgrade(alembic_cfg, "head")

        # 4. Verify new columns exist with correct defaults and legacy data preserved
        engine = create_engine(test_db_url)
        try:
            with engine.connect() as conn:
                res_row = conn.execute(text("SELECT version, is_current, compensation_amount FROM resolutions WHERE resolution_id = 'RES-CMP-0001'")).fetchone()
                assert res_row is not None
                assert res_row[0] == 1  # version default
                assert res_row[1] == 1  # is_current default
                assert res_row[2] == 120.0  # preserved legacy data

                srv_row = conn.execute(text("SELECT cycle, csat_score FROM surveys WHERE survey_id = 'SRV-CMP-0001'")).fetchone()
                assert srv_row is not None
                assert srv_row[0] == 1  # cycle default
                assert srv_row[1] == 5  # preserved CSAT

                sla_row = conn.execute(text("SELECT cycle, is_current, clock_status FROM sla_clocks WHERE sla_id = 'SLA-CMP-0001'")).fetchone()
                assert sla_row is not None
                assert sla_row[0] == 1  # cycle default
                assert sla_row[1] == 1  # is_current default
                assert sla_row[2] == "COMPLETED"  # preserved status
        finally:
            engine.dispose()
