"""initial schema baseline

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Customers
    op.create_table(
        'customers',
        sa.Column('customer_id', sa.String(length=32), nullable=False),
        sa.Column('first_name', sa.String(length=64), nullable=False),
        sa.Column('last_name', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=128), nullable=False),
        sa.Column('phone', sa.String(length=32), nullable=True),
        sa.Column('customer_tier', sa.String(length=16), nullable=False),
        sa.Column('is_vulnerable', sa.Boolean(), nullable=False),
        sa.Column('account_created_at', sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint('customer_id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_customers_customer_id'), 'customers', ['customer_id'], unique=False)

    # 2. Categories
    op.create_table(
        'categories',
        sa.Column('category_id', sa.String(length=16), nullable=False),
        sa.Column('category_name', sa.String(length=64), nullable=False),
        sa.Column('default_severity', sa.String(length=16), nullable=False),
        sa.Column('assigned_team', sa.String(length=64), nullable=False),
        sa.Column('is_safety_critical', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('category_id'),
        sa.UniqueConstraint('category_name')
    )
    op.create_index(op.f('ix_categories_category_id'), 'categories', ['category_id'], unique=False)

    # 3. Products
    op.create_table(
        'products',
        sa.Column('product_id', sa.String(length=32), nullable=False),
        sa.Column('product_name', sa.String(length=128), nullable=False),
        sa.Column('category_id', sa.String(length=16), nullable=False),
        sa.Column('base_price', sa.Float(), nullable=False),
        sa.Column('has_safety_hazard', sa.Boolean(), nullable=False),
        sa.Column('warranty_months', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.category_id']),
        sa.PrimaryKeyConstraint('product_id')
    )
    op.create_index(op.f('ix_products_product_id'), 'products', ['product_id'], unique=False)

    # 4. Priority Rules
    op.create_table(
        'priority_rules',
        sa.Column('rule_id', sa.String(length=16), nullable=False),
        sa.Column('rule_name', sa.String(length=64), nullable=False),
        sa.Column('condition_expression', sa.Text(), nullable=False),
        sa.Column('target_priority', sa.String(length=16), nullable=False),
        sa.Column('target_response_hours', sa.Integer(), nullable=False),
        sa.Column('target_resolution_hours', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('rule_id')
    )
    op.create_index(op.f('ix_priority_rules_rule_id'), 'priority_rules', ['rule_id'], unique=False)

    # 5. Orders
    op.create_table(
        'orders',
        sa.Column('order_id', sa.String(length=32), nullable=False),
        sa.Column('customer_id', sa.String(length=32), nullable=False),
        sa.Column('product_id', sa.String(length=32), nullable=False),
        sa.Column('order_amount', sa.Float(), nullable=False),
        sa.Column('order_status', sa.String(length=24), nullable=False),
        sa.Column('order_date', sa.String(length=32), nullable=False),
        sa.Column('delivery_date', sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.customer_id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.product_id']),
        sa.PrimaryKeyConstraint('order_id')
    )
    op.create_index(op.f('ix_orders_order_id'), 'orders', ['order_id'], unique=False)

    # 6. Complaints
    op.create_table(
        'complaints',
        sa.Column('complaint_id', sa.String(length=32), nullable=False),
        sa.Column('customer_id', sa.String(length=32), nullable=False),
        sa.Column('order_id', sa.String(length=32), nullable=True),
        sa.Column('category_id', sa.String(length=16), nullable=False),
        sa.Column('intake_channel', sa.String(length=24), nullable=False),
        sa.Column('severity', sa.String(length=16), nullable=False),
        sa.Column('priority', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=24), nullable=False),
        sa.Column('sentiment_score', sa.Float(), nullable=False),
        sa.Column('is_safety_issue', sa.Boolean(), nullable=False),
        sa.Column('is_repeat_complaint', sa.Boolean(), nullable=False),
        sa.Column('parent_complaint_id', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.String(length=32), nullable=False),
        sa.Column('updated_at', sa.String(length=32), nullable=False),
        sa.Column('closed_at', sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['categories.category_id']),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.customer_id']),
        sa.ForeignKeyConstraint(['order_id'], ['orders.order_id']),
        sa.ForeignKeyConstraint(['parent_complaint_id'], ['complaints.complaint_id']),
        sa.PrimaryKeyConstraint('complaint_id')
    )
    op.create_index(op.f('ix_complaints_complaint_id'), 'complaints', ['complaint_id'], unique=False)

    # 7. Complaint Messages
    op.create_table(
        'complaint_messages',
        sa.Column('message_id', sa.String(length=48), nullable=False),
        sa.Column('complaint_id', sa.String(length=32), nullable=False),
        sa.Column('sender_type', sa.String(length=16), nullable=False),
        sa.Column('sender_id', sa.String(length=32), nullable=False),
        sa.Column('channel', sa.String(length=24), nullable=False),
        sa.Column('message_body', sa.Text(), nullable=False),
        sa.Column('sentiment_score', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(['complaint_id'], ['complaints.complaint_id']),
        sa.PrimaryKeyConstraint('message_id')
    )
    op.create_index(op.f('ix_complaint_messages_message_id'), 'complaint_messages', ['message_id'], unique=False)

    # 8. Assignments
    op.create_table(
        'assignments',
        sa.Column('assignment_id', sa.String(length=48), nullable=False),
        sa.Column('complaint_id', sa.String(length=32), nullable=False),
        sa.Column('team_name', sa.String(length=64), nullable=False),
        sa.Column('agent_id', sa.String(length=32), nullable=False),
        sa.Column('assigned_by', sa.String(length=32), nullable=False),
        sa.Column('assigned_at', sa.String(length=32), nullable=False),
        sa.Column('released_at', sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(['complaint_id'], ['complaints.complaint_id']),
        sa.PrimaryKeyConstraint('assignment_id')
    )
    op.create_index(op.f('ix_assignments_assignment_id'), 'assignments', ['assignment_id'], unique=False)

    # 9. SLA Clocks (legacy baseline with single clock per complaint)
    op.create_table(
        'sla_clocks',
        sa.Column('sla_id', sa.String(length=48), nullable=False),
        sa.Column('complaint_id', sa.String(length=32), nullable=False),
        sa.Column('target_response_time', sa.String(length=32), nullable=False),
        sa.Column('actual_response_time', sa.String(length=32), nullable=True),
        sa.Column('target_resolution_time', sa.String(length=32), nullable=False),
        sa.Column('actual_resolution_time', sa.String(length=32), nullable=True),
        sa.Column('clock_status', sa.String(length=16), nullable=False),
        sa.Column('paused_at', sa.String(length=32), nullable=True),
        sa.Column('paused_duration_minutes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_response_breached', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_resolution_breached', sa.Boolean(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['complaint_id'], ['complaints.complaint_id']),
        sa.PrimaryKeyConstraint('sla_id')
    )
    op.create_index(op.f('ix_sla_clocks_sla_id'), 'sla_clocks', ['sla_id'], unique=False)

    # 10. Resolutions (legacy baseline without version column)
    op.create_table(
        'resolutions',
        sa.Column('resolution_id', sa.String(length=48), nullable=False),
        sa.Column('complaint_id', sa.String(length=32), nullable=False),
        sa.Column('resolution_type', sa.String(length=32), nullable=False),
        sa.Column('root_cause', sa.String(length=64), nullable=False),
        sa.Column('compensation_amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('approver_id', sa.String(length=32), nullable=True),
        sa.Column('approval_status', sa.String(length=16), nullable=False, server_default='NOT_REQUIRED'),
        sa.Column('resolved_at', sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(['complaint_id'], ['complaints.complaint_id']),
        sa.PrimaryKeyConstraint('resolution_id')
    )
    op.create_index(op.f('ix_resolutions_resolution_id'), 'resolutions', ['resolution_id'], unique=False)

    # 11. Surveys (legacy baseline without cycle column)
    op.create_table(
        'surveys',
        sa.Column('survey_id', sa.String(length=48), nullable=False),
        sa.Column('complaint_id', sa.String(length=32), nullable=False),
        sa.Column('csat_score', sa.Integer(), nullable=False),
        sa.Column('nps_score', sa.Integer(), nullable=False),
        sa.Column('effort_score', sa.Integer(), nullable=False),
        sa.Column('feedback_comments', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(['complaint_id'], ['complaints.complaint_id']),
        sa.PrimaryKeyConstraint('survey_id')
    )
    op.create_index(op.f('ix_surveys_survey_id'), 'surveys', ['survey_id'], unique=False)

    # 12. Complaint Events
    op.create_table(
        'complaint_events',
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('complaint_id', sa.String(length=32), nullable=False),
        sa.Column('event_type', sa.String(length=32), nullable=False),
        sa.Column('actor_role', sa.String(length=32), nullable=False),
        sa.Column('actor_id', sa.String(length=32), nullable=False),
        sa.Column('event_payload', sa.Text(), nullable=False),
        sa.Column('created_at', sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(['complaint_id'], ['complaints.complaint_id']),
        sa.PrimaryKeyConstraint('event_id')
    )
    op.create_index(op.f('ix_complaint_events_event_id'), 'complaint_events', ['event_id'], unique=False)

def downgrade() -> None:
    op.drop_table('complaint_events')
    op.drop_table('surveys')
    op.drop_table('resolutions')
    op.drop_table('sla_clocks')
    op.drop_table('assignments')
    op.drop_table('complaint_messages')
    op.drop_table('complaints')
    op.drop_table('orders')
    op.drop_table('priority_rules')
    op.drop_table('products')
    op.drop_table('categories')
    op.drop_table('customers')

