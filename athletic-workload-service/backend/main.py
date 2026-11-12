import hashlib
from datetime import datetime
from uuid import UUID

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Depends
)

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import Base, engine, get_db
from models import (
    WorkoutDB,
    WorkoutRecordDB,
    AthleteProfileDB,
)
from models import ProcessingJobDB
from fit_parser import parse_fit_file
from auth import get_current_user


from workload import (
    calculate_hr_load,
    calculate_workload_trends
)

from schemas import AthleteProfileUpdate
from sqlalchemy import func

import json
from redis.exceptions import RedisError
from redis_client import redis_client

from redis_client import invalidate_workload_cache

from pathlib import Path
from uuid import uuid4
from redis.exceptions import RedisError

from models import ProcessingJobDB
from queue_service import enqueue_workout
from job_service import get_job_file

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Athletic Workload API",
    description="Garmin FIT-based workload analysis",
    version="1.0.0"
)

MAX_FILE_SIZE = 20 * 1024 * 1024

# Creates tables that do not already exist.
Base.metadata.create_all(bind=engine)


def parse_timestamp(value):

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.replace(tzinfo=None)

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ).replace(tzinfo=None)


def get_record_position(record, field):

    value = record.get(field)

    if value is None:
        return None

    # FIT GPS coordinates use semicircles.
    return float(value) * (180 / 2**31)


def workout_to_dict(workout):

    return {
        "id": str(workout.id),
        "filename": workout.filename,
        "sport": workout.sport,
        "start_time": workout.start_time,
        "duration_seconds": workout.duration_seconds,
        "distance_meters": workout.distance_meters,
        "avg_heart_rate": workout.avg_heart_rate,
        "max_heart_rate": workout.max_heart_rate,
        "total_ascent": workout.total_ascent,
        "total_descent": workout.total_descent,
        "calories": workout.calories,
        "training_load": workout.training_load
    }


@app.get("/")
def root():
    return {
        "message": "Athletic Workload API is running!"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/workouts/upload", status_code=201)
async def upload_workout(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    if (
        not file.filename
        or not file.filename.lower().endswith(".fit")
    ):
        raise HTTPException(
            status_code=400,
            detail="Only .fit files are supported"
        )

    file_bytes = await file.read(MAX_FILE_SIZE + 1)

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty"
        )

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="FIT file exceeds 20 MB"
        )

    file_hash = hashlib.sha256(
        file_bytes
    ).hexdigest()

    existing = db.query(WorkoutDB).filter(
        WorkoutDB.user_id == current_user["id"],
        WorkoutDB.file_hash == file_hash
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Workout already exists: {existing.id}"
        )

    try:
        parsed = parse_fit_file(file_bytes)

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Unable to parse FIT file"
        ) from exc

    summary = parsed["summary"]

    workout = WorkoutDB(
        user_id=current_user["id"],
        filename=file.filename,
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

    try:
        db.add(workout)
        db.flush()

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
                    latitude=get_record_position(
                        record,
                        "position_lat"
                    ),
                    longitude=get_record_position(
                        record,
                        "position_long"
                    )
                )
            )

        db.add_all(records)

        # Get the authenticated athlete's profile
        profile = db.get(
            AthleteProfileDB,
            current_user["id"]
        )

        # Calculate workload using the athlete's maximum HR
        if profile is not None and profile.max_heart_rate is not None:

            result = calculate_hr_load(
                records,
                max_hr=profile.max_heart_rate
            )

            if result["covered_minutes"] > 0:
                workout.training_load = result["training_load"]

        else:
            # Save the workout without calculating workload
            workout.training_load = None

        db.commit()
        invalidate_workload_cache(current_user["id"])
        db.refresh(workout)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Workout already exists"
        )

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to save workout"
        )

    return {
        "message": "Workout uploaded successfully",
        "workout_id": str(workout.id),
        "summary": workout_to_dict(workout),
        "training_load": workout.training_load,
        "total_records": len(records)
    }


