"""
The catalog entries of payments: checkout orders and package usage
warnings (0003), and the retries of declined automatic charges (1214).
Part of DOCUMENT_COLLECTIONS (document_collection_catalog.py).
"""

from app.schemas.domain.package_usage import PackageUsageWarningDocument
from app.schemas.domain.payment_retries import PaymentRetryAttemptDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

PAYMENT_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(
        DocumentCollectionName("payment_orders"), PaymentOrderDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("package_usage_warnings"),
        PackageUsageWarningDocument,
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("payment_retry_attempts"),
        PaymentRetryAttemptDocument,
    ),
)
