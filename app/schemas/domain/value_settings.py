from base_pydantic_schemas import BaseDocument

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.value.booleans import (
    IsDailyDigestOn,
    IsMonthlyReportOn,
    IsWeeklyDigestOn,
)
from app.schemas.typings.value.constrained_integers import AverageCheckMinor
from app.schemas.typings.value.prefixed_id import DigestPreferencesId, ValueSettingsId


class ValueSettingsDocument(BaseDocument):
    """
    How the value of a business is estimated (one document per business,
    the id derived from it): `average_check_minor`, what one booking (or
    order) brings on average in minor units of the business currency, as
    the owner set it. Without it the typical check of the niche is used
    when one is known in the business currency.

    Kept apart from the business profile on purpose: the profile is what
    the assistant knows, and changing it asks for the assistant to be
    applied again; the average check is never shown to the assistant.
    """

    id: ValueSettingsId
    business_id: BusinessId
    average_check_minor: AverageCheckMinor | None = None


class DigestPreferencesDocument(BaseDocument):
    """
    Which summaries one owner of a business gets by e-mail and on their
    devices (one document per business and user, the id derived from
    them). Without a document: the weekly digest and the monthly report,
    no daily digest.
    """

    id: DigestPreferencesId
    business_id: BusinessId
    user_id: UserId
    is_daily_digest_on: IsDailyDigestOn = False
    is_weekly_digest_on: IsWeeklyDigestOn = True
    is_monthly_report_on: IsMonthlyReportOn = True
