# Data Dictionary: Enterprise Complaint & SLA Management Platform

This document fulfills **Step 1** of the Synthetic Data Generation & Schema Specification instructions.
It details every field across all 11 core and operational entities, specifying:
- **Type**: SQL / Python data type
- **Required/Optional**: Nullability constraints
- **Allowed Values / Enums**: Permitted domain values
- **Units**: Currency, duration, score scale
- **Uniqueness**: Primary key / Unique constraints
- **Validation Rule**: Business and referential integrity constraints

---

## 1. Master Data Entities

### 1.1 Customer (`customers`)
Represents the individual or enterprise placing orders and filing complaints.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `customer_id` | `VARCHAR(32)` | Required | `^CUS-\d{6}$` | None | Primary Key | Zero-padded 6-digit ID (e.g. `CUS-000001`). Immutable. |
| `first_name` | `VARCHAR(64)` | Required | Alphabetic strings | None | Non-unique | Length 1–64. |
| `last_name` | `VARCHAR(64)` | Required | Alphabetic strings | None | Non-unique | Length 1–64. |
| `email` | `VARCHAR(128)`| Required | Valid RFC 5322 email | None | Unique | Standard email regex; lowercase normalized. |
| `phone` | `VARCHAR(32)` | Optional | `^\+?[1-9]\d{1,14}$` | E.164 | Non-unique | Standard telephone format. |
| `customer_tier` | `VARCHAR(16)` | Required | `STANDARD`, `SILVER`, `GOLD`, `PLATINUM` | None | Non-unique | Customer commercial segment. |
| `is_vulnerable` | `BOOLEAN` | Required | `TRUE`, `FALSE` | None | Non-unique | Flag for accessibility, elderly, or critical vulnerability status (escalation trigger). |
| `account_created_at` | `TIMESTAMP` | Required | ISO 8601 UTC timestamp | UTC | Non-unique | Must be before or equal to current timestamp and before any linked order. |

---

### 1.2 Product (`products`)
Represents catalog goods or services for which orders are placed and issues may arise.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `product_id` | `VARCHAR(32)` | Required | `^PRD-\d{4}$` | None | Primary Key | Zero-padded 4-digit ID (e.g. `PRD-0001`). |
| `product_name` | `VARCHAR(128)`| Required | Text string | None | Non-unique | Non-empty product name. |
| `category_id` | `VARCHAR(16)` | Required | Foreign Key -> `categories.category_id` | None | Non-unique | Must match a valid category ID. |
| `base_price` | `DECIMAL(10,2)`| Required | Numeric >= 0.00 | USD ($) | Non-unique | Cannot be negative. |
| `has_safety_hazard`| `BOOLEAN` | Required | `TRUE`, `FALSE` | None | Non-unique | If TRUE, issues linked to this product default to high severity. |
| `warranty_months` | `INTEGER` | Required | 0 to 60 | Months | Non-unique | Product warranty duration. |

---

