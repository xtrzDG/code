from base_pydantic_schemas import BaseDocument, SchemaVersion

from app.schemas.constants.value import DigestChannel
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.handoffs.strings import ManagerContactAddress
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
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
    Which summaries one owner of a business gets and where (one document
    per business and user, the id derived from them). Without a document:
    the weekly digest and the monthly report, no daily digest, by e-mail
    and on their devices.

    Version 2: where they arrive. `channels` (None: e-mail and devices, as
    version 1 sent them); `telegram_chat`, the owner's own chat among the
    business's Telegram chats linked to the platform bot; `whatsapp_number`,
    the number the platform's WhatsApp sends the report template to (the
    owner opted in by choosing it). All optional, so version 1 rows read as
    they are.
    """

    schema_version: SchemaVersion = SchemaVersion("2")
    id: DigestPreferencesId
    business_id: BusinessId
    user_id: UserId
    is_daily_digest_on: IsDailyDigestOn = False
    is_weekly_digest_on: IsWeeklyDigestOn = True
    is_monthly_report_on: IsMonthlyReportOn = True
    channels: list[DigestChannel] | None = None
    telegram_chat: ManagerContactAddress | None = None
    whatsapp_number: E164PhoneNumber | None = None
