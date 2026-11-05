"""
The consent ledger's entries (CONS-02): a change of a customer's marketing
consent (`ContactDocument.marketing_consent`, the current state) becomes
one append-only entry of the ledger with where it happened and how it can
be proved; a change of nothing (agreeing again, taking back what was not
given) writes none.
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.consent_repositories import ConsentRecordRepoContract
from app.schemas.constants.consent_records import ConsentEvent
from app.schemas.domain.consent_records import ConsentRecordDocument
from app.schemas.domain.contacts import ContactDocument, MarketingConsent
from app.schemas.dto.customers.consent_records import ConsentOrigin


def consent_event(
    before: MarketingConsent | None, after: MarketingConsent | None
) -> ConsentEvent | None:
    """GIVEN when an active consent appeared, WITHDRAWN when one ended."""

    was_given: bool = before is not None and before.is_active
    is_given: bool = after is not None and after.is_active
    if is_given and not was_given:
        return ConsentEvent.GIVEN

    if was_given and not is_given:
        return ConsentEvent.WITHDRAWN

    return None


def record_consent_change(
    repo: ConsentRecordRepoContract | None,
    contact: ContactDocument,
    before: MarketingConsent | None,
    after: MarketingConsent | None,
    origin: ConsentOrigin,
    now: Microseconds,
) -> ConsentRecordDocument | None:
    """
    Append the entry of the change from `before` to `after`, with the
    wording given (or, for a withdrawal, the one taken back); the entry, or
    None when nothing changed (or no ledger is wired).
    """

    event: ConsentEvent | None = consent_event(before, after)
    if repo is None or event is None:
        return None

    worded: MarketingConsent | None = after if event is ConsentEvent.GIVEN else before
    record = ConsentRecordDocument(
        business_id=contact.business_id,
        contact_id=contact.id,
        event=event,
        source=origin.source,
        channel=origin.channel,
        text_version=None if worded is None else worded.text_version,
        language=origin.language,
        recorded_by=origin.recorded_by,
        booking_id=origin.booking_id,
        conversation_id=origin.conversation_id,
        client_ip_address=origin.client_ip_address,
        created_at=now,
        updated_at=now,
    )
    repo.append(record)
    return record