### 1.3 Category (`categories`)
Defines the standard taxonomy of 10 complaint domains and default service tiers.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `category_id` | `VARCHAR(16)` | Required | `CAT-01` through `CAT-10` | None | Primary Key | Fixed 2-digit category ID (`CAT-01` to `CAT-10`). |
| `category_name` | `VARCHAR(64)` | Required | E.g., `Product Safety`, `Delivery Delay`, `Billing & Refunds` | None | Unique | Distinct human-readable department name. |
| `default_severity`| `VARCHAR(16)` | Required | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` | None | Non-unique | Baseline severity for newly filed complaints in this domain. |
| `assigned_team` | `VARCHAR(64)` | Required | E.g. `Safety Escalations`, `Logistics Team`, `Billing Ops` | None | Non-unique | Default routing queue. |
| `is_safety_critical`| `BOOLEAN` | Required | `TRUE`, `FALSE` | None | Non-unique | `TRUE` if complaints in this category trigger automatic regulatory/safety alerts. |

---

### 1.4 PriorityRule (`priority_rules`)
Declarative rule table governing priority calculation from multiple input signals.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `rule_id` | `VARCHAR(16)` | Required | `^RUL-\d{2}$` | None | Primary Key | E.g. `RUL-01` to `RUL-08`. |
| `rule_name` | `VARCHAR(64)` | Required | Descriptive string | None | Unique | Human-readable rule title. |
| `condition_expression`| `TEXT` | Required | Boolean logic string | None | Non-unique | Evaluated against complaint/customer/order features. |
| `target_priority` | `VARCHAR(16)` | Required | `P1_CRITICAL`, `P2_HIGH`, `P3_MEDIUM`, `P4_LOW` | None | Non-unique | Output priority if condition evaluates to true. |
| `target_response_hours`| `INTEGER`| Required | 1, 4, 12, 24 | Hours | Non-unique | Response SLA clock target. |
| `target_resolution_hours`| `INTEGER`| Required | 4, 24, 48, 96 | Hours | Non-unique | Resolution SLA clock target. |

---

## 2. Transactional & Event Entities

### 2.1 Order (`orders`)
Commercial transactions linking customers to purchased products.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `order_id` | `VARCHAR(32)` | Required | `^ORD-2026-\d{6}$` | None | Primary Key | `ORD-2026-` prefix followed by 6 zero-padded digits. |
| `customer_id` | `VARCHAR(32)` | Required | Foreign Key -> `customers.customer_id` | None | Non-unique | Must reference a valid customer. |
| `product_id` | `VARCHAR(32)` | Required | Foreign Key -> `products.product_id` | None | Non-unique | Must reference an existing product. |
| `order_amount` | `DECIMAL(10,2)`| Required | Numeric > 0.00 | USD ($) | Non-unique | Arithmetic reconciliation with item price * quantity. |
| `order_status` | `VARCHAR(24)` | Required | `PLACED`, `PROCESSING`, `SHIPPED`, `DELIVERED`, `CANCELLED`, `RETURNED` | None | Non-unique | Valid lifecycle state. |
| `order_date` | `TIMESTAMP` | Required | ISO 8601 UTC timestamp | UTC | Non-unique | Must be >= `customers.account_created_at`. |
| `delivery_date` | `TIMESTAMP` | Optional | ISO 8601 UTC timestamp | UTC | Non-unique | Must be >= `order_date` if populated. |

---

### 2.2 Complaint (`complaints`)
Central entity managing reported customer grievances and lifecycle states.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `complaint_id` | `VARCHAR(32)` | Required | `^CMP-2026-\d{6}$` | None | Primary Key | `CMP-2026-` prefix followed by 6 zero-padded digits. |
| `customer_id` | `VARCHAR(32)` | Required | Foreign Key -> `customers.customer_id` | None | Non-unique | Must match valid customer (unless deliberate orphan anomaly). |
| `order_id` | `VARCHAR(32)` | Optional | Foreign Key -> `orders.order_id` | None | Non-unique | Must match valid order if provided. |
| `category_id` | `VARCHAR(16)` | Required | Foreign Key -> `categories.category_id` | None | Non-unique | Valid category reference. |
| `intake_channel` | `VARCHAR(24)` | Required | `EMAIL`, `PHONE`, `WEB_PORTAL`, `CHAT`, `MOBILE_APP` | None | Non-unique | Allowed omnichannel channels. |
| `severity` | `VARCHAR(16)` | Required | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` | None | Non-unique | Assessment of operational impact. |
| `priority` | `VARCHAR(16)` | Required | `P1_CRITICAL`, `P2_HIGH`, `P3_MEDIUM`, `P4_LOW` | None | Non-unique | Derived deterministically from PriorityRules. |
| `status` | `VARCHAR(24)` | Required | `OPEN`, `ASSIGNED`, `IN_INVESTIGATION`, `PENDING_CUSTOMER`, `RESOLVED`, `CLOSED`, `REOPENED` | None | Non-unique | Governed by finite state machine. |
| `sentiment_score` | `DECIMAL(3,2)` | Required | -1.00 to +1.00 | Scale | Non-unique | Polarity: -1.0 (extremely negative) to +1.0 (positive). |
| `is_safety_issue`| `BOOLEAN` | Required | `TRUE`, `FALSE` | None | Non-unique | If TRUE, forces priority = `P1_CRITICAL`. |
| `is_repeat_complaint`| `BOOLEAN` | Required | `TRUE`, `FALSE` | None | Non-unique | TRUE if customer had complaint within previous 30 days. |
| `parent_complaint_id`| `VARCHAR(32)`| Optional | Foreign Key -> `complaints.complaint_id` | None | Non-unique | Self-referential link for repeat/reopened issues. |
| `created_at` | `TIMESTAMP` | Required | ISO 8601 UTC timestamp | UTC | Non-unique | Baseline event timestamp. Must be >= `orders.order_date`. |
| `updated_at` | `TIMESTAMP` | Required | ISO 8601 UTC timestamp | UTC | Non-unique | Must be >= `created_at`. |
| `closed_at` | `TIMESTAMP` | Optional | ISO 8601 UTC timestamp | UTC | Non-unique | Only populated when status is `CLOSED`. |

---

