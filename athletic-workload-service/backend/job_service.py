
from pathlib import Path
from uuid import UUID

from database import SessionLocal
from models import ProcessingJobDB

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads" / "pending"


def get_job_file(job_id):
    return UPLOAD_DIR / f"{job_id}.fit"


def update_job_status(job_id, status, error=None):
    db = SessionLocal()

    try:
        job = db.get(ProcessingJobDB, UUID(str(job_id)))

        if job is None:
            raise ValueError("Processing job not found")

        job.status = status
        job.error_message = error

        db.commit()

    finally:
        db.close()
