
import hashlib
import socket
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models import (
    ProcessingJobDB,
    WorkoutDB,
    WorkoutRecordDB,
    AthleteProfileDB
)
from fit_parser import parse_fit_file
from workload import calculate_hr_load
from redis_client import redis_client, invalidate_workload_cache
from queue_service import (
    STREAM_NAME,
    GROUP_NAME,
    setup_consumer_group
)
from job_service import get_job_file

CONSUMER_NAME = f"worker-{socket.gethostname()}"


def parse_timestamp(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ).replace(tzinfo=None)


def gps_degrees(value):
    if value is None:
        return None
    return float(value) * (180 / 2**31)


def process_job(job_id):
    db = SessionLocal()
    file_path = get_job_file(job_id)

    try:
        job = db.get(ProcessingJobDB, UUID(job_id))

        if job is None:
            raise ValueError("Job not found")

        if job.status == "completed":
            return

        job.status = "processing"
        db.commit()

        file_bytes = file_path.read_bytes()
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        existing = db.query(WorkoutDB).filter(
            WorkoutDB.user_id == job.user_id,
            WorkoutDB.file_hash == file_hash
        ).first()

        if existing:
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            file_path.unlink(missing_ok=True)
            return

        parsed = parse_fit_file(file_bytes)
        summary = parsed["summary"]

        workout = WorkoutDB(
            user_id=job.user_id,
            filename=job.filename,
            file_hash=file_hash,
            sport=summary.get("sport"),
            start_time=parse_timestamp(summary.get("start_time")),
            duration_seconds=summary.get("duration_seconds"),
            distance_meters=summary.get("distance_meters"),
            avg_heart_rate=summary.get("avg_heart_rate"),
            max_heart_rate=summary.get("max_heart_rate"),
            total_ascent=summary.get("total_ascent"),
            total_descent=summary.get("total_descent"),
            calories=summary.get("calories")
        )

        db.add(workout)
        db.flush()

        records = []

        for record in parsed["records"]:
            records.append(
                WorkoutRecordDB(
                    workout_id=workout.id,
                    timestamp=parse_timestamp(record.get("timestamp")),
                    heart_rate=record.get("heart_rate"),
                    altitude=record.get(
                        "enhanced_altitude",
                        record.get("altitude")
                    ),
                    speed=record.get(
                        "enhanced_speed",
                        record.get("speed")
                    ),
                    latitude=gps_degrees(record.get("position_lat")),
                    longitude=gps_degrees(record.get("position_long"))
                )
            )

        db.add_all(records)

        profile = db.get(AthleteProfileDB, job.user_id)

        if profile and profile.max_heart_rate:
            result = calculate_hr_load(
                records,
                max_hr=profile.max_heart_rate
            )

            if result["covered_minutes"] > 0:
                workout.training_load = result["training_load"]

        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)

        db.commit()

        invalidate_workload_cache(job.user_id)
        file_path.unlink(missing_ok=True)

        print(f"Completed job {job_id}")

    except Exception as exc:
        db.rollback()

        job = db.get(ProcessingJobDB, UUID(job_id))

        if job:
            job.status = "failed"
            job.error_message = str(exc)[:500]
            db.commit()

        print(f"Failed job {job_id}: {exc}")

    finally:
        db.close()


def run_worker():
    setup_consumer_group()

    print("Worker waiting for Garmin FIT jobs...")

    while True:
        messages = redis_client.xreadgroup(
            groupname=GROUP_NAME,
            consumername=CONSUMER_NAME,
            streams={STREAM_NAME: ">"},
            count=1,
            block=5000
        )

        for stream_name, entries in messages:
            for message_id, data in entries:
                job_id = data["job_id"]

                process_job(job_id)

                redis_client.xack(
                    STREAM_NAME,
                    GROUP_NAME,
                    message_id
                )


if __name__ == "__main__":
    run_worker()
