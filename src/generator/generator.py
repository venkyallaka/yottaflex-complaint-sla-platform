"""
Synthetic Data Generation Engine for YottaFlex Complaint & SLA Management.
Generates master, transactional, and event entities with deterministic PRNG seeding.
"""
import os
import sys
import json
import csv
import hashlib
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional

from src.generator.rules import (
    CATEGORIES_DATA,
    PRIORITY_RULES_DATA,
    evaluate_priority,
    SLA_TARGET_MAP
)
from src.core.routing import determine_team_and_agent
from src.generator.anomalies import GroundTruthTracker

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Dorothy", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Edward", "Deborah", "Ronald", "Stephanie", "Timothy", "Rebecca", "Jason", "Sharon"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter"
]

PRODUCT_TEMPLATES = [
    ("Smart 4K Ultra TV 55-inch", "CAT-02", 549.99, False, 24),
    ("Ergonomic Mesh Office Chair", "CAT-02", 189.50, False, 12),
    ("Lithium Ion Power Drill 20V", "CAT-01", 129.99, True, 36),
    ("Active Noise Cancelling Headphones", "CAT-02", 219.00, False, 12),
    ("Stainless Steel Multi-Cooker", "CAT-01", 99.95, True, 24),
    ("Mechanical Gaming Keyboard", "CAT-08", 85.00, False, 12),
    ("Wireless Fast Charging Pad", "CAT-02", 29.99, False, 12),
    ("High-Pressure Espresso Machine", "CAT-01", 450.00, True, 24),
    ("Cordless Stick Vacuum Cleaner", "CAT-01", 279.99, True, 24),
    ("Smart Security Camera 1080p", "CAT-06", 69.99, False, 12),
    ("Portable Bluetooth Speaker", "CAT-02", 49.99, False, 12),
    ("Organic Cotton Bedding Sheet Set", "CAT-09", 75.00, False, 6),
    ("Professional Blender 1200W", "CAT-01", 149.99, True, 24),
    ("Compact Dehumidifier 30 Pint", "CAT-02", 189.99, False, 12),
    ("Digital Smart Door Lock", "CAT-06", 199.99, False, 24),
    ("USB-C Dual Display Docking Station", "CAT-10", 119.50, False, 12),
    ("True Wireless Fitness Earbuds", "CAT-02", 79.99, False, 12),
    ("Electric Standing Desk 55x28", "CAT-02", 349.00, False, 36),
    ("Smart Wi-Fi Thermostat", "CAT-10", 139.00, False, 24),
    ("Ceramic Nonstick Cookware Set", "CAT-02", 159.99, False, 12),
    ("Portable Power Bank 20000mAh", "CAT-01", 39.99, True, 12),
    ("Air Purifier HEPA H13", "CAT-02", 119.00, False, 24),
    ("Dual Dash Cam 4K Front & Rear", "CAT-10", 169.99, False, 12),
    ("Memory Foam Queen Mattress", "CAT-02", 699.00, False, 60),
    ("Waterproof Smart Fitness Tracker", "CAT-02", 59.99, False, 12)
]

SAMPLE_COMPLAINT_TEXTS = {
    "CAT-01": [
        "The battery started smoking and melting the casing during charging!",
        "The heating element threw sparks while boiling water. Major fire hazard.",
        "The cord has exposed wiring right at the power plug. Very dangerous.",
        "Unit overheating and emits burning plastic smell within 5 minutes of turning on."
    ],
    "CAT-02": [
        "The item arrived shattered in pieces inside the shipping box.",
        "The left channel has no sound at all out of the box. Completely defective.",
        "The assembly joint cracked on first use. Low quality materials.",
        "Screen has dead pixels and vertical lines across the center."
    ],
    "CAT-03": [
        "Order was marked delivered 4 days ago but nothing has arrived at my porch.",
        "Delivery is now two weeks past the guaranteed delivery date without tracking updates.",
        "Courier dumped the package in the rain on the sidewalk instead of under the porch.",
        "Tracking status has been stuck on 'Label Created' for 10 business days."
    ],
    "CAT-04": [
        "I was charged twice for the exact same order on my credit card statement.",
        "Promotion code 20OFF was valid but full price was charged at checkout.",
        "Unexpected renewal fee charged after I had already cancelled subscription.",
        "Sales tax was calculated at 18% instead of the local 6% rate."
    ],
    "CAT-05": [
        "Tracking shows returned parcel received at your warehouse 3 weeks ago, still no refund.",
        "Returned item was accepted but refund amount deducted a 30% restocking fee without notice.",
        "Customer portal gives error 500 whenever I try to generate a return shipping label.",
        "Refund was promised in 3-5 days, but it has been 20 days with no update."
    ],
    "CAT-06": [
        "Unauthorized login alert from unknown IP, unable to reset my password.",
        "Two-factor authentication code is never received on my verified mobile number.",
        "My shipping address was changed without my permission.",
        "Locked out of account with critical pending orders."
    ],
    "CAT-07": [
        "Representative on chat was extremely dismissive and abruptly disconnected.",
        "Agent promised a supervisor callback within 2 hours, nobody ever reached out.",
        "Transferred between 4 different departments with no one taking ownership.",
        "Staff refused to honor advertised store policy."
    ],
    "CAT-08": [
        "The box was missing power adapter and remote control.",
        "Hardware mounting screws and instruction manual were completely missing.",
        "Only received 1 out of 2 pairs included in the bundle.",
        "Cables specified on box packaging were absent from shipment."
    ],
    "CAT-09": [
        "Item received is bright red, whereas the website photo showed dark navy blue.",
        "Product listed as 100% leather is clearly synthetic faux vinyl.",
        "Dimensions stated on page are 24 inches, but actual product is only 16 inches.",
        "Advertised battery life is 10 hours, but actual lasts barely 90 minutes."
    ],
    "CAT-10": [
        "Mobile companion app crashes immediately upon opening on iOS 18.",
        "Firmware update failed mid-way and bricked the device completely.",
        "Sync fails with Bluetooth connection error code 0x8841.",
        "Device disconnects from Wi-Fi every 10 minutes and requires factory reset."
    ]
}

