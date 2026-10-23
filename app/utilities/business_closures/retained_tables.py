"""
What a business's deletion keeps, and why (docs/architecture.md, "Закрытие
бизнеса и удаление аккаунта"): the audit log is append-only and leaves only
through `workshop purge-audit-log` (entries of the last 365 days never),
its hash chains' own records keep the kept entries verifiable, and tax law
requires the issued invoices (DPA 13.2) and the partners' commissions
earned on them. Everything else of the business goes.
"""

from collections.abc import Mapping

from app.schemas.typings.storage.constrained_strings import DocumentCollectionName

RETAINED_TABLES: Mapping[DocumentCollectionName, str] = {
    DocumentCollectionName("audit_log_entries"): (
        "append-only; leaves through the audit retention purge (365 days and more)"
    ),
    DocumentCollectionName("audit_chain_heads"): "the kept entries' hash chain",
    DocumentCollectionName("audit_chain_checkpoints"): "the kept entries' hash chain",
    DocumentCollectionName("audit_chain_statuses"): "the kept entries' hash chain",
    DocumentCollectionName("invoices"): "issued invoices: tax law (DPA 13.2)",
    DocumentCollectionName("commission_entries"): (
        "partners' commissions on the kept invoices: the payout books"
    ),
}
# The business's own row goes last: until then a retried deletion still
# knows the business it deletes.
BUSINESSES_TABLE: DocumentCollectionName = DocumentCollectionName("businesses")
QUEUED_JOBS_TABLE: DocumentCollectionName = DocumentCollectionName("queued_jobs")


def is_retained(table: DocumentCollectionName) -> bool:
    return table in RETAINED_TABLES


def erase_order(
    tables: list[DocumentCollectionName],
) -> list[DocumentCollectionName]:
    """The erasable tables, the business's own row last."""

    erasable: list[DocumentCollectionName] = sorted(
        table for table in set(tables) if not is_retained(table)
    )
    if BUSINESSES_TABLE in erasable:
        erasable.remove(BUSINESSES_TABLE)
        erasable.append(BUSINESSES_TABLE)

    return erasable
