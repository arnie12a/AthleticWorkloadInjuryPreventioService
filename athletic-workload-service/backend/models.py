import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class WorkoutDB(Base):
    __tablename__ = "workouts"
    training_load = Column(Float, nullable=True)
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True
    )

    filename = Column(String, nullable=False)

    file_hash = Column(
        String(64),
        nullable=False,
        unique=True
    )

    sport = Column(String, nullable=True)
    start_time = Column(DateTime, nullable=True)

    duration_seconds = Column(Float, nullable=True)
    distance_meters = Column(Float, nullable=True)

    avg_heart_rate = Column(Integer, nullable=True)
    max_heart_rate = Column(Integer, nullable=True)

    total_ascent = Column(Float, nullable=True)
    total_descent = Column(Float, nullable=True)

    calories = Column(Integer, nullable=True)

    # Calculated from heart-rate records
    training_load = Column(Float, nullable=True)

    records = relationship(
        "WorkoutRecordDB",
        back_populates="workout",
        cascade="all, delete-orphan"
    )


class WorkoutRecordDB(Base):
    __tablename__ = "workout_records"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    workout_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "workouts.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    timestamp = Column(DateTime, nullable=True)

    heart_rate = Column(Integer, nullable=True)

    altitude = Column(Float, nullable=True)
    speed = Column(Float, nullable=True)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    workout = relationship(
        "WorkoutDB",
        back_populates="records"
    )


class AthleteProfileDB(Base):
    __tablename__ = "athlete_profiles"

    user_id = Column(
        UUID(as_uuid=True),
        primary_key=True
    )

    max_heart_rate = Column(
        Integer,
        nullable=True
    )

    resting_heart_rate = Column(
        Integer,
        nullable=True
    )


class ProcessingJobDB(Base):
    __tablename__ = "processing_jobs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    filename = Column(
        String,
        nullable=False
    )

    status = Column(
        String,
        nullable=False,
        default="pending"
    )

    error_message = Column(
        String,
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True
    )
    
    workout_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workouts.id", ondelete="SET NULL"),
        nullable=True
    )

    attempt_count = Column(
        Integer,
        nullable=False,
        default=0
    )
