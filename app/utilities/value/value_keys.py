"""
Identities of the value context: the settings of a business, one owner's
digest choices, one stored report per business, kind and period, and the
topics customers of a business ask about.
"""

from uuid import UUID, uuid5

from app.schemas.constants.value import ValueReportKind
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.insights.prefixed_id import ConversationTopicsId
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.value.constrained_strings import ValueReportPeriodKey
from app.schemas.typings.value.prefixed_id import (
    DigestPreferencesId,
    ValueReportId,
    ValueSettingsId,
)

# Fixed namespaces of derived ids (never change them: stored ids depend on
# them, and the report of a period is found again by its id).
VALUE_SETTINGS_NAMESPACE: UUID = UUID("2f6b9d14-7c3a-4e85-b1f0-8a4d2c6e9b31")
DIGEST_PREFERENCES_NAMESPACE: UUID = UUID("c47e2a90-15d8-4b3f-9e6a-0d1f7b8c2e54")
VALUE_REPORT_NAMESPACE: UUID = UUID("8d3c5f27-a196-4e0b-8c74-5e2b9a1d6f03")
CONVERSATION_TOPICS_NAMESPACE: UUID = UUID("5a1e8c3d-92f4-4b07-a6d2-7c9e0f4b13a8")


def value_settings_id_of(business_id: BusinessId) -> ValueSettingsId:
    """One value settings document per business."""

    return ValueSettingsId(uuid5(VALUE_SETTINGS_NAMESPACE, str(business_id)))


def digest_preferences_id_of(
    business_id: BusinessId,
    user_id: UserId,
) -> DigestPreferencesId:
    """One preferences document per business and owner."""

    return DigestPreferencesId(
        uuid5(DIGEST_PREFERENCES_NAMESPACE, f"{business_id}|{user_id}")
    )


def value_report_id_of(
    business_id: BusinessId,
    kind: ValueReportKind,
    period_key: ValueReportPeriodKey,
) -> ValueReportId:
    """The same period of the same kind is the same report."""

    return ValueReportId(
        uuid5(VALUE_REPORT_NAMESPACE, f"{business_id}|{kind.value}|{period_key}")
    )


def conversation_topics_id_of(business_id: BusinessId) -> ConversationTopicsId:
    """One topics document per business, replaced by every night's grouping."""

    return ConversationTopicsId(uuid5(CONVERSATION_TOPICS_NAMESPACE, str(business_id)))
