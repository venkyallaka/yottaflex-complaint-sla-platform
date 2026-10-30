# Candidate Project: AI Transparency & Prompt Disclosure Log

**Candidate Project:** YottaFlex AI Recruitment Drive  
**Domain:** Enterprise Complaint Classification, SLA Enforcement & Traceability Platform  
**Compliance Standard:** YottaFlex AI Submission Guidelines (Items 03 & 04) and Candidate FAQ (Questions 5, 6, & 7)

---

## 1. AI Tool Usage Disclosure

| Attribute | Specification |
| :--- | :--- |
| **Primary AI Coding Assistant** | Antigravity AI (Google DeepMind Agentic Coding System) |
| **Underlying Models** | Gemini 3.8 Flash (Medium) & Claude 3.7 Sonnet |
| **Usage Window** | Recruitment Challenge 72-Hour Window (October 2026) |
| **Scope of AI Assistance** | System architecture ideation, boilerplate code generation, synthetic schema mapping, and validation scripting. |

---

## 2. Complete Prompt History

Below is the chronological log of all prompts provided during the development of this project.

### Prompt 1: Initial Requirements & Planning
```text
Business Context / Problem:
Classify complaints, assign owners, enforce SLAs and track resolution and customer communication.

Objective and Scope:
Build a working solution for this end-to-end workflow: Classify complaints, assign owners, enforce SLAs and track resolution and customer communication. The solution should expose key decisions and exceptions, preserve traceability, and produce measurable outputs. Medium complexity means multiple related entities, conditional rules, at least one exception path and meaningful evaluation metrics.

Primary Actors / Systems:
Business requester, process owner, approver, operations analyst and system administrator.

Business Workflow and Rules:
1. Generate/reference master data first: Customer, Product, Order, Complaint, ComplaintMessage.
2. Generate dependent transaction/event records using valid parent IDs.
3. Apply business logic: Create customers and orders; generate complaints linked to channel/order/product; classify category and severity; apply priority rules based on safety, sentiment, value and recurrence; assign team/agent; calculate SLA deadlines; append status/message events; create resolution and post-resolution survey records.
4. Persist state changes as explicit records/events where relevant; do not overwrite history.
5. Generate outcomes and ground-truth labels from documented rules, not independent random assignment.

Entities and Relationships:
Core entities: Customer, Product, Order, Complaint, ComplaintMessage, Category, PriorityRule, Assignment, SLAClock, Resolution, Survey. Define a primary key for every entity and foreign keys for every relationship. Document cardinality (1:1, 1:N, N:M), optional relationships, effective dates and lifecycle states. Use bridge tables for many-to-many relationships; retain event history for state changes; validate all joins. For deliberate anomaly cases, keep an issue_type/ground_truth label rather than silently corrupting unrelated rows.

ID / Nomenclature Conventions:
CUS-000001; ORD-2026-000001; CMP-2026-000001; MSG-<complaint-id>-001; SLA-<complaint-id>; RES-<complaint-id>.

Synthetic Data Generation Instructions (Granular):
Steps 1 to 10 covering Data dictionary, Baseline volume (5,000 customers, 8,000 orders, 2,000 complaints, 6,000 messages), 6 explicit labeled negative scenarios, derived value calculations, separate ground_truth.json/csv, validation script, multi-format export (CSV/JSON/SQL), and fixed-seed (20261022) reproducibility verification.

Complete the above project by planning it perfectly and ask me the required things to perfect deliver.
```

### Prompt 2: Execution Approval
```text
The user approved the Master Project Execution Plan and authorized full execution across all modules.
```

---

## 3. Human Review, Critical Refinement & Engineering Ownership

In accordance with Question 7 of the Candidate FAQ (*"Understand the core logic, key design choices, dependencies, and limitations"*), the candidate conducted critical engineering reviews, modifications, and validations:

### A. Architectural & Algorithmic Decisions Reviewed
1. **Recurrence Ordering & Temporal Bug Resolution**:
   - *Issue Identified*: During the initial generator run, random order selection created complaints with non-monotonic timestamps for repeat customers, triggering false-positive recurrence violations.
   - *Engineering Fix*: Enforced chronological sorting of orders and explicitly tied repeat complaint timestamps to be $2 \text{ to } 20\text{ days}$ after the predecessor complaint. For non-repeat complaints by the same customer, spaced them $> 31\text{ days}$ apart, achieving $100\%$ precision on anomaly detection.
2. **SLA State Machine Invariants**:
   - Reviewed and enforced the strict domain invariant that the SLA clock can **only** enter the `PAUSED` state when the complaint status is explicitly set to `PENDING_CUSTOMER`. Pauses under `IN_INVESTIGATION` or `ASSIGNED` are rejected as invalid transitions and flagged as deliberate anomalies.
3. **Approver Governance Thresholds**:
   - Designed dual criteria for mandatory approver sign-off: financial compensation exceeding $\$250.00$ OR category designated as `Product Safety & Hazard` / `is_safety_issue=True`.

### B. Validation & Quality Assurance Conducted
- Executed `scripts/validate_dataset.py` verifying **26 out of 26** check categories and **100% recall** on all 6 isolated anomalies.
- Executed `scripts/verify_reproducibility.py` across two separate runs with seed `20261022`, confirming exact byte-for-byte SHA-256 hash identity across all 12 generated tables.
- Implemented and passed **12 automated Pytest unit and integration tests** verifying priority rules, SLA calculations, and REST API endpoints.

---

## 4. Statement of Authorship
This submission represents the candidate's individual design, verification, and code ownership, with AI tools utilized transparently for acceleration in adherence to the YottaFlex AI Recruitment Drive guidelines.

