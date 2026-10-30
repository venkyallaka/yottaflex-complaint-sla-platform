"""
Pydantic schemas for request validation and response serialization.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ComplaintCreateRequest(BaseModel):
    customer_id: str = Field(..., description="Customer ID (e.g. CUS-000001)")
    order_id: Optional[str] = Field(None, description="Optional linked Order ID (e.g. ORD-2026-000001)")
    category_id: Optional[str] = Field(None, description="Optional category; auto-classified if omitted")
    intake_channel: str = Field(default="WEB_PORTAL", description="EMAIL, PHONE, WEB_PORTAL, CHAT, MOBILE_APP")
    message_body: str = Field(..., description="Customer complaint description")

class MessageCreateRequest(BaseModel):
    sender_type: str = Field(..., description="CUSTOMER, AGENT, SYSTEM, APPROVER")
    sender_id: str = Field(..., description="ID of sender (e.g. AGT-0001, CUS-000001)")
    channel: str = Field(default="WEB_PORTAL")
    message_body: str = Field(..., min_length=1)

class PauseSLARequest(BaseModel):
    reason: str = Field(..., description="Reason for pausing SLA clock (e.g. waiting for customer photos)")

class ResolutionProposeRequest(BaseModel):
    resolution_type: str = Field(..., description="FULL_REFUND, PARTIAL_CREDIT, REPLACEMENT, TECHNICAL_FIX, PROCESS_APOLOGY")
    root_cause: str = Field(..., description="DEFECTIVE_PRODUCT, LOGISTICS_DELAY, BILLING_GLITCH, USER_ERROR, CARRIER_LOST")
    compensation_amount: float = Field(default=0.0, ge=0.0)

class ResolutionApproveRequest(BaseModel):
    approver_id: str = Field(..., description="Approver identifier (e.g. APP-0001)")
    approved: bool = Field(..., description="True to approve, False to reject")
    notes: Optional[str] = Field(None, description="Optional approval or rejection remarks")

class SurveySubmitRequest(BaseModel):
    csat_score: int = Field(..., ge=1, le=5, description="CSAT (1-5)")
    nps_score: int = Field(..., ge=0, le=10, description="NPS (0-10)")
    effort_score: int = Field(..., ge=1, le=5, description="Customer Effort Score (1-5)")
    feedback_comments: Optional[str] = Field(None)

class ReopenRequest(BaseModel):
    reason: str = Field(..., description="Reason for reopening resolved case")
