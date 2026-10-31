"""
SQLAlchemy ORM models defining the 11 core and operational entities.
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Customer(Base):
    __tablename__ = "customers"
    customer_id = Column(String(32), primary_key=True, index=True)
    first_name = Column(String(64), nullable=False)
    last_name = Column(String(64), nullable=False)
    email = Column(String(128), unique=True, nullable=False)
    phone = Column(String(32), nullable=True)
    customer_tier = Column(String(16), nullable=False, default="STANDARD")
    is_vulnerable = Column(Boolean, nullable=False, default=False)
    account_created_at = Column(String(32), nullable=False)

    orders = relationship("Order", back_populates="customer")
    complaints = relationship("Complaint", back_populates="customer")

class Product(Base):
    __tablename__ = "products"
    product_id = Column(String(32), primary_key=True, index=True)
    product_name = Column(String(128), nullable=False)
    category_id = Column(String(16), ForeignKey("categories.category_id"), nullable=False)
    base_price = Column(Float, nullable=False)
    has_safety_hazard = Column(Boolean, nullable=False, default=False)
    warranty_months = Column(Integer, nullable=False, default=12)

    category = relationship("Category", back_populates="products")
    orders = relationship("Order", back_populates="product")

class Category(Base):
    __tablename__ = "categories"
    category_id = Column(String(16), primary_key=True, index=True)
    category_name = Column(String(64), unique=True, nullable=False)
    default_severity = Column(String(16), nullable=False, default="MEDIUM")
    assigned_team = Column(String(64), nullable=False)
    is_safety_critical = Column(Boolean, nullable=False, default=False)

    products = relationship("Product", back_populates="category")
    complaints = relationship("Complaint", back_populates="category")

class PriorityRule(Base):
    __tablename__ = "priority_rules"
    rule_id = Column(String(16), primary_key=True, index=True)
    rule_name = Column(String(64), nullable=False)
    condition_expression = Column(Text, nullable=False)
    target_priority = Column(String(16), nullable=False)
    target_response_hours = Column(Integer, nullable=False)
    target_resolution_hours = Column(Integer, nullable=False)

class Order(Base):
    __tablename__ = "orders"
    order_id = Column(String(32), primary_key=True, index=True)
    customer_id = Column(String(32), ForeignKey("customers.customer_id"), nullable=False)
    product_id = Column(String(32), ForeignKey("products.product_id"), nullable=False)
    order_amount = Column(Float, nullable=False)
    order_status = Column(String(24), nullable=False)
    order_date = Column(String(32), nullable=False)
    delivery_date = Column(String(32), nullable=True)

    customer = relationship("Customer", back_populates="orders")
    product = relationship("Product", back_populates="orders")
    complaints = relationship("Complaint", back_populates="order")

class Complaint(Base):
    __tablename__ = "complaints"
    complaint_id = Column(String(32), primary_key=True, index=True)
    customer_id = Column(String(32), ForeignKey("customers.customer_id"), nullable=False)
    order_id = Column(String(32), ForeignKey("orders.order_id"), nullable=True)
    category_id = Column(String(16), ForeignKey("categories.category_id"), nullable=False)
    intake_channel = Column(String(24), nullable=False)
    severity = Column(String(16), nullable=False)
    priority = Column(String(16), nullable=False)
    status = Column(String(24), nullable=False)
    sentiment_score = Column(Float, nullable=False)
    is_safety_issue = Column(Boolean, nullable=False, default=False)
    is_repeat_complaint = Column(Boolean, nullable=False, default=False)
    parent_complaint_id = Column(String(32), ForeignKey("complaints.complaint_id"), nullable=True)
    created_at = Column(String(32), nullable=False)
    updated_at = Column(String(32), nullable=False)
    closed_at = Column(String(32), nullable=True)

    customer = relationship("Customer", back_populates="complaints")
    order = relationship("Order", back_populates="complaints")
    category = relationship("Category", back_populates="complaints")
    parent_complaint = relationship("Complaint", remote_side=[complaint_id], backref="child_complaints")
    messages = relationship("ComplaintMessage", back_populates="complaint", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="complaint", cascade="all, delete-orphan")
    sla_clock = relationship("SLAClock", back_populates="complaint", uselist=False, cascade="all, delete-orphan")
    resolution = relationship("Resolution", back_populates="complaint", uselist=False, cascade="all, delete-orphan")
    survey = relationship("Survey", back_populates="complaint", uselist=False, cascade="all, delete-orphan")
    events = relationship("ComplaintEvent", back_populates="complaint", cascade="all, delete-orphan")

class ComplaintMessage(Base):
    __tablename__ = "complaint_messages"
    message_id = Column(String(48), primary_key=True, index=True)
    complaint_id = Column(String(32), ForeignKey("complaints.complaint_id"), nullable=False)
    sender_type = Column(String(16), nullable=False)
    sender_id = Column(String(32), nullable=False)
    channel = Column(String(24), nullable=False)
    message_body = Column(Text, nullable=False)
    sentiment_score = Column(Float, nullable=False)
    timestamp = Column(String(32), nullable=False)

    complaint = relationship("Complaint", back_populates="messages")

class Assignment(Base):
    __tablename__ = "assignments"
    assignment_id = Column(String(48), primary_key=True, index=True)
    complaint_id = Column(String(32), ForeignKey("complaints.complaint_id"), nullable=False)
    team_name = Column(String(64), nullable=False)
    agent_id = Column(String(32), nullable=False)
    assigned_by = Column(String(32), nullable=False)
    assigned_at = Column(String(32), nullable=False)
    released_at = Column(String(32), nullable=True)

    complaint = relationship("Complaint", back_populates="assignments")

class SLAClock(Base):
    __tablename__ = "sla_clocks"
    sla_id = Column(String(36), primary_key=True, index=True)
    complaint_id = Column(String(32), ForeignKey("complaints.complaint_id"), unique=True, nullable=False)
    target_response_time = Column(String(32), nullable=False)
    actual_response_time = Column(String(32), nullable=True)
    target_resolution_time = Column(String(32), nullable=False)
    actual_resolution_time = Column(String(32), nullable=True)
    clock_status = Column(String(16), nullable=False)
    paused_at = Column(String(32), nullable=True)
    paused_duration_minutes = Column(Integer, nullable=False, default=0)
    is_response_breached = Column(Boolean, nullable=False, default=False)
    is_resolution_breached = Column(Boolean, nullable=False, default=False)

    complaint = relationship("Complaint", back_populates="sla_clock")

class Resolution(Base):
    __tablename__ = "resolutions"
    resolution_id = Column(String(36), primary_key=True, index=True)
    complaint_id = Column(String(32), ForeignKey("complaints.complaint_id"), unique=True, nullable=False)
    resolution_type = Column(String(32), nullable=False)
    root_cause = Column(String(64), nullable=False)
    compensation_amount = Column(Float, nullable=False, default=0.0)
    requires_approval = Column(Boolean, nullable=False, default=False)
    approver_id = Column(String(32), nullable=True)
    approval_status = Column(String(16), nullable=False, default="NOT_REQUIRED")
    resolved_at = Column(String(32), nullable=False)

    complaint = relationship("Complaint", back_populates="resolution")

class Survey(Base):
    __tablename__ = "surveys"
    survey_id = Column(String(36), primary_key=True, index=True)
    complaint_id = Column(String(32), ForeignKey("complaints.complaint_id"), unique=True, nullable=False)
    csat_score = Column(Integer, nullable=False)
    nps_score = Column(Integer, nullable=False)
    effort_score = Column(Integer, nullable=False)
    feedback_comments = Column(Text, nullable=True)
    submitted_at = Column(String(32), nullable=False)

    complaint = relationship("Complaint", back_populates="survey")

class ComplaintEvent(Base):
    __tablename__ = "complaint_events"
    event_id = Column(String(36), primary_key=True, index=True)
    complaint_id = Column(String(32), ForeignKey("complaints.complaint_id"), nullable=False)
    event_type = Column(String(32), nullable=False)
    actor_role = Column(String(32), nullable=False)
    actor_id = Column(String(32), nullable=False)
    event_payload = Column(Text, nullable=False)
    created_at = Column(String(32), nullable=False)

    complaint = relationship("Complaint", back_populates="events")

