from typed_time_provider import Microseconds, WallClock

from app.contracts.incidents import IncidentRepoContract
from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.session_assurance import StepUpGuardContract
from app.contracts.storage import StorageUnitOfWorkContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.incidents import IncidentScope
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.incidents import IncidentDocument, IncidentNoticeText
from app.schemas.domain.users import UserDocument
from app.schemas.dto.incidents import CreateIncidentCommand, IncidentView
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.incidents.constrained_integers import (
    AffectedBusinessCount,
    NotifiedOwnerCount,
)
from app.use_cases.admin.incidents.incident_expansion import (
    EXPAND_INCIDENT_JOB,
    expansion_payload,
    expansion_serial_key,
)
from app.use_cases.admin.incidents.incident_reach import IncidentReach
from app.use_cases.admin.incidents.incident_views import incident_view
from app.use_cases.shared.storage_transaction import in_unit_of_work


class CreateIncidentUseCase(UseCaseContract[CreateIncidentCommand, IncidentView]):
    """
    POST /v1/admin/incidents: a platform admin records an incident
    (docs/operations/incident.md) for the businesses it affected.

    The incident is stored first, so the log holds it whatever follows.
    Its businesses are then told (`IncidentReach`): for a data breach
    every owner gets the DPA 12.1 notice through the outbox, and each
    business's audit log names the incident and the admin; other kinds
    are recorded for the postmortem only (outages are told on the status
    page). An incident of every business (ALL_BUSINESSES) names none:
    the incident and its `expand_incident` job are stored in one
    transaction, and the worker walks the businesses a keyset batch at a
    time (`ExpandIncidentUseCase`), so recording it costs the same however
    many businesses there are.

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
        reach: IncidentReach,
        job_queue: JobQueueFacilitatorContract,
        unit_of_work: StorageUnitOfWorkContract | None,
        step_up: StepUpGuardContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._business_repo: BusinessRepoContract = business_repo
        self._incident_repo: IncidentRepoContract = incident_repo
        self._reach: IncidentReach = reach
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._unit_of_work: StorageUnitOfWorkContract | None = unit_of_work
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
            scope=body.scope,
            reached_business_count=(
                AffectedBusinessCount(0)
                if body.scope is IncidentScope.ALL_BUSINESSES
                else None
            ),
            created_at=now,
            updated_at=now,
        )
        if incident.scope is IncidentScope.ALL_BUSINESSES:
            with in_unit_of_work(self._unit_of_work):
                self._incident_repo.save(incident)
                self._job_queue.enqueue(
                    EXPAND_INCIDENT_JOB,
                    expansion_payload(incident.id),
                    None,
                    lane=JobLane.DEFAULT,
                    serial_key=expansion_serial_key(incident.id),
                )
            return incident_view(incident)

        self._incident_repo.save(incident)
        notified: int = self._reach.reach(
            incident, businesses, input_data.client_ip_address, now
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
