"""
ACGMS FastAPI Backend Application Entrypoint.
Mounts REST APIs, mounts static PWA frontend, configures CORS, and seeds test data on launch.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import engine, Base, SessionLocal
from .seed.seeder import seed_database
from .api import (
    auth, master, children, measurements, immunisation,
    alerts, visits, dashboards, exports, sync
)

# Initialize database schema
Base.metadata.create_all(bind=engine)

# Seed sample data on first run
db = SessionLocal()
try:
    seed_database(db)
finally:
    db.close()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Anganwadi / ICDS Child Growth Monitoring System (ACGMS) - WHO Z-Score & Malnutrition Surveillance Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register versioned API routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(master.router, prefix="/api/v1")
app.include_router(children.router, prefix="/api/v1")
app.include_router(measurements.router, prefix="/api/v1")
app.include_router(immunisation.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(visits.router, prefix="/api/v1")
app.include_router(dashboards.router, prefix="/api/v1")
app.include_router(exports.router, prefix="/api/v1")
app.include_router(sync.router, prefix="/api/v1")

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "HEALTHY",
        "system": settings.APP_NAME,
        "version": settings.VERSION,
        "who_standards": "WHO_2006_2007",
        "uip_schedule": "MoHFW_UIP_2024"
    }

# Mount static frontend directory
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
