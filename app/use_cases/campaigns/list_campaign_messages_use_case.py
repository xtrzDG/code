from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.campaign_repositories import (
    CampaignMessageRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.campaigns import CampaignMessageDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.growth.campaign_views import (
    CampaignMessagePage,
    CampaignMessagePageQuery,
    CampaignMessageView,
)
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.use_cases.shared.operations_support import build_audit_entry
from app.utilities.paging.keyset_paging import finish_page, read_slice

CAMPAIGN_MESSAGE_ENTITY: AuditEntityName = AuditEntityName("campaign_message")


class ListCampaignMessagesUseCase(
    UseCaseContract[CampaignMessagePageQuery, CampaignMessagePage]
):
    """
    Bookings → Return visits, the latest messages first: whom the campaign
    wrote to (or skipped, and why) and whether they booked again. Names
    customers, so owners only, and every read is audited.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        campaign_message_repo: CampaignMessageRepoContract,
        contact_repo: ContactRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._message_repo: CampaignMessageRepoContract = campaign_message_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CampaignMessagePageQuery) -> CampaignMessagePage:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        fetched: list[CampaignMessageDocument] = self._message_repo.page_latest(
            business.id, read_slice(input_data.page)
        )
        items, next_cursor = finish_page(
            fetched,
            input_data.page,
            sort_key=lambda message: int(message.created_at),
            item_id=lambda message: str(message.id),
        )
        contacts: dict[ContactId, ContactDocument] = self._contact_repo.get_many(
            business.id, list({message.contact_id for message in items})
        )
        self._audit_log_repo.append(
            build_audit_entry(
                business.id,
                input_data.user_id,
                AuditAction.VIEW,
                CAMPAIGN_MESSAGE_ENTITY,
                None,
                self._wall_clock.now_unix(),
                input_data.client_ip_address,
            )
        )
        return CampaignMessagePage(
            items=[build_message_view(message, contacts) for message in items],
            next_cursor=next_cursor,
        )


def build_message_view(
    message: CampaignMessageDocument, contacts: dict[ContactId, ContactDocument]
) -> CampaignMessageView:
    contact: ContactDocument | None = contacts.get(message.contact_id)
    return CampaignMessageView(
        id=message.id,
        contact_id=message.contact_id,
        contact_name=(
            None if contact is None or contact.erased_at is not None else contact.name
        ),
        rule_kind=message.rule_kind,
        status=message.status,
        skip_reason=message.skip_reason,
        channel=message.channel,
        conversation_id=message.conversation_id,
        sent_at=message.sent_at,
        booking_id=message.booking_id,
        booked_at=message.booked_at,
        created_at=message.created_at,
    )
