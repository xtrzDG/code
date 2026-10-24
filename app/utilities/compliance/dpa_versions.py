"""
Dated versions of the data processing agreement: owners who accepted an
earlier version accept a new one within 30 days of its date (DPA 15.2).
"""

import re
from datetime import date, timedelta

from app.schemas.typings.compliance.constrained_strings import (
    DpaAcceptanceDueDate,
    DpaDocumentVersion,
)

DPA_REACCEPTANCE_DAYS: int = 30
DATED_VERSION: re.Pattern[str] = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


def acceptance_due_on(version: DpaDocumentVersion) -> DpaAcceptanceDueDate | None:
    """
    The day owners accept `version` by, 30 days after its date
    ("2026-10-06" gives "2026-11-05"); None for a version not named by a
    date.
    """

    if DATED_VERSION.match(str(version)) is None:
        return None

    try:
        day: date = date.fromisoformat(str(version))
    except ValueError:
        return None

    return DpaAcceptanceDueDate(
        (day + timedelta(days=DPA_REACCEPTANCE_DAYS)).isoformat()
    )