### 2.3 ComplaintMessage (`complaint_messages`)
Chronological omnichannel communication records between customer and internal staff.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `message_id` | `VARCHAR(48)` | Required | `^MSG-CMP-2026-\d{6}-\d{3}$` | None | Primary Key | Composite format: `MSG-<complaint_id>-<seq:03d>`. |
| `complaint_id` | `VARCHAR(32)` | Required | Foreign Key -> `complaints.complaint_id` | None | Non-unique | Must match parent complaint. |
| `sender_type` | `VARCHAR(16)` | Required | `CUSTOMER`, `AGENT`, `SYSTEM`, `APPROVER` | None | Non-unique | Identifies message originator. |
| `sender_id` | `VARCHAR(32)` | Required | Valid actor ID | None | Non-unique | Customer ID, Agent ID, or `SYS_AUTOMATION`. |
| `channel` | `VARCHAR(24)` | Required | `EMAIL`, `PHONE_LOG`, `PORTAL_NOTE`, `CHAT_MSG`, `SMS` | None | Non-unique | Transmission medium. |
| `message_body` | `TEXT` | Required | Non-empty text | None | Non-unique | Thread payload. |
| `sentiment_score` | `DECIMAL(3,2)` | Required | -1.00 to +1.00 | Scale | Non-unique | NLP sentiment analysis score of message body. |
| `timestamp` | `TIMESTAMP` | Required | ISO 8601 UTC timestamp | UTC | Non-unique | Must be >= `complaint.created_at`. Strictly ascending sequence. |

---

### 2.4 Assignment (`assignments`)
History of ownership changes and routing events across teams and agents.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `assignment_id` | `VARCHAR(48)` | Required | `^ASN-CMP-2026-\d{6}-\d{3}$` | None | Primary Key | `ASN-<complaint_id>-<seq:03d>`. |
| `complaint_id` | `VARCHAR(32)` | Required | Foreign Key -> `complaints.complaint_id` | None | Non-unique | References parent complaint. |
| `team_name` | `VARCHAR(64)` | Required | E.g. `Tier 1 Support`, `Tier 2 Escalations`, `Safety Board` | None | Non-unique | Owning organizational unit. |
| `agent_id` | `VARCHAR(32)` | Required | `^AGT-\d{4}$` | None | Non-unique | Assigned operational handler. |
| `assigned_by` | `VARCHAR(32)` | Required | `SYS_AUTO_ROUTER`, `AGT-xxxx`, `MGR-xxxx` | None | Non-unique | Originator of assignment decision. |
| `assigned_at` | `TIMESTAMP` | Required | ISO 8601 UTC timestamp | UTC | Non-unique | Must be >= `complaint.created_at`. |
| `released_at` | `TIMESTAMP` | Optional | ISO 8601 UTC timestamp | UTC | Non-unique | Populated when handed off to new agent. Must be >= `assigned_at`. |

---

### 2.5 SLAClock (`sla_clocks`)
State machine managing compliance with contractual response and resolution time targets.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `sla_id` | `VARCHAR(36)` | Required | `^SLA-CMP-2026-\d{6}$` | None | Primary Key | 1:1 mapping: `SLA-<complaint_id>`. |
| `complaint_id` | `VARCHAR(32)` | Required | Foreign Key -> `complaints.complaint_id` | None | Unique | Strict 1:1 relationship with Complaint. |
| `target_response_time`| `TIMESTAMP` | Required | ISO 8601 UTC timestamp | UTC | Non-unique | `created_at + target_response_hours`. |
| `actual_response_time`| `TIMESTAMP` | Optional | ISO 8601 UTC timestamp | UTC | Non-unique | Timestamp of first agent response message. |
| `target_resolution_time`|`TIMESTAMP`| Required | ISO 8601 UTC timestamp | UTC | Non-unique | Baseline deadline, extended by total paused duration. |
| `actual_resolution_time`|`TIMESTAMP`| Optional | ISO 8601 UTC timestamp | UTC | Non-unique | Timestamp when resolution status reached. |
| `clock_status` | `VARCHAR(16)` | Required | `RUNNING`, `PAUSED`, `RESUMED`, `BREACHED`, `COMPLETED` | None | Non-unique | Active state of the SLA clock. |
| `paused_duration_minutes`|`INTEGER` | Required | >= 0 | Minutes | Non-unique | Cumulative paused duration during customer wait states. |
| `is_response_breached`| `BOOLEAN` | Required | `TRUE`, `FALSE` | None | Non-unique | `TRUE` if `actual_response_time > target_response_time`. |
| `is_resolution_breached`|`BOOLEAN`| Required | `TRUE`, `FALSE` | None | Non-unique | `TRUE` if `actual_resolution_time > target_resolution_time`. |

---

