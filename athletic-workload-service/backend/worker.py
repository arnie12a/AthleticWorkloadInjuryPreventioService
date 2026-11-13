
import hashlib
import socket
import time
from datetime import datetime, timezone
from uuid import UUID, uuid4

from redis.exceptions import RedisError
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
from redis_client import (
    redis_client,
    invalidate_workload_cache
)
from queue_service import (
    STREAM_NAME,
    GROUP_NAME,
    setup_consumer_group
)
from job_service import get_job_file


# --------------------------------------------------
# Worker configuration
# --------------------------------------------------

CONSUMER_NAME = f"worker-{socket.gethostname()}-{uuid4().hex[:8]}"

MAX_RETRIES = 3

# A message must be idle for 60 seconds before
# another worker can reclaim it.
RECOVERY_IDLE_MS = 60000

# Check for abandoned messages every 10 seconds.
RECOVERY_INTERVAL_SECONDS = 10

# Wait up to 5 seconds for new Redis messages.
READ_BLOCK_MS = 5000


# --------------------------------------------------
# Helper functions
# --------------------------------------------------

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


def now_utc():
    return datetime.now(timezone.utc)


# --------------------------------------------------
# Process a Garmin FIT job
# --------------------------------------------------

def process_job(job_id):
    """
    Process a Garmin FIT file.

    Returns True when the job reaches a durable
    terminal state (completed or failed).

    Returns False when processing should be retried.

    Raises if PostgreSQL cannot safely record
    the job's state.
    """

    db = SessionLocal()
    file_path = get_job_file(job_id)

    try:
        job = db.get(
            ProcessingJobDB,
            UUID(str(job_id))
        )

        if job is None:
            raise ValueError(
                f"Processing job {job_id} not found"
            )

        # Idempotency: do not process completed jobs again.
        if job.status == "completed":
            print(f"Job {job_id} already completed")
            return True

        if job.status == "failed":
            print(f"Job {job_id} already failed")
            return True

        # Increment attempts before processing.
        job.attempt_count = (job.attempt_count or 0) + 1
        job.status = "processing"
        job.error_message = None

        db.commit()

        print(
            f"Processing job {job_id} "
            f"(attempt {job.attempt_count}/{MAX_RETRIES})"
        )

        # Read the stored FIT file.
        file_bytes = file_path.read_bytes()

        file_hash = hashlib.sha256(
            file_bytes
        ).hexdigest()

        # Check for duplicate workouts belonging
        # to the same authenticated athlete.
        existing = db.query(WorkoutDB).filter(
            WorkoutDB.user_id == job.user_id,
            WorkoutDB.file_hash == file_hash
        ).first()

        if existing:
            job.workout_id = existing.id
            job.status = "completed"
            job.completed_at = now_utc()
            job.error_message = None

            db.commit()

            file_path.unlink(missing_ok=True)

            print(
                f"Job {job_id} completed: "
                f"existing workout {existing.id}"
            )

            return True

        # Parse Garmin FIT file.
        parsed = parse_fit_file(file_bytes)
        summary = parsed["summary"]

        # Create workout summary.
        workout = WorkoutDB(
            user_id=job.user_id,
            filename=job.filename,
            file_hash=file_hash,
            sport=summary.get("sport"),
            start_time=parse_timestamp(
                summary.get("start_time")
            ),
            duration_seconds=summary.get(
                "duration_seconds"
            ),
            distance_meters=summary.get(
                "distance_meters"
            ),
            avg_heart_rate=summary.get(
                "avg_heart_rate"
            ),
            max_heart_rate=summary.get(
                "max_heart_rate"
            ),
            total_ascent=summary.get(
                "total_ascent"
            ),
            total_descent=summary.get(
                "total_descent"
            ),
            calories=summary.get("calories")
        )

        db.add(workout)
        db.flush()

        # Convert Garmin sensor measurements
        # into PostgreSQL records.
        records = []

        for record in parsed["records"]:
            records.append(
                WorkoutRecordDB(
                    workout_id=workout.id,
                    timestamp=parse_timestamp(
                        record.get("timestamp")
                    ),
                    heart_rate=record.get(
                        "heart_rate"
                    ),
                    altitude=record.get(
                        "enhanced_altitude",
                        record.get("altitude")
                    ),
                    speed=record.get(
                        "enhanced_speed",
                        record.get("speed")
                    ),
                    latitude=gps_degrees(
                        record.get("position_lat")
                    ),
                    longitude=gps_degrees(
                        record.get("position_long")
                    )
                )
            )

        db.add_all(records)

        # Retrieve personalized athlete settings.
        profile = db.get(
            AthleteProfileDB,
            job.user_id
        )

        # Calculate heart-rate-based workload.
        if profile and profile.max_heart_rate:
            result = calculate_hr_load(
                records,
                max_hr=profile.max_heart_rate
            )

            if result["covered_minutes"] > 0:
                workout.training_load = result[
                    "training_load"
                ]

        # Record successful processing.
        job.workout_id = workout.id
        job.status = "completed"
        job.completed_at = now_utc()
        job.error_message = None

        # Save workout, sensor records, and job
        # completion in one transaction.
        db.commit()

        # Cache invalidation and file cleanup.
        # These must not undo a committed workout.
        try:
            invalidate_workload_cache(job.user_id)
        except Exception as exc:
            print(f"Cache invalidation warning: {exc}")

        try:
            file_path.unlink(missing_ok=True)
        except OSError as exc:
            print(f"File cleanup warning: {exc}")

        print(
            f"Completed job {job_id} "
            f"-> workout {workout.id}"
        )

        return True

    except Exception as exc:
        db.rollback()

        print(f"Error processing job {job_id}: {exc}")

        # Persist failure/retry state.
        # If this fails, raise so Redis is not ACKed.
        try:
            job = db.get(
                ProcessingJobDB,
                UUID(str(job_id))
            )

            if job is None:
                raise RuntimeError(
                    f"Cannot persist status: job {job_id} missing"
                )

            job.error_message = str(exc)[:500]

            if (job.attempt_count or 0) >= MAX_RETRIES:
                job.status = "failed"
                job.completed_at = now_utc()

                db.commit()

                print(
                    f"Job {job_id} permanently failed "
                    f"after {job.attempt_count} attempts"
                )

                return True

            job.status = "pending"
            db.commit()

            print(
                f"Job {job_id} will be retried "
                f"after the recovery idle period"
            )

            return False

        except Exception:
            db.rollback()
            raise

    finally:
        db.close()


