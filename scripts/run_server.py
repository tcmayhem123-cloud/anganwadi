"""
Server launcher script for ACGMS.
Runs automated checks, generates WHO datasets if missing, seeds demo data,
and starts Uvicorn ASGI web server.
"""
import os
import sys
import uvicorn

# Add backend to python path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.rules.zscore import WHOReferenceStore
from app.rules.immunisation import ImmunisationScheduleStore
from app.database import Base, engine, SessionLocal
from app.seed.seeder import seed_database

def start():
    print("=" * 70)
    print("  Anganwadi / ICDS Child Growth Monitoring System (ACGMS)")
    print("  WHO Anthro Z-Score Engine & Malnutrition Surveillance Platform")
    print("=" * 70)

    # 1. Ensure reference datasets are loaded
    print("[1/3] Loading WHO Child Growth Standards & UIP Schedules...")
    WHOReferenceStore.ensure_loaded()
    ImmunisationScheduleStore.load()

    # 2. Initialize Database & Seed
    print("[2/3] Initializing Database & Verifying Seed Records...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

    # 3. Launch Server
    print("[3/3] Starting ACGMS Server at http://127.0.0.1:8000")
    print("  - Web Application:     http://127.0.0.1:8000/")
    print("  - Interactive API Doc: http://127.0.0.1:8000/docs")
    print("  - ReDoc Documentation: http://127.0.0.1:8000/redoc")
    print("=" * 70)

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, app_dir=backend_dir)

if __name__ == "__main__":
    start()
