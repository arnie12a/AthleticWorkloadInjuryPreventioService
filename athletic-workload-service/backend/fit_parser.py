from io import BytesIO
from datetime import date, datetime

from fitparse import FitFile


def serialize_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, bytes):
        return value.hex()

    return value


def message_to_dict(message):
    return {
        field.name: serialize_value(field.value)
        for field in message
    }


def parse_fit_file(file_bytes: bytes):

    fitfile = FitFile(BytesIO(file_bytes))

    sessions = []
    records = []
    laps = []

    for message in fitfile.get_messages():

        if message.name == "session":
            sessions.append(message_to_dict(message))

        elif message.name == "record":
            records.append(message_to_dict(message))

        elif message.name == "lap":
            laps.append(message_to_dict(message))

    if not sessions:
        raise ValueError(
            "No workout sessions found in FIT file"
        )

    session = sessions[0]

    duration_seconds = session.get("total_timer_time")
    distance_meters = session.get("total_distance")

    summary = {
        "sport": session.get("sport"),
        "start_time": session.get("start_time"),
        "duration_seconds": duration_seconds,
        "duration_minutes": (
            round(duration_seconds / 60, 2)
            if duration_seconds is not None
            else None
        ),
        "distance_meters": distance_meters,
        "distance_km": (
            round(distance_meters / 1000, 2)
            if distance_meters is not None
            else None
        ),
        "avg_heart_rate": session.get("avg_heart_rate"),
        "max_heart_rate": session.get("max_heart_rate"),
        "avg_speed": session.get("avg_speed"),
        "calories": session.get("total_calories"),
        "total_ascent": session.get("total_ascent"),
        "total_descent": session.get("total_descent")
    }

    return {
        "summary": summary,
        "sessions": sessions,
        "records": records,
        "laps": laps,
        "total_records": len(records),
        "total_laps": len(laps)
    }