from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.customer_repositories import (
    CustomerCardRepoContract,
    CustomerSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactBlock, ContactDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.customers.customer_card import (
    ChangeCustomerBlockingCommand,
    CustomerCardView,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
)
from app.use_cases.contacts.customer_card_views import card_change_entry, card_view


class ChangeCustomerBlockingUseCase(
    UseCaseContract[ChangeCustomerBlockingCommand, CustomerCardView]
):
    """
    The owner blocks a customer (spam, abuse) or unblocks them. While
    blocked, the assistant answers nothing the customer sends in any
    channel (the turn gate stays silent, a call ends) and the customer
    belongs to no segment; their messages still reach the inbox. Owners
    only: a block silences a real person. Blocking again keeps the first
    moment. Audited (UPDATE of the contact).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        card_repo: CustomerCardRepoContract,
        customer_settings_repo: CustomerSettingsRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._card_repo: CustomerCardRepoContract = card_repo
        self._customer_settings_repo: CustomerSettingsRepoContract = (
            customer_settings_repo
        )
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ChangeCustomerBlockingCommand) -> CustomerCardView:
        """
        Raises:
            AccessDeniedError: staff asked.
            NotFoundError: no such customer in the business.
            ConflictError: the customer's data was erased.
        """

        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        is_blocked: bool = input_data.request.is_blocked

        def change(contact: ContactDocument) -> None:
            if contact.erased_at is not None:
                raise ConflictError("An erased customer cannot be blocked.")

            if not is_blocked:
                contact.block = None
            elif contact.block is None:
                contact.block = ContactBlock(
                    blocked_at=now, blocked_by=input_data.user_id
                )

        changed: ContactDocument | None = self._card_repo.change_card(
            business.id, input_data.contact_id, change
        )
        if changed is None:
            raise NotFoundError(f"Contact {input_data.contact_id} was not found.")

        self._audit_log_repo.append(
            card_change_entry(
                changed, input_data.user_id, input_data.client_ip_address, now
            )
        )
        return card_view(
            changed, self._customer_settings_repo.get_by_business(business.id)
        )
