"""
How many records a customer's export copied (the export's audit entry,
`record_count`): the contact itself and every record of `ContactRecords`,
the consent ledger's entries included. Every list the records hold counts,
so a kind of record added to them later is counted without a change here.
"""

from typing import cast

from app.schemas.dto.compliance import ContactRecords
from app.schemas.typings.compliance.constrained_integers import AuditRecordCount


def exported_record_count(records: ContactRecords) -> AuditRecordCount:
    """The contact and each record of each of its lists, one each."""

    copied: int = 0
    for _, value in records:
        if isinstance(value, list):
            copied += len(cast("list[object]", value))

    return AuditRecordCount(1 + copied)
