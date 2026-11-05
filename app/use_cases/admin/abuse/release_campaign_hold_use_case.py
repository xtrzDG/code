import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.campaign_repositories import (
    CampaignSettingsRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.campaigns import CampaignSettingsDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.admin_campaign_holds import (
    CampaignHoldView,
    ReleaseCampaignHoldCommand,
)
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.conversations.strings import MessageText
from app.use_cases.shared.owner_contacts import owner_contacts
from app.utilities.campaigns.campaign_review_texts import (
    OWNER_RELEASE_NOTICE,
    fill_hold_notice,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
AUDITED_ENTITY: AuditEntityName = AuditEntityName("campaign_settings")
RELEASED: AuditEntityReference = AuditEntityReference("review_hold_released")


class ReleaseCampaignHoldUseCase(
    UseCaseContract[ReleaseCampaignHoldCommand, CampaignHoldView]
):
    """
    A SUPER platform admin (MANAGE_OPERATIONS) lets a campaign held over its
    opt-out rate write again (ABUSE-05), with a reason: the hold is
    cleared (the owner's settings stay as they are), the release goes to
    the business's audit log (UPDATE of `campaign_settings`,
    `review_hold_released`, with the reason and the address) and the
    owners are told in their language. The release time is kept
    (`review_released_at`): from then on the campaign's opt-out rate counts
    only the messages sent after it, so the messages that held it cannot
    hold it again, and new ones past the rate hold it again.

    Raises:
        AccessDeniedError: the user is not a SUPER platform admin.
        NotFoundError: the business or its campaign does not exist.
        ConflictError: the campaign is not held.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        business_repo: BusinessRepoContract,
        campaign_settings_repo: CampaignSettingsRepoContract,
        user_repo: UserRepoContract,
        manager_notifier: ManagerNotificationFacilitatorContract,
        text_resolver: LocalizedTextResolverContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize: UseCaseContract[PlatformAdminAccessRequest, UserDocument] = (
            authorize_platform_admin
        )
        self._business_repo: BusinessRepoContract = business_repo
        self._settings_repo: CampaignSettingsRepoContract = campaign_settings_repo
        self._user_repo: UserRepoContract = user_repo
        self._notifier: ManagerNotificationFacilitatorContract = manager_notifier
        self._resolver: LocalizedTextResolverContract = text_resolver
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ReleaseCampaignHoldCommand) -> CampaignHoldView:
        admin: UserDocument = self._authorize.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.MANAGE_OPERATIONS,
            )
        )
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        settings: CampaignSettingsDocument | None = (
            None
            if business is None
            else self._settings_repo.get_by_business(business.id)
        )
        if business is None or settings is None:
            raise NotFoundError("The business has no campaign.")

        hold = settings.review_hold
        if hold is None:
            raise ConflictError("The campaign is not held.")

        now: Microseconds = self._wall_clock.now_unix()
        self._settings_repo.save(
            settings.model_copy(
                update={
                    "review_hold": None,
                    "review_released_at": now,
                    "updated_at": now,
                }
            )
        )
        entry = AuditLogEntryDocument(
            business_id=business.id,
            actor_id=admin.id,
            action=AuditAction.UPDATE,
            entity=AUDITED_ENTITY,
            entity_id=RELEASED,
            ip_address=input_data.client_ip_address,
            reason=input_data.reason,
            created_at=now,
            updated_at=now,
        )
        self._audit_log_repo.append(entry)
        LOGGER.warning(
            "The campaign of %s was released by platform admin %s (audit entry %s)",
            business.id,
            admin.id,
            entry.id,
        )
        for owner in owner_contacts(business, self._user_repo):
            text: str = str(
                self._resolver.resolve(OWNER_RELEASE_NOTICE, owner.language)
            )
            self._notifier.notify(
                StaffNotification(
                    business_id=business.id,
                    contact=owner,
                    text=MessageText(fill_hold_notice(text, str(business.name), hold)),
                )
            )

        return CampaignHoldView(
            business_id=business.id,
            held_at=hold.held_at,
            sent=hold.sent,
            opted_out=hold.opted_out,
        )
