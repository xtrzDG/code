from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.analytics import DeviceClass, WebVitalName, WebVitalRating
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.analytics.churn_views import ChurnView
from app.schemas.dto.analytics.growth_views import GrowthView
from app.schemas.dto.analytics.revenue_views import RevenueView
from app.schemas.typings.analytics.constrained_integers import (
    WebVitalPercentile,
    WebVitalSampleCount,
)
from app.schemas.typings.analytics.constrained_strings import (
    AcquisitionSourceKey,
    CabinetRoutePattern,
    MetricsDate,
)
from app.schemas.typings.localization.constrained_strings import CountryCode


class WebVitalView(ImmutableDTO):
    """
    The 75th percentile of one Core Web Vital on one cabinet page and kind
    of device in the period, with how many page views it rests on.
    """

    metric: WebVitalName
    route: CabinetRoutePattern
    device_class: DeviceClass
    p75: WebVitalPercentile
    samples: WebVitalSampleCount
    rating: WebVitalRating


class MetricsFilterChoices(ImmutableDTO):
    """The countries, niches and sources present, for the filter controls."""

    countries: list[CountryCode]
    niches: list[NicheKey]
    sources: list[AcquisitionSourceKey]


class AdminMetricsView(ImmutableDTO):
    """
    The founder's growth metrics of a period (UTC days, both included): the
    owners' funnel and what explains it, recurring revenue in euros, gross
    margin, why owners cancelled and what kept or brought them back
    (`churn`), and the cabinet's Web Vitals. First-party data only.
    """

    generated_at: Microseconds
    period_start: MetricsDate
    period_end: MetricsDate
    growth: GrowthView
    revenue: RevenueView
    web_vitals: list[WebVitalView]
    choices: MetricsFilterChoices
    churn: ChurnView = Field(default_factory=ChurnView)
