
from redis_client import redis_client

STREAM_NAME = "workout:jobs"
GROUP_NAME = "workout-workers"


def setup_consumer_group():
    try:
        redis_client.xgroup_create(
            STREAM_NAME,
            GROUP_NAME,
            id="0",
            mkstream=True
        )
    except Exception as exc:
        # BUSYGROUP means the group already exists.
        if "BUSYGROUP" not in str(exc):
            raise


def enqueue_workout(job_id):
    return redis_client.xadd(
        STREAM_NAME,
        {"job_id": str(job_id)}
    )