### 2.6 Resolution (`resolutions`)
Formal business settlement of a complaint including root cause and remedial actions.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `resolution_id`| `VARCHAR(36)` | Required | `^RES-CMP-2026-\d{6}$` | None | Primary Key | 1:1 mapping: `RES-<complaint_id>`. |
| `complaint_id` | `VARCHAR(32)` | Required | Foreign Key -> `complaints.complaint_id` | None | Unique | Must match parent complaint. |
| `resolution_type`| `VARCHAR(32)`| Required | `FULL_REFUND`, `PARTIAL_CREDIT`, `REPLACEMENT`, `TECHNICAL_FIX`, `PROCESS_APOLOGY`, `REJECTED_UNFOUNDED` | None | Non-unique | Category of remedy provided. |
| `root_cause` | `VARCHAR(64)` | Required | `DEFECTIVE_PRODUCT`, `LOGISTICS_DELAY`, `BILLING_GLITCH`, `USER_ERROR`, `CARRIER_LOST` | None | Non-unique | Documented root cause. |
| `compensation_amount`|`DECIMAL(10,2)`| Required | Numeric >= 0.00 | USD ($) | Non-unique | Monetary payout or credit issued. |
| `requires_approval`| `BOOLEAN` | Required | `TRUE`, `FALSE` | None | Non-unique | `TRUE` if compensation > $250.00 or safety critical issue. |
| `approver_id` | `VARCHAR(32)` | Optional | `^APP-\d{4}$` | None | Non-unique | Required if `requires_approval` is TRUE. |
| `approval_status`| `VARCHAR(16)` | Required | `NOT_REQUIRED`, `PENDING_REVIEW`, `APPROVED`, `REJECTED` | None | Non-unique | State of financial/safety approval. |
| `resolved_at` | `TIMESTAMP` | Required | ISO 8601 UTC timestamp | UTC | Non-unique | Must be >= `complaints.created_at`. |

---

### 2.7 Survey (`surveys`)
Post-resolution customer experience feedback and quality scores.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `survey_id` | `VARCHAR(36)` | Required | `^SRV-CMP-2026-\d{6}$` | None | Primary Key | `SRV-<complaint_id>`. |
| `complaint_id` | `VARCHAR(32)` | Required | Foreign Key -> `complaints.complaint_id` | None | Unique | One survey per complaint. |
| `csat_score` | `INTEGER` | Required | 1 to 5 | Score (1-5) | Non-unique | Customer Satisfaction rating (1=Very Dissatisfied, 5=Very Satisfied). |
| `nps_score` | `INTEGER` | Required | 0 to 10 | Score (0-10)| Non-unique | Net Promoter Score (0-6 Detractor, 7-8 Passive, 9-10 Promoter). |
| `effort_score` | `INTEGER` | Required | 1 to 5 | Score (1-5) | Non-unique | Customer Effort Score (1=Very Difficult, 5=Very Easy). |
| `feedback_comments`| `TEXT` | Optional | Text | None | Non-unique | Free-text feedback. |
| `submitted_at` | `TIMESTAMP` | Required | ISO 8601 UTC timestamp | UTC | Non-unique | Must be >= `resolutions.resolved_at` (unless premature anomaly). |

---

### 2.8 ComplaintEvent (`complaint_events`) - Audit Store
Immutable append-only log capturing all state changes and lifecycle events.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `event_id` | `VARCHAR(36)` | Required | `^EVT-2026-\d{7}$` | None | Primary Key | Monotonically increasing sequential audit ID. |
| `complaint_id` | `VARCHAR(32)` | Required | Foreign Key -> `complaints.complaint_id` | None | Non-unique | Target complaint entity. |
| `event_type` | `VARCHAR(32)` | Required | `CREATED`, `CLASSIFIED`, `PRIORITIZED`, `ASSIGNED`, `MESSAGE_SENT`, `SLA_PAUSED`, `SLA_RESUMED`, `RESOLUTION_PROPOSED`, `RESOLUTION_APPROVED`, `CLOSED`, `REOPENED` | None | Non-unique | Strict lifecycle transition enum. |
| `actor_role` | `VARCHAR(32)` | Required | `BUSINESS_REQUESTER`, `PROCESS_OWNER`, `APPROVER`, `OPERATIONS_ANALYST`, `SYSTEM_ADMIN` | None | Non-unique | Originator role. |
| `actor_id` | `VARCHAR(32)` | Required | Valid actor identifier | None | Non-unique | Identifying username or agent/approver ID. |
| `event_payload`| `JSON` / `TEXT`| Required | Serialized JSON dictionary | None | Non-unique | State delta containing before/after values. |
| `created_at` | `TIMESTAMP` | Required | ISO 8601 UTC timestamp | UTC | Non-unique | Immutable wall clock event timestamp. |

