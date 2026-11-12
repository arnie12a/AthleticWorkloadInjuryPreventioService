from collections import defaultdict
from datetime import datetime, timedelta, timezone


def calculate_hr_load(records, max_hr=190):
    """
    Calculate training load from heart-rate records.

    Uses time spent in HR zones with weights 1-5.
    """

    if max_hr <= 0:
        raise ValueError("max_hr must be positive")

    zone_minutes = defaultdict(float)

    valid_records = [
        record
        for record in records
        if record.timestamp is not None
        and record.heart_rate is not None
    ]

    valid_records.sort(
        key=lambda record: record.timestamp
    )

    for current, following in zip(
        valid_records,
        valid_records[1:]
    ):

        delta = (
            following.timestamp - current.timestamp
        ).total_seconds()

        # Skip duplicate timestamps and large recording gaps.
        if delta <= 0 or delta > 30:
            continue

        hr_fraction = current.heart_rate / max_hr

        if hr_fraction < 0.50:
            zone = 0
        elif hr_fraction < 0.60:
            zone = 1
        elif hr_fraction < 0.70:
            zone = 2
        elif hr_fraction < 0.80:
            zone = 3
        elif hr_fraction < 0.90:
            zone = 4
        else:
            zone = 5

        zone_minutes[zone] += delta / 60

    training_load = sum(
        zone * minutes
        for zone, minutes in zone_minutes.items()
    )

    return {
        "training_load": round(training_load, 2),
        "zone_minutes": {
            f"zone_{zone}": round(
                zone_minutes[zone], 2
            )
            for zone in range(6)
        },
        "covered_minutes": round(
            sum(zone_minutes.values()), 2
        )
    }


def calculate_workload_trends(workouts, as_of=None):
    """
    Compare the most recent 7 days against the
    preceding 28 days.

    The chronic value is averaged to a weekly load.
    """

    if as_of is None:
        as_of = datetime.now(timezone.utc).replace(
            tzinfo=None
        )

    acute_start = as_of - timedelta(days=7)
    chronic_start = as_of - timedelta(days=35)

    acute_load = 0.0
    chronic_load = 0.0

    for workout in workouts:

        if workout.start_time is None:
            continue

        workout_date = workout.start_time
        load = workout.training_load

        if load is None:
            continue

        if acute_start <= workout_date <= as_of:
            acute_load += load

        elif chronic_start <= workout_date < acute_start:
            chronic_load += load

    chronic_weekly_average = chronic_load / 4

    acwr = (
        acute_load / chronic_weekly_average
        if chronic_weekly_average > 0
        else None
    )

    return {
        "acute_7_day_load": round(acute_load, 2),
        "chronic_weekly_average": round(
            chronic_weekly_average, 2
        ),
        "acwr": (
            round(acwr, 2)
            if acwr is not None
            else None
        )
    }