"""
A customer's export is audited with how many records it copied: the
contact and each record, the consent ledger's entries included.
"""

from app.schemas.constants.consent_records import ConsentEvent, ConsentEventSource
from app.schemas.domain.consent_records import ConsentRecordDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.compliance import ContactRecords
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.compliance.contact_record_counts import exported_record_count


def test_the_count_holds_the_contact_and_every_record() -> None:
    contact = ContactDocument(business_id=BusinessId())
    entries = [
        ConsentRecordDocument(
            business_id=contact.business_id,
            contact_id=contact.id,
            event=event,
            source=ConsentEventSource.IN_PERSON,
        )
        for event in (ConsentEvent.GIVEN, ConsentEvent.WITHDRAWN)
    ]

    assert int(exported_record_count(ContactRecords(contact=contact))) == 1
    assert (
        int(
            exported_record_count(
                ContactRecords(contact=contact, consent_records=entries)
            )
        )
        == 3
    )


def test_every_kind_of_record_counts_one_each() -> None:
    contact = ContactDocument(business_id=BusinessId())
    lists: list[str] = [
        name
        for name, value in ContactRecords(contact=contact)
        if isinstance(value, list)
    ]
    # One record in each list (their content does not matter to the count).
    values: dict[str, object] = {name: [object()] for name in lists}
    filled = ContactRecords.model_construct(None, contact=contact, **values)

    assert "consent_records" in lists
    assert len(lists) >= 14
    assert int(exported_record_count(filled)) == 1 + len(lists)
