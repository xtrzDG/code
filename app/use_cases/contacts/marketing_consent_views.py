"""
A customer's marketing consent on the team's card: what the card says
about it, and the team's record of a consent given or taken back in person.
"""

from typed_time_provider import Microseconds

from app.contracts.privacy import SuppressionListContract
from app.schemas.constants.marketing_consent import (
    CURRENT_MARKETING_CONSENT_TEXT,
    MarketingConsentSource,
    MarketingConsentStatus,
    MarketingConsentWithdrawal,
)
from app.schemas.domain.contacts import ContactDocument, MarketingConsent
from app.schemas.dto.customers.customer_card import MarketingConsentView
from app.schemas.typings.contacts.booleans import IsMarketingConsentGiven
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.privacy.messaging_suppression import is_messaging_suppressed


def consent_view(
    contact: ContactDocument, suppression_list: SuppressionListContract
) -> MarketingConsentView:
    """
    The consent as recorded, with its status: STOPPED while the customer
    gets no message they did not ask for (STOP, the suppression list, a
    block), so the card never says "agreed" for them.
    """

    consent: MarketingConsent | None = contact.marketing_consent
    status: MarketingConsentStatus = consent_status(
        contact,
        is_messaging_suppressed(suppression_list, contact.business_id, contact),
    )
    if consent is None:
        return MarketingConsentView(status=status)

    return MarketingConsentView(
        status=status,
        given_at=consent.given_at,
        source=consent.source,
        text_version=consent.text_version,
        recorded_by=consent.recorded_by,
        withdrawn_at=consent.withdrawn_at,
        withdrawal=consent.withdrawal,
        withdrawn_by=consent.withdrawn_by,
    )


def consent_status(
    contact: ContactDocument, is_suppressed: bool
) -> MarketingConsentStatus:
    if is_suppressed:
        return MarketingConsentStatus.STOPPED

    if contact.marketing_consent is None:
        return MarketingConsentStatus.NOT_GIVEN

    if contact.marketing_consent.is_active:
        return MarketingConsentStatus.AGREED

    return MarketingConsentStatus.WITHDRAWN


def record_in_person(
    contact: ContactDocument,
    is_given: IsMarketingConsentGiven,
    user_id: UserId,
    now: Microseconds,
) -> None:
    """
    The customer told the team they agree (the current wording, recorded
    by this team member) or take it back. Agreeing again keeps the first
    consent; taking back what is not given changes nothing.
    """

    consent: MarketingConsent | None = contact.marketing_consent
    if is_given and not contact.has_marketing_consent:
        contact.marketing_consent = MarketingConsent(
            given_at=now,
            source=MarketingConsentSource.IN_PERSON,
            text_version=CURRENT_MARKETING_CONSENT_TEXT,
            recorded_by=user_id,
        )
    elif not is_given and consent is not None:
        contact.marketing_consent = consent.withdrawn(
            now, MarketingConsentWithdrawal.IN_PERSON, user_id
        )
