from typed_time_provider import Microseconds

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.incidents import IncidentKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.incidents import IncidentDocument
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
    ClientIpAddress,
)
from app.use_cases.admin.incidents.owner_breach_notices import OwnerBreachNotices

INCIDENT_ENTITY: AuditEntityName = AuditEntityName("incident")


class IncidentReach:
    """
    What an incident does to each business it affected: for a data breach
    every owner gets the DPA 12.1 notice through the outbox
    (`OwnerBreachNotices`, one per owner and incident however often it is
    sent), and the business's audit log gets an entry naming the incident
    and the admin who recorded it, so the owner can see they were told.
    Used for the businesses an incident names at once, and by the
    `expand_incident` job for every business, a batch at a time.
    """

    def __init__(
        self,
        breach_notices: OwnerBreachNotices,
        audit_log_repo: AuditLogRepoContract,
    ) -> None:
        self._breach_notices: OwnerBreachNotices = breach_notices
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo

    def reach(
        self,
        incident: IncidentDocument,
        businesses: list[BusinessDocument],
        ip_address: ClientIpAddress | None,
        now: Microseconds,
    ) -> int:
        """Tell `businesses` about `incident`; how many owners' notices were queued."""

        notified: int = 0
        for business in businesses:
            if incident.kind is IncidentKind.DATA_BREACH:
                notified += self._breach_notices.send(incident, business)

            self._audit_log_repo.append(
                AuditLogEntryDocument(
                    business_id=business.id,
                    actor_id=incident.reported_by,
                    action=AuditAction.CREATE,
                    entity=INCIDENT_ENTITY,
                    entity_id=AuditEntityReference(str(incident.id)),
                    ip_address=ip_address,
                    created_at=now,
                    updated_at=now,
                )
            )

        return notified
