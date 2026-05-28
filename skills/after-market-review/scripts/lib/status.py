OK = "ok"
PARTIAL = "partial"
UNAVAILABLE = "unavailable"
ERROR = "error"

VALID_STATUSES = {OK, PARTIAL, UNAVAILABLE, ERROR}


def layer_result(status: str, data: dict | None = None, errors: list[str] | None = None) -> dict:
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid layer status: {status}")
    return {
        "status": status,
        "data": data or {},
        "errors": errors or [],
    }
