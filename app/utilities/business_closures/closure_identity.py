"""
The ids of a business's closure and of its deletion ledger entry: one of
each per business. The namespaces are fixed: stored ids depend on them.
"""

from uuid import UUID, uuid5

from app.schemas.typings.business_closures.prefixed_id import (
    BusinessClosureId,
    BusinessDeletionId,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId

BUSINESS_CLOSURE_NAMESPACE: UUID = UUID("6697dfe2-8c16-43f5-b001-09e4c5fe5ef4")
BUSINESS_DELETION_NAMESPACE: UUID = UUID("c9914975-d72c-4ade-b7c5-3a1cda60a309")


def closure_id_for(business_id: BusinessId) -> BusinessClosureId:
    return BusinessClosureId(uuid5(BUSINESS_CLOSURE_NAMESPACE, str(business_id)))


def deletion_id_for(business_id: BusinessId) -> BusinessDeletionId:
    return BusinessDeletionId(uuid5(BUSINESS_DELETION_NAMESPACE, str(business_id)))
