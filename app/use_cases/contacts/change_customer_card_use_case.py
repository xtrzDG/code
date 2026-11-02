from typed_time_provider import Microseconds, WallClock

from app.contracts.privacy import SuppressionListContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.consent_repositories import ConsentRecordRepoContract
from app.contracts.repositories.customer_repositories import (
    CustomerCardRepoContract,
    CustomerSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.consent_records import ConsentEventSource
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument, MarketingConsent
from app.schemas.domain.customer_settings import CustomerSettingsDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.customers.consent_records import ConsentOrigin
from app.schemas.dto.customers.customer_card import (
    ChangeCustomerCardCommand,
    CustomerCardView,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
)
from app.schemas.typings.contacts.constrained_strings import CustomerTag
from app.use_cases.contacts.customer_card_views import card_change_entry, card_view
from app.use_cases.contacts.marketing_consent_views import record_in_person
from app.use_cases.shared.consent_ledger import record_consent_change
from app.utilities.customers.customer_card import (
    add_tags,
    remember_tags,
    remove_tags,
)


class ChangeCustomerCardUseCase(
    UseCaseContract[ChangeCustomerCardCommand, CustomerCardView]
):
    """
    Owners and staff tag a customer, mark them VIP and record the
    marketing consent the customer gave or took back in person, with who
    recorded it and the wording's version (Customers → a customer). The
    change is one atomic step on the contact as stored, so two colleagues
    tagging at once both land, and a turn saving the contact meanwhile
    keeps it. Tags compare without case; a customer carries at most 20;
    the business's list of tags remembers the new ones first. An erased
    customer has no card. Audited (UPDATE of the contact); a consent given
    or taken back is also an entry of the consent ledger (who recorded it,
    the wording's version, the team member's network).
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
        suppression_list: SuppressionListContract,
        consent_record_repo: ConsentRecordRepoContract,
    ) -> None:
        self._suppression_list: SuppressionListContract = suppression_list
        self._consent_record_repo: ConsentRecordRepoContract = consent_record_repo
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._card_repo: CustomerCardRepoContract = card_repo
        self._customer_settings_repo: CustomerSettingsRepoContract = (
            customer_settings_repo
        )
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ChangeCustomerCardCommand) -> CustomerCardView:
        """
        Raises:
            NotFoundError: no such customer in the business.
            ConflictError: the customer's data was erased.
        """

        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        request = input_data.request
        added: list[CustomerTag] = []
        # The consent as stored before the change that went through.
        consent_before: list[MarketingConsent | None] = []

        def change(contact: ContactDocument) -> None:
            if contact.erased_at is not None:
                raise ConflictError("An erased customer has no card.")

            remove_tags(contact, list(request.remove_tags))
            added.extend(
                add_tags(contact, list(request.add_tags), input_data.user_id, now)
            )
            if request.is_vip is not None:
                contact.is_vip = request.is_vip
            if request.marketing_consent is not None:
                consent_before.append(contact.marketing_consent)
                record_in_person(
                    contact, request.marketing_consent, input_data.user_id, now
                )

        changed: ContactDocument | None = self._card_repo.change_card(
            business.id, input_data.contact_id, change
        )
        if changed is None:
            raise NotFoundError(f"Contact {input_data.contact_id} was not found.")

        if consent_before:
            record_consent_change(
                self._consent_record_repo,
                changed,
                consent_before[-1],
                changed.marketing_consent,
                ConsentOrigin(
                    source=ConsentEventSource.IN_PERSON,
                    recorded_by=input_data.user_id,
                    client_ip_address=input_data.client_ip_address,
                ),
                now,
            )

        settings: CustomerSettingsDocument | None = (
            self._remember(business, added, now)
            if added
            else self._customer_settings_repo.get_by_business(business.id)
        )
        self._audit_log_repo.append(
            card_change_entry(
                changed, input_data.user_id, input_data.client_ip_address, now
            )
        )
        return card_view(changed, settings, self._suppression_list)

    def _remember(
        self, business: BusinessDocument, added: list[CustomerTag], now: Microseconds
    ) -> CustomerSettingsDocument:
        def remember(settings: CustomerSettingsDocument) -> None:
            settings.known_tags = remember_tags(list(settings.known_tags), added)

        return self._customer_settings_repo.change(business.id, remember, now)