AGENT_POOL = [
    {"agent_id": f"AGT-{i:04d}", "name": f"Agent {i}", "team": "Tier 1 Support"} for i in range(1, 15)
] + [
    {"agent_id": f"AGT-{i:04d}", "name": f"Escalation Lead {i}", "team": "Safety & Regulatory Escalations"} for i in range(15, 22)
] + [
    {"agent_id": f"AGT-{i:04d}", "name": f"Finance Specialist {i}", "team": "Finance & Billing Ops"} for i in range(22, 28)
] + [
    {"agent_id": f"AGT-{i:04d}", "name": f"Logistics Handler {i}", "team": "Logistics & Fulfillment"} for i in range(28, 35)
]

APPROVER_POOL = [
    f"APP-{i:04d}" for i in range(1, 11)
]

class DatasetGenerator:
    def __init__(self, seed: int = 20261022, scale: float = 1.0):
        self.seed = seed
        self.scale = scale
        self.rng = random.Random(seed)
        self.ground_truth = GroundTruthTracker()
        
        self.num_customers = int(5000 * scale)
        self.num_orders = int(8000 * scale)
        self.num_complaints = int(2000 * scale)
        self.num_messages = int(6000 * scale)
        
        self.customers: List[Dict[str, Any]] = []
        self.products: List[Dict[str, Any]] = []
        self.categories: List[Dict[str, Any]] = CATEGORIES_DATA
        self.priority_rules: List[Dict[str, Any]] = PRIORITY_RULES_DATA
        self.orders: List[Dict[str, Any]] = []
        self.complaints: List[Dict[str, Any]] = []
        self.complaint_messages: List[Dict[str, Any]] = []
        self.assignments: List[Dict[str, Any]] = []
        self.sla_clocks: List[Dict[str, Any]] = []
        self.resolutions: List[Dict[str, Any]] = []
        self.surveys: List[Dict[str, Any]] = []
        self.complaint_events: List[Dict[str, Any]] = []
        self.anomaly_fixtures: List[Dict[str, Any]] = []
        
        self.base_time = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
        self.event_counter = 1

    def _next_event_id(self) -> str:
        eid = f"EVT-2026-{self.event_counter:07d}"
        self.event_counter += 1
        return eid

    def generate_all(self):
        self._generate_customers()
        self._generate_products()
        self._generate_orders()
        self._generate_complaints_and_downstream()
        self._inject_explicit_anomalies()
        return self

    def _generate_customers(self):
        print(f"[*] Generating {self.num_customers} customers...")
        tiers = ["STANDARD", "SILVER", "GOLD", "PLATINUM"]
        tier_weights = [0.65, 0.20, 0.10, 0.05]
        
        for i in range(1, self.num_customers + 1):
            cid = f"CUS-{i:06d}"
            fname = self.rng.choice(FIRST_NAMES)
            lname = self.rng.choice(LAST_NAMES)
            domain = self.rng.choice(["example.com", "mailhub.org", "inboxnet.io", "customerpost.com"])
            email = f"{fname.lower()}.{lname.lower()}{i}@{domain}"
            phone = f"+1{self.rng.randint(200, 999)}{self.rng.randint(1000000, 9999999)}"
            tier = self.rng.choices(tiers, weights=tier_weights, k=1)[0]
            is_vulnerable = self.rng.random() < 0.06
            account_age_days = self.rng.randint(30, 700)
            created_at = self.base_time + timedelta(days=account_age_days)
            
            self.customers.append({
                "customer_id": cid,
                "first_name": fname,
                "last_name": lname,
                "email": email,
                "phone": phone,
                "customer_tier": tier,
                "is_vulnerable": is_vulnerable,
                "account_created_at": created_at.isoformat()
            })

    def _generate_products(self):
        print(f"[*] Generating products catalog...")
        for i, (name, cat_id, price, safety, warranty) in enumerate(PRODUCT_TEMPLATES, 1):
            pid = f"PRD-{i:04d}"
            self.products.append({
                "product_id": pid,
                "product_name": name,
                "category_id": cat_id,
                "base_price": round(price, 2),
                "has_safety_hazard": safety,
                "warranty_months": warranty
            })
        for i in range(len(PRODUCT_TEMPLATES) + 1, 51):
            base_template = PRODUCT_TEMPLATES[(i - 1) % len(PRODUCT_TEMPLATES)]
            pid = f"PRD-{i:04d}"
            multiplier = self.rng.choice([1.1, 1.25, 0.85, 0.95, 1.5])
            price = round(base_template[2] * multiplier, 2)
            self.products.append({
                "product_id": pid,
                "product_name": f"{base_template[0]} (Pro Model v{i})",
                "category_id": base_template[1],
                "base_price": price,
                "has_safety_hazard": base_template[3],
                "warranty_months": base_template[4]
            })

    def _generate_orders(self):
        print(f"[*] Generating {self.num_orders} orders...")
        statuses = ["DELIVERED", "DELIVERED", "DELIVERED", "SHIPPED", "RETURNED", "CANCELLED"]
        
        for i in range(1, self.num_orders + 1):
            oid = f"ORD-2026-{i:06d}"
            customer = self.rng.choice(self.customers)
            product = self.rng.choice(self.products)
            
            cust_created = datetime.fromisoformat(customer["account_created_at"])
            order_delay_days = self.rng.randint(1, 90)
            order_date = cust_created + timedelta(days=order_delay_days, hours=self.rng.randint(1, 23))
            
            quantity = self.rng.choices([1, 2, 3, 4, 5], weights=[0.70, 0.18, 0.07, 0.03, 0.02])[0]
            shipping = 9.99 if product["base_price"] < 100.0 else 0.0
            order_amount = round((product["base_price"] * quantity) + shipping, 2)
            
            status = self.rng.choice(statuses)
            delivery_date = None
            if status in ["DELIVERED", "RETURNED"]:
                delivery_date = (order_date + timedelta(days=self.rng.randint(2, 6))).isoformat()
            
            self.orders.append({
                "order_id": oid,
                "customer_id": customer["customer_id"],
                "product_id": product["product_id"],
                "order_amount": order_amount,
                "order_status": status,
                "order_date": order_date.isoformat(),
                "delivery_date": delivery_date
            })

    def _generate_complaints_and_downstream(self):
        print(f"[*] Generating {self.num_complaints} complaints, messages, and lifecycle events...")
        channels = ["EMAIL", "WEB_PORTAL", "PHONE", "CHAT", "MOBILE_APP"]
        channel_weights = [0.40, 0.30, 0.15, 0.10, 0.05]
        
        # Sort orders chronologically to preserve temporal coherence
        sorted_orders = sorted(self.orders, key=lambda o: o["order_date"])
        
        # Build customer-to-orders index
        cust_to_orders: Dict[str, List[Dict[str, Any]]] = {}
        for o in sorted_orders:
            cust_to_orders.setdefault(o["customer_id"], []).append(o)
            
        customer_complaints: Dict[str, List[Dict[str, Any]]] = {}
        target_complaints = self.num_complaints
        
        for i in range(1, target_complaints + 1):
            cid = f"CMP-2026-{i:06d}"
            
            # Determine if this should be a repeat complaint (10% of complaints)
            eligible_repeat_custs = [c_id for c_id, cmps in customer_complaints.items() if len(cmps) > 0]
            make_repeat = (self.rng.random() < 0.10) and (len(eligible_repeat_custs) > 0)
            
            if make_repeat:
                customer_id = self.rng.choice(eligible_repeat_custs)
                prev_c = customer_complaints[customer_id][-1]
                prev_dt = datetime.fromisoformat(prev_c["created_at"])
                complaint_dt = prev_dt + timedelta(days=self.rng.randint(2, 20), hours=self.rng.randint(1, 8))
                is_repeat = True
                parent_id = prev_c["complaint_id"]
                # If customer has orders, attach an order 90% of the time
                cust_orders = cust_to_orders.get(customer_id, [])
                if cust_orders and self.rng.random() < 0.90:
                    order = self.rng.choice(cust_orders)
                    order_id = order["order_id"]
                    order_amount = order["order_amount"]
                    product = next(p for p in self.products if p["product_id"] == order["product_id"])
                else:
                    order_id = None
                    order_amount = 0.0
                    product = self.rng.choice(self.products)
            else:
                is_repeat = False
                parent_id = None
                # 90% of regular complaints have an order, 10% are general inquiries / missing orders
                has_order = self.rng.random() < 0.90
                if has_order:
                    order = self.rng.choice(sorted_orders)
                    customer_id = order["customer_id"]
                    order_id = order["order_id"]
                    order_amount = order["order_amount"]
                    product = next(p for p in self.products if p["product_id"] == order["product_id"])
                    order_dt = datetime.fromisoformat(order["order_date"])
                    if customer_id in customer_complaints and len(customer_complaints[customer_id]) > 0:
                        prev_c = customer_complaints[customer_id][-1]
                        prev_dt = datetime.fromisoformat(prev_c["created_at"])
                        complaint_dt = prev_dt + timedelta(days=self.rng.randint(35, 90), hours=self.rng.randint(1, 12))
                    else:
                        complaint_dt = order_dt + timedelta(days=self.rng.randint(1, 20), hours=self.rng.randint(1, 12))
                else:
                    customer = self.rng.choice(self.customers)
                    customer_id = customer["customer_id"]
                    order_id = None
                    order_amount = 0.0
                    product = self.rng.choice(self.products)
                    cust_dt = datetime.fromisoformat(customer["account_created_at"])
                    if customer_id in customer_complaints and len(customer_complaints[customer_id]) > 0:
                        prev_c = customer_complaints[customer_id][-1]
                        prev_dt = datetime.fromisoformat(prev_c["created_at"])
                        complaint_dt = prev_dt + timedelta(days=self.rng.randint(35, 90), hours=self.rng.randint(1, 12))
                    else:
                        complaint_dt = cust_dt + timedelta(days=self.rng.randint(5, 60), hours=self.rng.randint(1, 12))

            customer = next(c for c in self.customers if c["customer_id"] == customer_id)
            
            if product["has_safety_hazard"] and self.rng.random() < 0.35:
                cat_id = "CAT-01"
            else:
                cat_id = self.rng.choice(CATEGORIES_DATA)["category_id"]
                
            cat_meta = next(c for c in CATEGORIES_DATA if c["category_id"] == cat_id)
            is_safety_issue = cat_meta["is_safety_critical"] or (product["has_safety_hazard"] and cat_id in ["CAT-01", "CAT-02"])
            
            if is_safety_issue:
                sentiment = round(self.rng.uniform(-0.95, -0.60), 2)
                severity = "CRITICAL"
            else:
                sentiment = round(self.rng.uniform(-0.85, 0.10), 2)
                severity = cat_meta["default_severity"]
                
            channel = self.rng.choices(channels, weights=channel_weights)[0]
            
            eval_res = evaluate_priority(
                is_safety_issue=is_safety_issue,
                category_id=cat_id,
                is_vulnerable=customer["is_vulnerable"],
                sentiment_score=sentiment,
                order_amount=order_amount,
                is_repeat_complaint=is_repeat,
                severity=severity
            )
            priority = eval_res["priority"]
            rule_id = eval_res["matched_rule_id"]
            resp_hours = eval_res["target_response_hours"]
            resol_hours = eval_res["target_resolution_hours"]
            
            target_resp_dt = complaint_dt + timedelta(hours=resp_hours)
            target_resol_dt = complaint_dt + timedelta(hours=resol_hours)
            
            # Lifecycle status distribution
            # 50% CLOSED, 20% RESOLVED, 10% RESOLUTION_PENDING, 10% IN_INVESTIGATION, 5% PENDING_CUSTOMER, 3% ASSIGNED, 2% REOPENED
            status_roll = self.rng.random()
            if status_roll < 0.50:
                status = "CLOSED"
            elif status_roll < 0.70:
                status = "RESOLVED"
            elif status_roll < 0.80:
                status = "RESOLUTION_PENDING"
            elif status_roll < 0.90:
                status = "IN_INVESTIGATION"
            elif status_roll < 0.95:
                status = "PENDING_CUSTOMER"
            elif status_roll < 0.98:
                status = "ASSIGNED"
            else:
                status = "REOPENED"
                
            updated_dt = complaint_dt + timedelta(hours=self.rng.randint(1, 30))
            closed_dt = None
            if status == "CLOSED":
                closed_dt = (complaint_dt + timedelta(hours=self.rng.randint(6, 40))).isoformat()
                
            complaint_record = {
                "complaint_id": cid,
                "customer_id": customer_id,
                "order_id": order_id,
                "category_id": cat_id,
                "intake_channel": channel,
                "severity": severity,
                "priority": priority,
                "status": status,
                "sentiment_score": sentiment,
                "is_safety_issue": is_safety_issue,
                "is_repeat_complaint": is_repeat,
                "parent_complaint_id": parent_id,
                "created_at": complaint_dt.isoformat(),
                "updated_at": updated_dt.isoformat(),
                "closed_at": closed_dt
            }
            self.complaints.append(complaint_record)
            customer_complaints.setdefault(customer_id, []).append(complaint_record)
            
            self.ground_truth.record_classification(
                complaint_id=cid,
                true_category=cat_id,
                true_priority=priority,
                rule_applied=rule_id,
                is_safety=is_safety_issue,
                is_vulnerable=customer["is_vulnerable"]
            )
            
            # Event 1: CREATED
            self.complaint_events.append({
                "event_id": self._next_event_id(),
                "complaint_id": cid,
                "event_type": "CREATED",
                "actor_role": "BUSINESS_REQUESTER",
                "actor_id": customer_id,
                "event_payload": json.dumps({"intake_channel": channel, "severity": severity}),
                "created_at": complaint_dt.isoformat()
            })
            
            # 2. Assignment using shared priority-aware routing engine
            routing_info = determine_team_and_agent(category_id=cat_id, priority=priority)
            target_team = routing_info["team_name"]
            agent_id = routing_info["agent_id"]
            
            assign_dt = complaint_dt + timedelta(minutes=self.rng.randint(5, 45))
            asn_id = f"ASN-{cid}-001"
            self.assignments.append({
                "assignment_id": asn_id,
                "complaint_id": cid,
                "team_name": target_team,
                "agent_id": agent_id,
                "assigned_by": "SYS_AUTO_ROUTER",
                "assigned_at": assign_dt.isoformat(),
                "released_at": None
            })
            
            self.complaint_events.append({
                "event_id": self._next_event_id(),
                "complaint_id": cid,
                "event_type": "ASSIGNED",
                "actor_role": "SYSTEM_ADMIN",
                "actor_id": "SYS_AUTO_ROUTER",
                "event_payload": json.dumps({"team": target_team, "agent_id": agent_id, "priority": priority}),
                "created_at": assign_dt.isoformat()
            })
            
            # Messages
            # Msg 1: Customer initial filing
            msg_dt = complaint_dt
            cat_templates = SAMPLE_COMPLAINT_TEXTS.get(cat_id, ["Issue reported with product/service."])
            cust_body = self.rng.choice(cat_templates)
            
            self.complaint_messages.append({
                "message_id": f"MSG-{cid}-001",
                "complaint_id": cid,
                "sender_type": "CUSTOMER",
                "sender_id": customer_id,
                "channel": channel,
                "message_body": cust_body,
                "sentiment_score": sentiment,
                "timestamp": msg_dt.isoformat()
            })
            
            # Msg 2: Agent Response
            resp_lag_minutes = self.rng.randint(15, resp_hours * 55)
            if self.rng.random() < 0.08:
                resp_lag_minutes = int(resp_hours * 60 + self.rng.randint(10, 120))
            actual_resp_dt = complaint_dt + timedelta(minutes=resp_lag_minutes)
            
            agent_body = f"Hello {customer['first_name']}, thank you for reaching out. We have opened ticket {cid} to resolve this immediately."
            self.complaint_messages.append({
                "message_id": f"MSG-{cid}-002",
                "complaint_id": cid,
                "sender_type": "AGENT",
                "sender_id": agent_id,
                "channel": channel,
                "message_body": agent_body,
                "sentiment_score": 0.35,
                "timestamp": actual_resp_dt.isoformat()
            })
            
            # Msg 3: follow up
            if status in ["RESOLVED", "CLOSED", "PENDING_CUSTOMER", "RESOLUTION_PENDING", "REOPENED"]:
                m3_dt = actual_resp_dt + timedelta(hours=self.rng.randint(1, 5))
                self.complaint_messages.append({
                    "message_id": f"MSG-{cid}-003",
                    "complaint_id": cid,
                    "sender_type": "AGENT" if status in ["PENDING_CUSTOMER", "RESOLUTION_PENDING"] else "CUSTOMER",
                    "sender_id": agent_id if status in ["PENDING_CUSTOMER", "RESOLUTION_PENDING"] else customer_id,
                    "channel": channel,
                    "message_body": "Could you provide additional photos of the package?" if status == "PENDING_CUSTOMER" else ("Remedy proposal submitted for managerial approval." if status == "RESOLUTION_PENDING" else "Here is the requested information."),
                    "sentiment_score": -0.10 if status == "PENDING_CUSTOMER" else 0.05,
                    "timestamp": m3_dt.isoformat()
                })
            
            # SLA Clock
            paused_mins = 0
            paused_at_iso = None
            clock_status = "RUNNING"
            if status == "PENDING_CUSTOMER":
                clock_status = "PAUSED"
                paused_mins = self.rng.randint(60, 480)
                paused_at_iso = (complaint_dt + timedelta(hours=2)).isoformat()
            elif status in ["RESOLVED", "CLOSED"]:
                clock_status = "COMPLETED"
                if self.rng.random() < 0.25:
                    paused_mins = self.rng.randint(30, 240)
            elif status == "RESOLUTION_PENDING":
                clock_status = "RUNNING"
            
            actual_resol_dt = None
            is_resol_breached = False
            adjusted_target_resol_dt = target_resol_dt + timedelta(minutes=paused_mins)
            
            if status in ["RESOLVED", "CLOSED"]:
                if self.rng.random() < 0.90:
                    resol_mins = self.rng.randint(60, int(resol_hours * 60 * 0.9))
                else:
                    resol_mins = int(resol_hours * 60 + self.rng.randint(30, 300))
                actual_resol_dt = complaint_dt + timedelta(minutes=resol_mins + paused_mins)
                is_resol_breached = actual_resol_dt > adjusted_target_resol_dt
            
            is_resp_breached = actual_resp_dt > target_resp_dt
            if clock_status != "COMPLETED" and datetime.now(timezone.utc) > adjusted_target_resol_dt:
                is_resol_breached = True
                
            self.sla_clocks.append({
                "sla_id": f"SLA-{cid}",
                "complaint_id": cid,
                "target_response_time": target_resp_dt.isoformat(),
                "actual_response_time": actual_resp_dt.isoformat(),
                "target_resolution_time": adjusted_target_resol_dt.isoformat(),
                "actual_resolution_time": actual_resol_dt.isoformat() if actual_resol_dt else None,
                "clock_status": clock_status,
                "paused_at": paused_at_iso,
                "paused_duration_minutes": paused_mins,
                "is_response_breached": is_resp_breached,
                "is_resolution_breached": is_resol_breached
            })
            
            # Resolution & Approvals
            if status in ["RESOLVED", "CLOSED", "RESOLUTION_PENDING", "REOPENED"]:
                res_types = ["FULL_REFUND", "PARTIAL_CREDIT", "REPLACEMENT", "TECHNICAL_FIX", "PROCESS_APOLOGY"]
                res_type = self.rng.choice(res_types)
                root_causes = ["DEFECTIVE_PRODUCT", "LOGISTICS_DELAY", "BILLING_GLITCH", "USER_ERROR", "CARRIER_LOST"]
                root_cause = self.rng.choice(root_causes)
                
                comp_amount = 0.0
                if res_type == "FULL_REFUND":
                    comp_amount = order_amount if order_amount > 0 else 300.00
                elif res_type == "PARTIAL_CREDIT":
                    comp_amount = round((order_amount if order_amount > 0 else 200.00) * self.rng.uniform(0.15, 0.50), 2)
                    
                if status == "RESOLUTION_PENDING":
                    requires_appr = True
                    approver = None
                    appr_status = "PENDING_REVIEW"
                    res_time = (complaint_dt + timedelta(hours=3)).isoformat()
                elif status == "REOPENED":
                    requires_appr = (comp_amount > 250.00) or is_safety_issue
                    approver = self.rng.choice(APPROVER_POOL) if requires_appr else None
                    appr_status = "APPROVED" if requires_appr else "NOT_REQUIRED"
                    initial_resol_dt = complaint_dt + timedelta(hours=self.rng.randint(4, 20))
                    res_time = initial_resol_dt.isoformat()
                else:
                    requires_appr = (comp_amount > 250.00) or is_safety_issue
                    approver = self.rng.choice(APPROVER_POOL) if requires_appr else None
                    appr_status = "APPROVED" if requires_appr else "NOT_REQUIRED"
                    res_time = actual_resol_dt.isoformat() if actual_resol_dt else (complaint_dt + timedelta(hours=8)).isoformat()
                
                self.resolutions.append({
                    "resolution_id": f"RES-{cid}",
                    "complaint_id": cid,
                    "version": 1,
                    "resolution_type": res_type,
                    "root_cause": root_cause,
                    "compensation_amount": comp_amount,
                    "requires_approval": requires_appr,
                    "approver_id": approver,
                    "approval_status": appr_status,
                    "resolved_at": res_time,
                    "is_current": False if status == "REOPENED" else True
                })
                
                self.complaint_events.append({
                    "event_id": self._next_event_id(),
                    "complaint_id": cid,
                    "event_type": "RESOLUTION_APPROVED" if appr_status == "APPROVED" else "RESOLUTION_PROPOSED",
                    "actor_role": "APPROVER" if appr_status == "APPROVED" else "PROCESS_OWNER",
                    "actor_id": approver if approver else agent_id,
                    "event_payload": json.dumps({"version": 1, "resolution_type": res_type, "compensation": comp_amount, "approval_status": appr_status}),
                    "created_at": res_time
                })
                
                # If REOPENED status, record full sequence: RESOLVED -> CLOSED -> REOPENED -> IN_INVESTIGATION
                if status == "REOPENED":
                    initial_closed_dt = initial_resol_dt + timedelta(hours=self.rng.randint(1, 10))
                    self.complaint_events.append({
                        "event_id": self._next_event_id(),
                        "complaint_id": cid,
                        "event_type": "CLOSED",
                        "actor_role": "SYSTEM",
                        "actor_id": "AUTO_CLOSE_JOB",
                        "event_payload": json.dumps({"note": "Complaint settled and closed after initial resolution"}),
                        "created_at": initial_closed_dt.isoformat()
                    })
                    
                    reopen_dt = initial_closed_dt + timedelta(hours=self.rng.randint(6, 36))
                    self.complaint_events.append({
                        "event_id": self._next_event_id(),
                        "complaint_id": cid,
                        "event_type": "REOPENED",
                        "actor_role": "BUSINESS_REQUESTER",
                        "actor_id": customer_id,
                        "event_payload": json.dumps({"reason": "Issue persisted after initial settlement", "reopened_at": reopen_dt.isoformat()}),
                        "created_at": reopen_dt.isoformat()
                    })
                    
                    # Subsequent re-investigation event
                    reinvestigate_dt = reopen_dt + timedelta(minutes=15)
                    self.complaint_events.append({
                        "event_id": self._next_event_id(),
                        "complaint_id": cid,
                        "event_type": "IN_INVESTIGATION",
                        "actor_role": "SYSTEM",
                        "actor_id": "WORKFLOW_ENGINE",
                        "event_payload": json.dumps({"stage": "reopened_reinvestigation"}),
                        "created_at": reinvestigate_dt.isoformat()
                    })
                    
                    # Update reopened SLA clock target
                    target_reopen_resol_dt = reopen_dt + timedelta(hours=resol_hours)
                    sla_record = self.sla_clocks[-1]
                    sla_record["clock_status"] = "RUNNING"
                    sla_record["actual_resolution_time"] = None
                    sla_record["target_resolution_time"] = target_reopen_resol_dt.isoformat()
                    sla_record["paused_at"] = None
                    sla_record["paused_duration_minutes"] = 0
                    sla_record["is_resolution_breached"] = False
                
                # Survey (only for resolved/closed complaints with an actual resolution timestamp)
                if status in ["RESOLVED", "CLOSED"] and actual_resol_dt and self.rng.random() < 0.75:
                    srv_dt = actual_resol_dt + timedelta(hours=self.rng.randint(2, 24))
                    if not is_resol_breached:
                        csat = self.rng.choices([4, 5, 3], weights=[0.55, 0.35, 0.10])[0]
                        nps = self.rng.randint(8, 10)
                        effort = self.rng.randint(4, 5)
                    else:
                        csat = self.rng.choices([1, 2, 3], weights=[0.45, 0.35, 0.20])[0]
                        nps = self.rng.randint(1, 5)
                        effort = self.rng.randint(1, 2)
                        
                    self.surveys.append({
                        "survey_id": f"SRV-{cid}",
                        "complaint_id": cid,
                        "cycle": 1,
                        "csat_score": csat,
                        "nps_score": nps,
                        "effort_score": effort,
                        "feedback_comments": "Support handled everything efficiently." if csat >= 4 else "Resolution took longer than expected.",
                        "submitted_at": srv_dt.isoformat()
                    })

        # Top up complaint messages to hit exact target count (6,000)
        remaining_messages = self.num_messages - len(self.complaint_messages)
        if remaining_messages > 0:
            print(f"[*] Appending {remaining_messages} lifecycle messages to reach target message volume ({self.num_messages})...")
            for j in range(remaining_messages):
                cmp_target = self.complaints[j % len(self.complaints)]
                cid = cmp_target["complaint_id"]
                seq = sum(1 for m in self.complaint_messages if m["complaint_id"] == cid) + 1
                base_msg_dt = datetime.fromisoformat(cmp_target["updated_at"]) + timedelta(minutes=(j + 1) * 2)
                self.complaint_messages.append({
                    "message_id": f"MSG-{cid}-{seq:03d}",
                    "complaint_id": cid,
                    "sender_type": "SYSTEM" if j % 2 == 0 else "AGENT",
                    "sender_id": "SYS_AUTOMATION" if j % 2 == 0 else "AGT-0001",
                    "channel": cmp_target["intake_channel"],
                    "message_body": "Operational status update: case review logged." if j % 2 == 0 else "Follow-up status inquiry sent.",
                    "sentiment_score": 0.00,
                    "timestamp": base_msg_dt.isoformat()
                })

    def _inject_explicit_anomalies(self):
        """
        Injects the 6 labeled edge cases required by Step 5 and records them into GroundTruthTracker.
        Guarantees that each of the 6 anomalies is assigned to a mutually distinct entity.
        """
        print("[*] Injecting 6 explicit labeled negative scenarios / anomalies across distinct tickets...")
        
        # 1. ERR_ORPHAN_COMPLAINT: Complaint without valid customer
        # Keep operational complaint valid, store corrupted record in separate anomaly fixture
        orphan_candidate = self.complaints[10]
        original_customer = orphan_candidate["customer_id"]
        orphan_fixture = dict(orphan_candidate)
        orphan_fixture["customer_id"] = "CUS-999999"
        self.anomaly_fixtures.append(orphan_fixture)
        
        self.ground_truth.record_anomaly(
            anomaly_code="ERR_ORPHAN_COMPLAINT",
            entity_id=orphan_candidate["complaint_id"],
            entity_type="complaints",
            field_name="customer_id",
            injected_value="CUS-999999",
            expected_value=original_customer,
            notes="Injected non-existent customer ID in isolated anomaly test fixture to evaluate FK integrity without corrupting the operational DB."
        )

        # 2. ERR_TEMPORAL_INVERSION: Resolution before complaint
        res_target = self.resolutions[5]
        cmp_target_inv = next(c for c in self.complaints if c["complaint_id"] == res_target["complaint_id"])
        cmp_created_inv = datetime.fromisoformat(cmp_target_inv["created_at"])
        inversion_dt = (cmp_created_inv - timedelta(days=2)).isoformat()
        original_resolved_at = res_target["resolved_at"]
        res_target["resolved_at"] = inversion_dt
        self.ground_truth.record_anomaly(
            anomaly_code="ERR_TEMPORAL_INVERSION",
            entity_id=res_target["resolution_id"],
            entity_type="resolutions",
            field_name="resolved_at",
            injected_value=inversion_dt,
            expected_value=original_resolved_at,
            notes="Injected resolved_at timestamp 2 days before complaint created_at."
        )

        used_complaint_ids = {orphan_candidate["complaint_id"], cmp_target_inv["complaint_id"]}

        # 3. ERR_INVALID_SLA_PAUSE: SLA clock pauses incorrectly
        inv_candidate = next(c for c in self.complaints if c["status"] == "IN_INVESTIGATION" and c["complaint_id"] not in used_complaint_ids)
        sla_target = next(s for s in self.sla_clocks if s["complaint_id"] == inv_candidate["complaint_id"])
        original_clock_status = sla_target["clock_status"]
        sla_target["clock_status"] = "PAUSED"
        used_complaint_ids.add(inv_candidate["complaint_id"])
        self.ground_truth.record_anomaly(
            anomaly_code="ERR_INVALID_SLA_PAUSE",
            entity_id=sla_target["sla_id"],
            entity_type="sla_clocks",
            field_name="clock_status",
            injected_value="PAUSED",
            expected_value=original_clock_status,
            notes="SLA clock set to PAUSED while complaint status is IN_INVESTIGATION instead of PENDING_CUSTOMER."
        )

        # 4. ERR_UNLINKED_RECURRENCE: Repeat issue not linked (ensure distinct from others)
        rec_candidate = next(c for c in self.complaints if c["is_repeat_complaint"] and c["parent_complaint_id"] is not None and c["complaint_id"] not in used_complaint_ids)
        orig_parent = rec_candidate["parent_complaint_id"]
        rec_candidate["is_repeat_complaint"] = False
        rec_candidate["parent_complaint_id"] = None
        used_complaint_ids.add(rec_candidate["complaint_id"])
        self.ground_truth.record_anomaly(
            anomaly_code="ERR_UNLINKED_RECURRENCE",
            entity_id=rec_candidate["complaint_id"],
            entity_type="complaints",
            field_name="is_repeat_complaint",
            injected_value="False (parent=None)",
            expected_value=f"True (parent={orig_parent})",
            notes="Customer filed repeat complaint within 30 days but repeat flags were deliberately stripped."
        )

        # 5. ERR_SAFETY_PRIORITY_MISMATCH: Critical safety issue assigned to low-priority queue (distinct ticket)
        safety_candidate = next(c for c in self.complaints if c["is_safety_issue"] and c["complaint_id"] not in used_complaint_ids)
        orig_prio = safety_candidate["priority"]
        safety_candidate["priority"] = "P4_LOW"
        asn = next(a for a in self.assignments if a["complaint_id"] == safety_candidate["complaint_id"])
        asn["team_name"] = "General Support"
        used_complaint_ids.add(safety_candidate["complaint_id"])
        self.ground_truth.record_anomaly(
            anomaly_code="ERR_SAFETY_PRIORITY_MISMATCH",
            entity_id=safety_candidate["complaint_id"],
            entity_type="complaints",
            field_name="priority",
            injected_value="P4_LOW (Queue: General Support)",
            expected_value=f"{orig_prio} (Queue: Safety & Regulatory Escalations)",
            notes="Safety issue improperly assigned P4_LOW and routed to General Support."
        )

        # 6. ERR_PREMATURE_SURVEY: Survey before closure (choose distinct from temporal inversion and all others)
        survey_candidate = next(s for s in self.surveys if s["complaint_id"] not in used_complaint_ids)
        res_matching = next(r for r in self.resolutions if r["complaint_id"] == survey_candidate["complaint_id"])
        res_dt = datetime.fromisoformat(res_matching["resolved_at"])
        premature_dt = (res_dt - timedelta(hours=5)).isoformat()
        orig_survey_time = survey_candidate["submitted_at"]
        survey_candidate["submitted_at"] = premature_dt
        self.ground_truth.record_anomaly(
            anomaly_code="ERR_PREMATURE_SURVEY",
            entity_id=survey_candidate["survey_id"],
            entity_type="surveys",
            field_name="submitted_at",
            injected_value=premature_dt,
            expected_value=orig_survey_time,
            notes="Survey submitted 5 hours before formal complaint resolution."
        )

    def export_data(self, output_dir: str):
        os.makedirs(os.path.join(output_dir, "csv"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "json"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "sql"), exist_ok=True)
        
        tables = {
            "customers": self.customers,
            "products": self.products,
            "categories": self.categories,
            "priority_rules": self.priority_rules,
            "orders": self.orders,
            "complaints": self.complaints,
            "complaint_messages": self.complaint_messages,
            "assignments": self.assignments,
            "sla_clocks": self.sla_clocks,
            "resolutions": self.resolutions,
            "surveys": self.surveys,
            "complaint_events": self.complaint_events
        }
        
        manifest = {
            "seed": self.seed,
            "scale": self.scale,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "table_counts": {},
            "file_checksums": {}
        }
        
        for table_name, records in tables.items():
            if not records:
                continue
            csv_path = os.path.join(output_dir, "csv", f"{table_name}.csv")
            fieldnames = list(records[0].keys())
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(records)
            
            with open(csv_path, "rb") as f:
                checksum = hashlib.sha256(f.read()).hexdigest()
            manifest["table_counts"][table_name] = len(records)
            manifest["file_checksums"][f"csv/{table_name}.csv"] = checksum

        for table_name, records in tables.items():
            json_path = os.path.join(output_dir, "json", f"{table_name}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
            with open(json_path, "rb") as f:
                checksum = hashlib.sha256(f.read()).hexdigest()
            manifest["file_checksums"][f"json/{table_name}.json"] = checksum

        sql_path = os.path.join(output_dir, "sql", "seed_data.sql")
        with open(sql_path, "w", encoding="utf-8") as f:
            f.write("-- Synthetic Seed Data generated for YottaFlex Complaint Management Platform\n")
            f.write(f"-- Seed: {self.seed} | Scale: {self.scale}\n\n")
            for table_name, records in tables.items():
                if not records:
                    continue
                f.write(f"-- Table: {table_name} ({len(records)} rows)\n")
                fields = list(records[0].keys())
                field_list = ", ".join(fields)
                for r in records:
                    values = []
                    for k in fields:
                        val = r[k]
                        if val is None:
                            values.append("NULL")
                        elif isinstance(val, (int, float)):
                            values.append(str(val))
                        elif isinstance(val, bool):
                            values.append("1" if val else "0")
                        else:
                            clean_str = str(val).replace("'", "''")
                            values.append(f"'{clean_str}'")
                    val_str = ", ".join(values)
                    f.write(f"INSERT INTO {table_name} ({field_list}) VALUES ({val_str});\n")
                f.write("\n")
                
        with open(sql_path, "rb") as f:
            manifest["file_checksums"]["sql/seed_data.sql"] = hashlib.sha256(f.read()).hexdigest()

        gt_json_path = os.path.join(output_dir, "ground_truth.json")
        with open(gt_json_path, "w", encoding="utf-8") as f:
            json.dump({
                "anomalies": self.ground_truth.anomalies,
                "classification_ground_truth": self.ground_truth.classification_ground_truth
            }, f, indent=2)

        gt_csv_path = os.path.join(output_dir, "ground_truth.csv")
        if self.ground_truth.anomalies:
            with open(gt_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(self.ground_truth.anomalies[0].keys()))
                writer.writeheader()
                writer.writerows(self.ground_truth.anomalies)

        # Export isolated anomaly test fixtures
        anomalies_dir = os.path.join(output_dir, "anomalies")
        os.makedirs(anomalies_dir, exist_ok=True)
        if self.anomaly_fixtures:
            anomalies_path = os.path.join(anomalies_dir, "orphan_complaints.json")
            with open(anomalies_path, "w", encoding="utf-8") as f:
                json.dump(self.anomaly_fixtures, f, indent=2)

        manifest_path = os.path.join(output_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        print(f"[+] Generation & Export complete to {output_dir}")
        print(f"    Customers: {len(self.customers)} | Orders: {len(self.orders)}")
        print(f"    Complaints: {len(self.complaints)} | Messages: {len(self.complaint_messages)}")
        print(f"    Anomalies recorded in ground truth: {len(self.ground_truth.anomalies)}")
        return manifest
