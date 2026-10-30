"""
Database connection, session management, and automated JSON seed loader.
"""
import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.database.models import (
    Base, Customer, Product, Category, PriorityRule, Order,
    Complaint, ComplaintMessage, Assignment, SLAClock, Resolution,
    Survey, ComplaintEvent
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
DB_PATH = os.path.join(DATA_DIR, "yottaflex.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db_and_seed():
    """Initializes schema and populates SQLite database from generated JSON seeds if empty."""
    os.makedirs(DATA_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    try:
        # Check if already seeded
        if db.query(Customer).first() is not None:
            return

        json_dir = os.path.join(DATA_DIR, "json")
        if not os.path.exists(json_dir):
            print("[!] JSON seed directory not found. Skipping auto-seeding.")
            return

        print("[*] Seeding database from JSON files...")
        
        # 1. Master tables
        def load_json(name):
            p = os.path.join(json_dir, f"{name}.json")
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            return []

        categories = [Category(**r) for r in load_json("categories")]
        db.bulk_save_objects(categories)
        db.commit()

        priority_rules = [PriorityRule(**r) for r in load_json("priority_rules")]
        db.bulk_save_objects(priority_rules)
        db.commit()

        products = [Product(**r) for r in load_json("products")]
        db.bulk_save_objects(products)
        db.commit()

        customers = [Customer(**r) for r in load_json("customers")]
        db.bulk_save_objects(customers)
        db.commit()

        orders = [Order(**r) for r in load_json("orders")]
        db.bulk_save_objects(orders)
        db.commit()

        complaints = [Complaint(**r) for r in load_json("complaints")]
        db.bulk_save_objects(complaints)
        db.commit()

        messages = [ComplaintMessage(**r) for r in load_json("complaint_messages")]
        db.bulk_save_objects(messages)
        db.commit()

        assignments = [Assignment(**r) for r in load_json("assignments")]
        db.bulk_save_objects(assignments)
        db.commit()

        slas = [SLAClock(**r) for r in load_json("sla_clocks")]
        db.bulk_save_objects(slas)
        db.commit()

        resolutions = [Resolution(**r) for r in load_json("resolutions")]
        db.bulk_save_objects(resolutions)
        db.commit()

        surveys = [Survey(**r) for r in load_json("surveys")]
        db.bulk_save_objects(surveys)
        db.commit()

        events = [ComplaintEvent(**r) for r in load_json("complaint_events")]
        db.bulk_save_objects(events)
        db.commit()

        print("[+] Database initialized and seeded successfully.")
    except Exception as e:
        db.rollback()
        print(f"[!] Error seeding database: {e}")
    finally:
        db.close()

