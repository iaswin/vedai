from django.core.cache import cache


TIMEOUT = 60 * 60


def save_assessment(session_id, data):
    cache.set(
        f"assessment:{session_id}",
        data,
        TIMEOUT,
    )


def get_assessment(session_id):
    return cache.get(
        f"assessment:{session_id}"
    )


def update_status(
    session_id,
    status,
    **extra
):
    data = get_assessment(
        session_id
    ) or {}

    data["status"] = status

    data.update(extra)

    save_assessment(
        session_id,
        data,
    )