from typed_time_provider import Microseconds, WallClock

from app.contracts.incidents import IncidentRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.incidents import IncidentKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.incidents import IncidentDocument, IncidentNoticeText
from app.schemas.domain.users import UserDocument
from app.schemas.dto.incidents import CreateIncidentCommand, IncidentView
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.incidents.constrained_integers import NotifiedOwnerCount
from app.use_cases.admin.incidents.incident_views import incident_view
from app.use_cases.admin.incidents.owner_breach_notices import OwnerBreachNotices

INCIDENT_ENTITY: AuditEntityName = AuditEntityName("incident")


class CreateIncidentUseCase(UseCaseContract[CreateIncidentCommand, IncidentView]):
    """
    POST /v1/admin/incidents: a platform admin records an incident
    (docs/operations/incident.md) for the businesses it affected.

    The incident is stored first, so the log holds it whatever follows.
    For a data breach every owner of every affected business then gets
    the DPA 12.1 notice through the outbox (`OwnerBreachNotices`); other
    kinds are recorded for the postmortem only (outages are told on the
    status page). Each affected business's audit log gets an entry naming
    the incident and the admin, so an owner can see it was told.

    Needs a recent sign-in (step-up), like every admin action that reaches
    owners' data or inboxes.

    Raises:
        AccessDeniedError: the user is not a platform admin.
        StepUpRequiredError: the session must sign in again first.
        ValidationFailedError: a named business does not exist, or the
            incident starts in the future or after it was detected.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        business_repo: BusinessRepoContract,
        incident_repo: IncidentRepoContract,
        audit_log_repo: AuditLogRepoContract,
        breach_notices: OwnerBreachNotices,
        step_up: StepUpGuardContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._business_repo: BusinessRepoContract = business_repo
        self._incident_repo: IncidentRepoContract = incident_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._breach_notices: OwnerBreachNotices = breach_notices
        self._step_up: StepUpGuardContract = step_up
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CreateIncidentCommand) -> IncidentView:
        admin: UserDocument = self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.MANAGE_OPERATIONS,
            )
        )
        self._step_up.require_recent_authentication()
        now: Microseconds = self._wall_clock.now_unix()
        body = input_data.body
        detected_at: Microseconds = body.detected_at or now
        if int(body.started_at) > int(detected_at) or int(detected_at) > int(now):
            raise ValidationFailedError(
                "An incident starts before it is detected, and neither is in "
                "the future."
            )

        businesses: list[BusinessDocument] = self._load_businesses(input_data)
        incident = IncidentDocument(
            kind=body.kind,
            severity=body.severity,
            title=body.title,
            started_at=body.started_at,
            detected_at=detected_at,
            affected_business_ids=[business.id for business in businesses],
            approximate_subject_count=body.approximate_subject_count,
            approximate_record_count=body.approximate_record_count,
            notice_texts=[
                IncidentNoticeText(
                    language=text.language,
                    nature=text.nature,
                    subject_categories=text.subject_categories,
                    record_categories=text.record_categories,
                    likely_consequences=text.likely_consequences,
                    measures=text.measures,
                )
                for text in body.notice_texts
            ],
            reported_by=admin.id,
            created_at=now,
            updated_at=now,
        )
        self._incident_repo.save(incident)
        notified: int = 0
        for business in businesses:
            if incident.kind is IncidentKind.DATA_BREACH:
                notified += self._breach_notices.send(incident, business)

            self._audit_log_repo.append(
                AuditLogEntryDocument(
                    business_id=business.id,
                    actor_id=admin.id,
                    action=AuditAction.CREATE,
                    entity=INCIDENT_ENTITY,
                    entity_id=AuditEntityReference(str(incident.id)),
                    ip_address=input_data.client_ip_address,
                    created_at=now,
                    updated_at=now,
                )
            )

        if notified:
            incident.notified_owner_count = NotifiedOwnerCount(notified)
            incident.notified_at = now
            incident.updated_at = now
            self._incident_repo.save(incident)

        return incident_view(incident)

    def _load_businesses(
        self, input_data: CreateIncidentCommand
    ) -> list[BusinessDocument]:
        businesses: list[BusinessDocument] = []
        missing: list[str] = []
        for business_id in input_data.body.affected_business_ids:
            business: BusinessDocument | None = self._business_repo.get(business_id)
            if business is None:
                missing.append(str(business_id))
            else:
                businesses.append(business)

        if missing:
            raise ValidationFailedError(
                f"These businesses do not exist: {', '.join(missing)}."
            )

        return businesses
