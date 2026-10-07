"""
Helpers of the founder's metrics: where an owner came from, the days a
period covers, the 75th percentile of bucketed Web Vitals and its rating,
and an empty funnel.
"""

import pytest

from app.schemas.constants.analytics import FunnelStep, WebVitalName, WebVitalRating
from app.schemas.domain.signup_attribution import SignupAttribution
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.analytics.constrained_strings import (
    LandingPath,
    MetricsDate,
    ReferralCode,
    ReferrerHost,
    SignupSourceTag,
    UtmSource,
)
from app.use_cases.admin.metrics.metrics_period import resolve_period
from app.utilities.analytics.acquisition_sources import (
    acquisition_source_of,
    normalize_source,
)
from app.utilities.analytics.funnel_math import (
    build_funnel,
    median_time_to_live,
    percent_of,
)
from app.utilities.analytics.web_vital_math import BUCKET_STARTS, percentile_of, rate
from tests.analytics.metric_events import DAY, at_day


@pytest.mark.parametrize(
    ("attribution", "source"),
    [
        (None, "unknown"),
        (SignupAttribution(), "direct"),
        (
            SignupAttribution(
                utm_source=UtmSource("Google Ads"),
                source_tag=SignupSourceTag("flyer"),
                referral_code=ReferralCode("p-1"),
            ),
            "google-ads",
        ),
        (
            SignupAttribution(
                source_tag=SignupSourceTag("flyer"),
                referral_code=ReferralCode("p-1"),
            ),
            "flyer",
        ),
        (
            SignupAttribution(
                referral_code=ReferralCode("p-1"),
                landing_path=LandingPath("/c/salobie-bia"),
            ),
            "referral",
        ),
        (
            SignupAttribution(
                landing_path=LandingPath("/c/salobie-bia"),
                referrer_host=ReferrerHost("www.instagram.com"),
            ),
            "hosted_chat",
        ),
        (
            SignupAttribution(referrer_host=ReferrerHost("www.instagram.com")),
            "instagram.com",
        ),
    ],
)
def test_the_most_specific_source_wins(
    attribution: SignupAttribution | None, source: str
) -> None:
    assert str(acquisition_source_of(attribution)) == source


def test_sources_are_normalized_keys() -> None:
    assert str(normalize_source("  Telegram Channel!! ")) == "telegram-channel"
    assert normalize_source("---") is None
    assert normalize_source(None) is None
    long_key = normalize_source("a" * 200)
    assert long_key is not None and len(str(long_key)) == 120


def test_the_default_period_is_the_last_90_days() -> None:
    period = resolve_period(None, None, at_day(44.5))

    assert (str(period.first_day), str(period.last_day)) == ("2026-07-18", "2026-10-15")
    assert int(period.end) - int(period.start) == 90 * DAY


def test_a_period_ends_after_its_last_day() -> None:
    period = resolve_period(
        MetricsDate("2026-09-01"), MetricsDate("2026-09-30"), at_day(44)
    )

    assert int(period.start) == int(at_day(0))
    assert int(period.end) == int(at_day(30))


@pytest.mark.parametrize(
    ("first", "last"),
    [
        ("2026-09-30", "2026-09-01"),
        ("2024-01-01", "2026-09-01"),
        ("2026-02-30", "2026-03-01"),
    ],
)
def test_impossible_periods_are_refused(first: str, last: str) -> None:
    with pytest.raises(ValidationFailedError):
        resolve_period(MetricsDate(first), MetricsDate(last), at_day(44))


def test_the_percentile_is_interpolated_inside_its_bucket() -> None:
    starts = BUCKET_STARTS[WebVitalName.INP]

    # Four samples in 100-125: the 75th percentile is three quarters in.
    assert percentile_of({4: 4}, starts) == 119
    # The open last bucket reads as its start.
    assert percentile_of({len(starts) - 1: 2}, starts) == starts[-1]
    assert percentile_of({}, starts) == starts[-1]


@pytest.mark.parametrize(
    ("metric", "p75", "rating"),
    [
        (WebVitalName.LCP, 2500, WebVitalRating.GOOD),
        (WebVitalName.LCP, 2501, WebVitalRating.NEEDS_IMPROVEMENT),
        (WebVitalName.LCP, 4001, WebVitalRating.POOR),
        (WebVitalName.INP, 200, WebVitalRating.GOOD),
        (WebVitalName.INP, 500, WebVitalRating.NEEDS_IMPROVEMENT),
        (WebVitalName.CLS, 1000, WebVitalRating.GOOD),
        (WebVitalName.CLS, 2600, WebVitalRating.POOR),
    ],
)
def test_ratings_follow_the_web_vitals_thresholds(
    metric: WebVitalName, p75: int, rating: WebVitalRating
) -> None:
    assert rate(metric, p75) is rating


def test_an_empty_funnel_has_no_shares() -> None:
    steps = build_funnel([])

    assert [step.step for step in steps] == list(FunnelStep)
    assert all(int(step.owners) == 0 for step in steps)
    assert all(step.share_of_sign_ups is None for step in steps)
    assert median_time_to_live([]) is None
    assert percent_of(1, 3) == 33.33
