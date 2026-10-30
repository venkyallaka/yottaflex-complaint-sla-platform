# Operational & Data Evaluation Metrics

This document outlines the measurable outputs, operational key performance indicators (KPIs), and validation evaluation criteria defined for this platform.

---

## 1. Operational Key Performance Indicators (KPIs)

### 1.1 SLA Compliance Rate (%)
$$
\text{SLA Compliance} = \frac{\text{Total Complaints Resolved Within Target Resolution Time}}{\text{Total Resolved Complaints}} \times 100
$$
- **Target**: >= 95.0% for P3/P4, >= 98.0% for P1/P2.
- **Reporting Granularity**: By Priority tier, Category, and Assigned Team.

### 1.2 Mean Time to First Response (MTFR)
$$
\text{MTFR} = \frac{1}{N} \sum_{i=1}^{N} (\text{actual\_response\_time}_i - \text{created\_at}_i)
$$
- **Benchmark**: < 1 hour for P1, < 4 hours for P2, < 12 hours for P3, < 24 hours for P4.

### 1.3 Mean Time to Resolution (MTTR)
$$
\text{MTTR} = \frac{1}{N} \sum_{i=1}^{N} \left[(\text{resolved\_at}_i - \text{created\_at}_i) - \text{paused\_duration}_i\right]
$$
- Calculated excluding authorized paused customer wait states to ensure fairness.

### 1.4 First Contact Resolution (FCR) Rate (%)
$$
\text{FCR Rate} = \frac{\text{Complaints Resolved with Exactly 1 Inbound and 1 Outbound Message}}{\text{Total Resolved Complaints}} \times 100
$$

### 1.5 Net Promoter Score (NPS) & CSAT
- **CSAT**: Average rating on a scale of 1 to 5.
- **NPS**: 
$$
\text{NPS} = \% \text{ Promoters (9-10)} - \% \text{ Detractors (0-6)}
$$

---

## 2. Data Generation & Integrity Evaluation Metrics

The synthetic dataset generator and validation suite are evaluated across the 7 dimensions specified in the problem statement:

| Evaluation Dimension | Metric / Criterion | Threshold / Acceptance Standard |
| :--- | :--- | :--- |
| **(a) Realistic Distributions** | Non-uniform natural distribution of categories, priorities, sentiments, and amounts. | Normal/log-normal distribution for amounts; Poisson distribution for message counts per complaint. |
| **(b) Consistent IDs & Valid Joins**| Referential integrity score across PK/FK pairs. | 100% valid joins for baseline records; 0 unintended orphan keys. |
| **(c) Lifecycle Consistency** | State transition validation score. | 100% of transitions conform to the lifecycle finite state machine. |
| **(d) Derived Value Reconciliation**| Arithmetic and date delta verification. | Calculated totals (spent, paused minutes, SLA deadlines) reconcile with zero floating point drift. |
| **(e) Anomaly & Edge Case Coverage**| Recall of 6 injected negative scenarios. | Exactly 100% detection rate by `validate_dataset.py` matching ground truth records. |
| **(f) Ground Truth Isolation** | Zero-leakage verification. | Anomaly indicators and ground truth labels exist solely in `ground_truth.json` / `ground_truth.csv`. |
| **(g) Fixed-Seed Reproducibility**| SHA-256 dataset hash reproducibility across successive runs. | Identical checksums and identical row counts across 100% of generated tables. |
