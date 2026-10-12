"""
What the audit log's hash chains and its anomaly checks read from storage:
the platform log's filter and the hour's counts the alerts compare with
their thresholds.
"""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.compliance import AuditAction, AuditSecurityEvent
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.users.prefixed_id import UserId


class PlatformAuditFilter(ImmutableDTO):
    """The platform log's entries of one operation or security event."""

    action: AuditAction | None = None
    security_event: AuditSecurityEvent | None = None


class BusinessOperationCount(ImmutableDTO):
    """How many exports and erasures of personal data one business ran."""

    business_id: BusinessId
    operation_count: DocumentCount


class AdminTenantCount(ImmutableDTO):
    """How many different businesses one platform admin entered or changed."""

    actor_id: UserId
    business_count: DocumentCount


class FailedCheckCount(ImmutableDTO):
    """
    How many sign-in checks failed for one destination: a login code's
    address (its keyed digest, never the address) or a person's second
    factor.
    """

    entity: AuditEntityName
    entity_id: AuditEntityReference
    failure_count: DocumentCount
