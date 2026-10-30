"""
Main FastAPI Application Entrypoint.
Initializes the SQLite database, exposes REST endpoints, and mounts the interactive Dashboard.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from src.database.session import init_db_and_seed
from src.api.routes import complaints, analytics

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database and auto-seed on startup
    init_db_and_seed()
    yield

app = FastAPI(
    title="YottaFlex Enterprise Complaint & SLA Management API",
    description="End-to-end complaint classification, dynamic priority routing, SLA clock state machine, and multi-actor traceability.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for external integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(complaints.router)
app.include_router(analytics.router)

# Mount Static Files for Dashboard
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", include_in_schema=False)
def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return RedirectResponse(url="/docs")

@app.get("/dashboard", include_in_schema=False)
def dashboard():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return RedirectResponse(url="/docs")

@app.get("/api/v1/health", tags=["System"])
def health_check():
    return {
        "status": "HEALTHY",
        "service": "YottaFlex Complaint & SLA Engine",
        "api_version": "1.0.0"
    }
