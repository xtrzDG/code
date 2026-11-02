"""
How many records a customer's export copied (the export's audit entry,
`record_count`): the contact itself and every record of `ContactRecords`,
the consent ledger's entries included.
"""

from collections.abc import Sized

from app.schemas.dto.compliance import ContactRecords
from app.schemas.typings.compliance.constrained_integers import AuditRecordCount


def exported_record_count(records: ContactRecords) -> AuditRecordCount:
    """The contact and each of its records, one each."""

    collections: tuple[Sized, ...] = (
        records.conversations,
        records.messages,
        records.calls,
        records.bookings,
        records.leads,
        records.handoffs,
        records.notes,
        records.missed_calls,
        records.outbound_messages,
        records.inbound_events,
        records.feedback_requests,
        records.waitlist_entries,
        records.campaign_messages,
        records.consent_records,
    )
    return AuditRecordCount(1 + sum(len(items) for items in collections))