# --------------------------------------------------
# Handle a Redis Stream message
# --------------------------------------------------

def handle_message(message_id, data):
    job_id = data.get("job_id")

    if not job_id:
        print(
            f"Message {message_id} has no job_id; "
            "leaving unacknowledged for inspection"
        )
        return

    try:
        terminal = process_job(job_id)

        if terminal:
            # Acknowledge only completed or durably
            # failed jobs.
            redis_client.xack(
                STREAM_NAME,
                GROUP_NAME,
                message_id
            )

            print(
                f"Acknowledged Redis message {message_id}"
            )

        else:
            # Leave pending for future recovery.
            print(
                f"Message {message_id} remains pending"
            )

    except Exception as exc:
        print(
            f"Could not finalize job {job_id}: {exc}"
        )

        # Do not acknowledge the message.
        # Redis retains it in the pending list.


# --------------------------------------------------
# Recover abandoned Redis messages
# --------------------------------------------------

def recover_pending_jobs():
    """
    Recover messages left pending by crashed workers.

    Uses Redis XAUTOCLAIM to transfer ownership of
    messages idle longer than RECOVERY_IDLE_MS.
    """

    cursor = "0-0"

    while True:
        result = redis_client.xautoclaim(
            name=STREAM_NAME,
            groupname=GROUP_NAME,
            consumername=CONSUMER_NAME,
            min_idle_time=RECOVERY_IDLE_MS,
            start_id=cursor,
            count=10
        )

        cursor = result[0]
        messages = result[1]

        for message_id, data in messages:
            print(
                f"Recovered pending message {message_id}"
            )

            handle_message(message_id, data)

        if cursor == "0-0":
            break


# --------------------------------------------------
# Main worker loop
# --------------------------------------------------

def run_worker():
    setup_consumer_group()

    print("Worker waiting for Garmin FIT jobs...")
    print(f"Consumer: {CONSUMER_NAME}")
    print(
        f"Crash recovery enabled "
        f"(idle threshold: {RECOVERY_IDLE_MS / 1000:.0f}s)"
    )

    last_recovery = 0.0

    while True:
        try:
            # Periodically recover abandoned messages.
            if (
                time.monotonic() - last_recovery
                >= RECOVERY_INTERVAL_SECONDS
            ):
                recover_pending_jobs()
                last_recovery = time.monotonic()

            # Read newly queued jobs.
            messages = redis_client.xreadgroup(
                groupname=GROUP_NAME,
                consumername=CONSUMER_NAME,
                streams={STREAM_NAME: ">"},
                count=1,
                block=READ_BLOCK_MS
            )

            for stream_name, entries in messages:
                for message_id, data in entries:
                    handle_message(message_id, data)

        except RedisError as exc:
            print(f"Redis connection error: {exc}")
            print("Retrying connection in 5 seconds...")
            time.sleep(5)

        except Exception as exc:
            print(f"Unexpected worker error: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    run_worker()
