from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.niches import NicheKey
from app.schemas.typings.analytics.constrained_strings import (
    AcquisitionSourceKey,
    MetricsDate,
)
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.users.prefixed_id import UserId


class AdminMetricsQuery(ImmutableDTO):
    """
    The founder's growth metrics (GET /v1/admin/metrics): sign-up days from
    `period_start` to `period_end` (UTC, both included; the last 90 days
    when left out), optionally only owners of one country, niche or
    acquisition source.
    """

    user_id: UserId
    period_start: MetricsDate | None = None
    period_end: MetricsDate | None = None
    country_code: CountryCode | None = None
    niche_key: NicheKey | None = None
    source: AcquisitionSourceKey | None = None