@app.get("/workouts")
async def get_workouts(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workouts = (
        db.query(WorkoutDB)
        .filter(WorkoutDB.user_id == current_user["id"])
        .order_by(WorkoutDB.start_time.desc())
        .all()
    )

    return {
        "total": len(workouts),
        "workouts": [
            workout_to_dict(workout)
            for workout in workouts
        ]
    }


@app.get("/workouts/{workout_id}")
async def get_workout(
    workout_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    workout = db.query(WorkoutDB).filter(
        WorkoutDB.id == workout_id,
        WorkoutDB.user_id == current_user["id"]
    ).first()

    if workout is None:
        raise HTTPException(
            status_code=404,
            detail="Workout not found"
        )

    return workout_to_dict(workout)


@app.get("/workouts/{workout_id}/records")
async def get_workout_records(
    workout_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    workout = db.query(WorkoutDB).filter(
        WorkoutDB.id == workout_id,
        WorkoutDB.user_id == current_user["id"]
    ).first()

    if workout is None:
        raise HTTPException(
            status_code=404,
            detail="Workout not found"
        )

    records = db.query(WorkoutRecordDB).filter(
        WorkoutRecordDB.workout_id == workout_id
    ).order_by(
        WorkoutRecordDB.timestamp
    ).all()

    return {
        "workout_id": str(workout_id),
        "total_records": len(records),
        "records": [
            {
                "timestamp": record.timestamp,
                "heart_rate": record.heart_rate,
                "altitude": record.altitude,
                "speed": record.speed,
                "latitude": record.latitude,
                "longitude": record.longitude
            }
            for record in records
        ]
    }



@app.post("/analytics/calculate/{workout_id}")
async def calculate_workout_load(
    workout_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):

    # Step 1: Get the authenticated athlete's profile
    profile = db.get(
        AthleteProfileDB,
        current_user["id"]
    )

    if profile is None or profile.max_heart_rate is None:
        raise HTTPException(
            status_code=422,
            detail="Set your maximum heart rate in your profile first"
        )

    max_hr = profile.max_heart_rate

    # Step 2: Find the workout belonging to the current user
    workout = db.query(WorkoutDB).filter(
        WorkoutDB.id == workout_id,
        WorkoutDB.user_id == current_user["id"]
    ).first()

    if workout is None:
        raise HTTPException(
            status_code=404,
            detail="Workout not found"
        )

    # Step 3: Retrieve heart-rate records for this workout
    records = db.query(WorkoutRecordDB).filter(
        WorkoutRecordDB.workout_id == workout.id
    ).order_by(
        WorkoutRecordDB.timestamp
    ).all()

    # Step 4: Calculate heart-rate-based training load
    result = calculate_hr_load(
        records,
        max_hr=max_hr
    )

    # Step 5: Verify usable heart-rate data exists
    if result["covered_minutes"] == 0:
        raise HTTPException(
            status_code=422,
            detail="No usable heart-rate records"
        )

    # Step 6: Save calculated training load to PostgreSQL
    workout.training_load = result["training_load"]

    db.commit()
    invalidate_workload_cache(current_user["id"])
    db.refresh(workout)

    # Step 7: Return calculated workload
    return {
        "workout_id": str(workout.id),
        "max_hr_used": max_hr,
        **result
    }


@app.get("/analytics/trends")
async def get_training_trends(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = current_user["id"]

    cache_key = f"workload:trends:{user_id}"

    # Step 1: Check Redis
    try:
        cached = redis_client.get(cache_key)

        if cached is not None:
            return json.loads(cached)

    except RedisError:
        pass

    # Step 2: Calculate from PostgreSQL
    workouts = db.query(WorkoutDB).filter(
        WorkoutDB.user_id == user_id,
        WorkoutDB.training_load.isnot(None)
    ).all()

    result = calculate_workload_trends(workouts)

    # Step 3: Cache result for 5 minutes
    try:
        redis_client.setex(
            cache_key,
            300,
            json.dumps(result)
        )
    except RedisError:
        pass

    return result

@app.get("/auth/me")
async def get_my_profile(
    current_user=Depends(get_current_user)
):
    return {
        "id": str(current_user["id"]),
        "email": current_user["email"]
    }



@app.get("/users/me/profile")
async def get_athlete_profile(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = current_user["id"]

    profile = db.get(
        AthleteProfileDB,
        user_id
    )

    max_observed_hr = db.query(
        func.max(WorkoutDB.max_heart_rate)
    ).filter(
        WorkoutDB.user_id == user_id,
        WorkoutDB.max_heart_rate.between(100, 230)
    ).scalar()

    return {
        "user_id": str(user_id),
        "max_heart_rate": (
            profile.max_heart_rate
            if profile else None
        ),
        "resting_heart_rate": (
            profile.resting_heart_rate
            if profile else None
        ),
        "max_observed_heart_rate": max_observed_hr
    }



@app.patch("/users/me/profile")
async def update_athlete_profile(
    updates: AthleteProfileUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    user_id = current_user["id"]

    profile = db.get(
        AthleteProfileDB,
        user_id
    )

    if profile is None:
        profile = AthleteProfileDB(
            user_id=user_id
        )
        db.add(profile)

    update_data = updates.model_dump(
        exclude_unset=True
    )

    new_max = update_data.get(
        "max_heart_rate",
        profile.max_heart_rate
    )

    new_rest = update_data.get(
        "resting_heart_rate",
        profile.resting_heart_rate
    )

    if (
        new_max is not None
        and new_rest is not None
        and new_rest >= new_max
    ):
        raise HTTPException(
            status_code=422,
            detail="Resting HR must be below maximum HR"
        )

    max_hr_changed = (
        "max_heart_rate" in update_data
        and new_max != profile.max_heart_rate
    )

    for field, value in update_data.items():
        setattr(profile, field, value)

    # Existing workload values were calculated with
    # an older HR setting and should be recalculated.
    if max_hr_changed:
        db.query(WorkoutDB).filter(
            WorkoutDB.user_id == user_id
        ).update(
            {WorkoutDB.training_load: None},
            synchronize_session=False
        )

    db.commit()
    invalidate_workload_cache(current_user["id"])
    db.refresh(profile)

    return {
        "message": "Profile updated successfully",
        "user_id": str(profile.user_id),
        "max_heart_rate": profile.max_heart_rate,
        "resting_heart_rate": profile.resting_heart_rate,
        "workloads_need_recalculation": max_hr_changed
    }



@app.post("/workouts/upload-async", status_code=202)
async def upload_workout_async(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if not file.filename or not file.filename.lower().endswith(".fit"):
        raise HTTPException(
            status_code=400,
            detail="Only FIT files are supported"
        )

    file_bytes = await file.read(MAX_FILE_SIZE + 1)

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty"
        )

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="FIT file exceeds 20 MB"
        )

    job_id = uuid4()

    file_path = get_job_file(job_id)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Store the FIT file for the background worker.
    file_path.write_bytes(file_bytes)

    job = ProcessingJobDB(
        id=job_id,
        user_id=current_user["id"],
        filename=file.filename,
        status="pending"
    )

    try:
        db.add(job)
        db.commit()

    except Exception:
        db.rollback()
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create processing job"
        )

    try:
        enqueue_workout(job_id)

    except RedisError:
        # The job remains pending for recovery.
        raise HTTPException(
            status_code=503,
            detail="Job saved, but queue unavailable"
        )

    return {
        "message": "Workout queued for processing",
        "job_id": str(job_id),
        "status": "pending"
    }


@app.get("/jobs/{job_id}")
async def get_processing_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    job = db.query(ProcessingJobDB).filter(
        ProcessingJobDB.id == job_id,
        ProcessingJobDB.user_id == current_user["id"]
    ).first()

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    return {
        "job_id": str(job.id),
        "filename": job.filename,
        "status": job.status,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "completed_at": job.completed_at
    }

