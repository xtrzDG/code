"""
How big the perf dataset is (PERF_SCALE) and where results go (PERF_REPORT).

- `full`: the weekly run (.github/workflows/perf.yml): 500 businesses,
  2,000,000 messages, 200,000 bookings and 1,000 widget visitors;
- `medium`: a tenth of it, for a local check before a risky change;
- `small` (default): a quick local run that still pages and counts.
"""

import os
from dataclasses import dataclass

from app.schemas.dto.load_data import SeedLoadCommand


@dataclass(frozen=True)
class PerfScale:
    name: str
    businesses: int
    messages: int
    bookings: int
    visitors: int

    def command(self) -> SeedLoadCommand:
        return SeedLoadCommand.model_validate(
            {
                "business_count": self.businesses,
                "message_count": self.messages,
                "booking_count": self.bookings,
                "visitor_count": self.visitors,
            }
        )


SCALES: dict[str, PerfScale] = {
    scale.name: scale
    for scale in (
        PerfScale("full", 500, 2_000_000, 200_000, 1_000),
        PerfScale("medium", 50, 200_000, 20_000, 300),
        PerfScale("small", 10, 20_000, 2_000, 100),
    )
}


def read_scale() -> PerfScale:
    name: str = os.environ.get("PERF_SCALE", "small").strip() or "small"
    if name not in SCALES:
        raise ValueError(f"PERF_SCALE must be one of {sorted(SCALES)}, not {name!r}.")

    return SCALES[name]


def read_report_path() -> str | None:
    """Where the results JSON goes (scripts/perf_compare.py reads it)."""

    path: str = os.environ.get("PERF_REPORT", "").strip()
    return path or None
