"""Which generic request limit a signed-in request counts against."""

from app.schemas.constants.spend import RequestLimitClass

EXPORT_PATH_MARKERS: tuple[str, ...] = ("/export", "/business-exports/")


def limit_class_of(path: str) -> RequestLimitClass:
    """
    EXPORT for the routes that hand out data in bulk (the CSV exports, a
    customer's data, a segment's members, the full business export and its
    download), GENERAL for every other.
    """

    return (
        RequestLimitClass.EXPORT
        if any(marker in path for marker in EXPORT_PATH_MARKERS)
        else RequestLimitClass.GENERAL
    )
