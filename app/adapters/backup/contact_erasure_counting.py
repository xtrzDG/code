"""
The ledger of erased customers counted in a restored database: how many
erased customers it names, and how many of them the restored backup holds
with their data again (it is older than their erasure). The drill counts
them; after a real restore the daily `reapply_contact_erasures` erases them
again with the application's own erasure (messages, calls, recordings, the
copies at the sub-processors), which plain SQL cannot reach.
"""

from collections.abc import Sequence
from typing import LiteralString

import psycopg
from psycopg.rows import TupleRow

from app.schemas.dto.business_closures.contact_erasure_ledger import (
    ContactErasureRecord,
)

CONTACTS_TABLE_SQL: LiteralString = "select to_regclass('workshop.contacts')"
RESTORED_CONTACTS_SQL: LiteralString = (
    "select count(*) from workshop.contacts as contact"
    " join unnest(%s::text[], %s::text[]) as ledger(business_id, contact_id)"
    " on contact.business_id = ledger.business_id"
    " and contact.document_key = ledger.contact_id"
    " where contact.document ->> 'erased_at' is null"
)

type Connection = psycopg.Connection[TupleRow]


def count_restored_contacts(
    connection: Connection, records: Sequence[ContactErasureRecord]
) -> int:
    """Erased customers of the ledger whose contact has its data again."""

    row = connection.execute(CONTACTS_TABLE_SQL).fetchone()
    if not records or row is None or row[0] is None:
        return 0

    counted = connection.execute(
        RESTORED_CONTACTS_SQL,
        [
            [str(record.business_id) for record in records],
            [str(record.contact_id) for record in records],
        ],
    ).fetchone()
    return 0 if counted is None else int(counted[0])
