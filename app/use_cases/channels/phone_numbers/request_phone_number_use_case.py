"""An owner asks the platform team for a number."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.phone_numbers import PhoneNumberRequestRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.spend import OwnerAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.phone_numbers import PhoneNumberRequestDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.phone_numbers.phone_line import (
    PhoneNumberRequestView,
    RequestPhoneNumberCommand,
)
from app.schemas.dto.spend_guard import OwnerActionAdmission
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.channels.phone_numbers.phone_line_views import (
    build_open_request_view,
)
from app.use_cases.channels.phone_numbers.team_notice import tell_team_of_request
from app.utilities.telephony.phone_number_keys import phone_number_request_id_of

REQUEST_ENTITY: AuditEntityName = AuditEntityName("phone_number_request")


class RequestPhoneNumberUseCase(
    UseCaseContract[RequestPhoneNumberCommand, PhoneNumberRequestView]
):
    """
    The owner asks the platform team for a number: where a regulator wants
    the business's documents, where this server rents none by itself, or
    simply by choice. A business has one request (its id derives from the
    business): asking while one is open keeps it as it is (one e-mail to
    the team, never a stream of them); asking after it was done or
    cancelled opens it again. A new request e-mails every platform admin
    and is audited; a business (re)opens at most three a day
    (`owner_action_limits`), so asking and cancelling in a loop never
    floods the team's inbox. The team closes it by connecting the number as
    the phone channel (the maintenance job then marks it DONE).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        phone_number_request_repo: PhoneNumberRequestRepoContract,
        audit_log_repo: AuditLogRepoContract,
        manager_notifier: ManagerNotificationFacilitatorContract,
        app_settings: AppSettings,
        admit_owner_action: UseCaseContract[OwnerActionAdmission, None],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._request_repo: PhoneNumberRequestRepoContract = phone_number_request_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._manager_notifier: ManagerNotificationFacilitatorContract = (
            manager_notifier
        )
        self._app_settings: AppSettings = app_settings
        self._admit_owner_action: UseCaseContract[OwnerActionAdmission, None] = (
            admit_owner_action
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: RequestPhoneNumberCommand) -> PhoneNumberRequestView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        if (
            build_open_request_view(self._request_repo.get_by_business(business.id))
            is None
        ):
            # Only a request that opens (and e-mails the team) counts.
            self._admit_owner_action.run(
                OwnerActionAdmission(
                    action=OwnerAction.PHONE_NUMBER_REQUEST,
                    user_id=input_data.user_id,
                    business_id=business.id,
                )
            )

        now: Microseconds = self._wall_clock.now_unix()
        request = PhoneNumberRequestDocument(
            id=phone_number_request_id_of(business.id),
            business_id=business.id,
            requested_by=input_data.user_id,
            country_code=input_data.request.country_code,
            number_type=input_data.request.number_type,
            city=input_data.request.city,
            requested_at=now,
            created_at=now,
            updated_at=now,
        )
        if self._request_repo.open_request(request):
            self._audit_log_repo.append(
                AuditLogEntryDocument(
                    business_id=business.id,
                    actor_id=input_data.user_id,
                    action=AuditAction.CREATE,
                    entity=REQUEST_ENTITY,
                    entity_id=AuditEntityReference(str(request.id)),
                    ip_address=input_data.client_ip_address,
                    created_at=now,
                    updated_at=now,
                )
            )
            tell_team_of_request(
                self._manager_notifier, self._app_settings, business, request
            )

        view: PhoneNumberRequestView | None = build_open_request_view(
            self._request_repo.get_by_business(business.id)
        )
        if view is None:
            # Closed by the team between the write and this read.
            raise ConflictError("The request was just closed; reload the page.")

        return view
