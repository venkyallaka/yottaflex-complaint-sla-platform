"""
Database connection, session management, and automated JSON seed loader.
"""
import os
import json
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from src.database.models import (
    Base, Customer, Product, Category, PriorityRule, Order,
    Complaint, ComplaintMessage, Assignment, SLAClock, Resolution,
    Survey, ComplaintEvent
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
DB_PATH = os.path.join(DATA_DIR, "yottaflex.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args
)

# Enable Foreign Key enforcement for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db_and_seed():
    """Initializes schema and populates SQLite database from generated JSON seeds if empty.
    
    Ensures referential integrity by separating valid operational records from 
    deliberately corrupted anomaly test fixtures, preserving foreign key enforcement.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    try:
        # Check if already seeded
        if db.query(Customer).first() is not None:
            return

        json_dir = os.path.join(DATA_DIR, "json")
        anomalies_dir = os.path.join(DATA_DIR, "anomalies")
        os.makedirs(anomalies_dir, exist_ok=True)
        
        if not os.path.exists(json_dir):
            print("[!] JSON seed directory not found. Skipping auto-seeding.")
            return

        print("[*] Seeding operational database from JSON seeds (with strict FK enforcement)...")
        
        def load_json(name):
            p = os.path.join(json_dir, f"{name}.json")
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            return []

        # 1. Master tables
        categories_data = load_json("categories")
        categories = [Category(**r) for r in categories_data]
        valid_cat_ids = {c["category_id"] for c in categories_data}
        db.bulk_save_objects(categories)

        priority_rules_data = load_json("priority_rules")
        priority_rules = [PriorityRule(**r) for r in priority_rules_data]
        db.bulk_save_objects(priority_rules)

        products_data = load_json("products")
        products = [Product(**r) for r in products_data]
        valid_prod_ids = {p["product_id"] for p in products_data}
        db.bulk_save_objects(products)

        customers_data = load_json("customers")
        customers = [Customer(**r) for r in customers_data]
        valid_cust_ids = {c["customer_id"] for c in customers_data}
        db.bulk_save_objects(customers)

        orders_data = load_json("orders")
        orders = [Order(**r) for r in orders_data if r.get("customer_id") in valid_cust_ids and r.get("product_id") in valid_prod_ids]
        valid_order_ids = {o.order_id for o in orders}
        db.bulk_save_objects(orders)

        # 2. Complaints: separate valid operational complaints from orphan anomaly test fixtures
        raw_complaints = load_json("complaints")
        valid_complaint_dicts = []
        orphan_complaint_dicts = []
        
        for c_dict in raw_complaints:
            if c_dict.get("customer_id") in valid_cust_ids and c_dict.get("category_id") in valid_cat_ids:
                valid_complaint_dicts.append(c_dict)
            else:
                orphan_complaint_dicts.append(c_dict)
                
        if orphan_complaint_dicts:
            orphan_path = os.path.join(anomalies_dir, "orphan_complaints.json")
            with open(orphan_path, "w", encoding="utf-8") as f:
                json.dump(orphan_complaint_dicts, f, indent=2)
            print(f"[*] Quarantined {len(orphan_complaint_dicts)} deliberate orphan complaint(s) to {orphan_path} to preserve SQLite FK integrity.")

        complaints = [Complaint(**r) for r in valid_complaint_dicts]
        valid_cmp_ids = {c.complaint_id for c in complaints}
        db.bulk_save_objects(complaints)

        # 3. Dependent transactional / operational child records
        messages_data = [r for r in load_json("complaint_messages") if r.get("complaint_id") in valid_cmp_ids]
        messages = [ComplaintMessage(**r) for r in messages_data]
        db.bulk_save_objects(messages)

        assignments_data = [r for r in load_json("assignments") if r.get("complaint_id") in valid_cmp_ids]
        assignments = [Assignment(**r) for r in assignments_data]
        db.bulk_save_objects(assignments)

        sla_data = [r for r in load_json("sla_clocks") if r.get("complaint_id") in valid_cmp_ids]
        slas = [SLAClock(**r) for r in sla_data]
        db.bulk_save_objects(slas)

        resolutions_data = [r for r in load_json("resolutions") if r.get("complaint_id") in valid_cmp_ids]
        resolutions = [Resolution(**r) for r in resolutions_data]
        db.bulk_save_objects(resolutions)

        surveys_data = [r for r in load_json("surveys") if r.get("complaint_id") in valid_cmp_ids]
        surveys = [Survey(**r) for r in surveys_data]
        db.bulk_save_objects(surveys)

        events_data = [r for r in load_json("complaint_events") if r.get("complaint_id") in valid_cmp_ids]
        events = [ComplaintEvent(**r) for r in events_data]
        db.bulk_save_objects(events)

        # Single atomic commit for entire seeding process
        db.commit()
        print("[+] Operational database seeded successfully with 100% referential integrity.")
    except Exception as e:
        db.rollback()
        print(f"[!] Error seeding database: {e}")
        raise e
    finally:
        db.close()

