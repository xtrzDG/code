"""
The cabinet's Core Web Vitals per page and device: the database counts the
samples per value bucket, the 75th percentile is read from the buckets.
"""

from collections import defaultdict
from collections.abc import Sequence

from app.schemas.constants.analytics import DeviceClass, WebVitalName, WebVitalRating
from app.schemas.dto.analytics.admin_metrics_view import WebVitalView
from app.schemas.dto.analytics.web_vital_counts import WebVitalBucketCount
from app.schemas.typings.analytics.constrained_integers import (
    WebVitalPercentile,
    WebVitalSampleCount,
    WebVitalValue,
)
from app.schemas.typings.analytics.constrained_strings import CabinetRoutePattern

PERCENTILE: float = 0.75
# Bucket starts in each vital's unit; Google's thresholds are among them,
# so a rating never depends on where inside a bucket a value lies.
BUCKET_STARTS: dict[WebVitalName, tuple[int, ...]] = {
    WebVitalName.LCP: (
        0, 250, 500, 750, 1000, 1250, 1500, 1750, 2000, 2250, 2500, 3000,
        3500, 4000, 5000, 6000, 8000, 10000, 15000, 20000, 30000,
    ),
    WebVitalName.INP: (
        0, 25, 50, 75, 100, 125, 150, 175, 200, 250, 300, 350, 400, 500,
        600, 800, 1000, 1500, 2000, 3000, 5000,
    ),
    WebVitalName.CLS: (
        0, 100, 250, 500, 750, 1000, 1500, 2000, 2500, 3000, 4000, 5000,
        7500, 10000, 15000, 25000,
    ),
}  # fmt: skip
# (good up to, poor above) in the vital's unit (CLS in ten-thousandths).
THRESHOLDS: dict[WebVitalName, tuple[int, int]] = {
    WebVitalName.LCP: (2500, 4000),
    WebVitalName.INP: (200, 500),
    WebVitalName.CLS: (1000, 2500),
}


def bucket_starts(metric: WebVitalName) -> list[WebVitalValue]:
    return [WebVitalValue(start) for start in BUCKET_STARTS[metric]]


def percentile_of(
    counts: dict[int, int], starts: Sequence[int], fraction: float = PERCENTILE
) -> int:
    """
    The value below which `fraction` of the samples lie, interpolated inside
    its bucket; a value in the open last bucket reads as that bucket's start.
    """

    total: int = sum(counts.values())
    target: float = fraction * total
    seen: int = 0
    for index in sorted(counts):
        count: int = counts[index]
        if seen + count >= target and count > 0:
            lower: int = starts[index]
            if index + 1 >= len(starts):
                return lower
            upper: int = starts[index + 1]
            return round(lower + (target - seen) / count * (upper - lower))
        seen += count

    return starts[-1]


def rate(metric: WebVitalName, p75: int) -> WebVitalRating:
    good_up_to, poor_above = THRESHOLDS[metric]
    if p75 <= good_up_to:
        return WebVitalRating.GOOD
    if p75 > poor_above:
        return WebVitalRating.POOR
    return WebVitalRating.NEEDS_IMPROVEMENT


def build_web_vitals(
    metric: WebVitalName, buckets: Sequence[WebVitalBucketCount]
) -> list[WebVitalView]:
    """One row per page and device class, the busiest pages first."""

    grouped: dict[tuple[CabinetRoutePattern, DeviceClass], dict[int, int]] = (
        defaultdict(dict)
    )
    for bucket in buckets:
        cell = grouped[(bucket.route, bucket.device_class)]
        cell[int(bucket.bucket)] = cell.get(int(bucket.bucket), 0) + int(bucket.count)

    views: list[WebVitalView] = []
    for (route, device_class), counts in grouped.items():
        p75: int = percentile_of(counts, BUCKET_STARTS[metric])
        views.append(
            WebVitalView(
                metric=metric,
                route=route,
                device_class=device_class,
                p75=WebVitalPercentile(min(p75, 600_000)),
                samples=WebVitalSampleCount(sum(counts.values())),
                rating=rate(metric, p75),
            )
        )

    return sorted(
        views, key=lambda view: (-int(view.samples), str(view.route), view.device_class)
    )
