from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    OnboardingRequestRepoContract,
    SubscriptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.billing import InvoiceKind, InvoiceStatus, SetupOption
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.billing import (
    InvoiceDocument,
    OnboardingRequestDocument,
    SubscriptionDocument,
)
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.dto.billing_cabinet import SetupOptionChoice
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.constrained_strings import StaffAlertSubject
from app.use_cases.shared.billing_records import (
    OPEN_INVOICE_STATUSES,
    list_subscription_invoices,
)
from app.utilities.billing.onboarding_keys import derive_onboarding_request_id

ADMIN_LANGUAGE: LanguageTag = LanguageTag("en")


class ChooseSetupOptionUseCase(UseCaseContract[SetupOptionChoice, None]):
    """
    The owner chose how the business is set up for the subscription about
    to be paid:

    - DONE_FOR_YOU: the subscription carries the option (its first monthly
      invoice brings the plan's setup fee), the business gets one
      onboarding request for the platform team, and every PLATFORM_ADMIN_
      EMAILS address hears about it once through the outbox;
    - SELF_SERVE: free. A setup fee invoiced earlier and not paid is voided;
      one already paid keeps the business DONE_FOR_YOU (the team does the
      setup it was paid for).
    """

    def __init__(
        self,
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        onboarding_request_repo: OnboardingRequestRepoContract,
        manager_notifier: ManagerNotificationFacilitatorContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._invoice_repo: InvoiceRepoContract = invoice_repo
        self._onboarding_request_repo: OnboardingRequestRepoContract = (
            onboarding_request_repo
        )
        self._manager_notifier: ManagerNotificationFacilitatorContract = (
            manager_notifier
        )
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: SetupOptionChoice) -> None:
        business: BusinessDocument = input_data.business
        subscription: SubscriptionDocument | None = self._subscription_repo.get(
            business.id, input_data.subscription_id
        )
        if subscription is None:
            raise NotFoundError("The subscription to pay for is gone.")

        now: Microseconds = self._wall_clock.now_unix()
        if input_data.option is SetupOption.DONE_FOR_YOU:
            self._save_option(subscription, SetupOption.DONE_FOR_YOU, now)
            self._request_onboarding(input_data, subscription, now)
            return

        setup_fees: list[InvoiceDocument] = [
            invoice
            for invoice in list_subscription_invoices(self._invoice_repo, subscription)
            if invoice.kind is InvoiceKind.SETUP_FEE
        ]
        if any(invoice.status is InvoiceStatus.PAID for invoice in setup_fees):
            return

        for invoice in setup_fees:
            if invoice.status in OPEN_INVOICE_STATUSES:
                invoice.status = InvoiceStatus.VOID
                invoice.updated_at = now
                self._invoice_repo.save(invoice)

        self._save_option(subscription, SetupOption.SELF_SERVE, now)

    def _save_option(
        self,
        subscription: SubscriptionDocument,
        option: SetupOption,
        now: Microseconds,
    ) -> None:
        if subscription.setup_option is option:
            return

        subscription.setup_option = option
        subscription.updated_at = now
        self._subscription_repo.save(subscription)

    def _request_onboarding(
        self,
        input_data: SetupOptionChoice,
        subscription: SubscriptionDocument,
        now: Microseconds,
    ) -> None:
        business: BusinessDocument = input_data.business
        is_new: bool = self._onboarding_request_repo.open_once(
            OnboardingRequestDocument(
                id=derive_onboarding_request_id(business.id),
                business_id=business.id,
                requested_by=input_data.user_id,
                plan_key=subscription.plan_key,
                requested_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        if not is_new:
            return

        base: str = str(self._app_settings.cabinet_base_url or "").rstrip("/")
        text = MessageText(
            f"Done-for-you setup requested: {business.name}\n\n"
            f"Country {business.country_code}, niche {business.niche_key.value}, "
            f"plan {subscription.plan_key.value}. The setup fee comes with the "
            "first monthly invoice.\n"
            f"{base}/admin/clients/{business.id}"
        )
        for address in self._app_settings.platform_admin_emails:
            self._manager_notifier.notify(
                StaffNotification(
                    business_id=business.id,
                    contact=ManagerContact(
                        name=ManagerName("Platform team"),
                        channel=ManagerContactChannel.EMAIL,
                        address=ManagerContactAddress(str(address)),
                        language=ADMIN_LANGUAGE,
                    ),
                    text=text,
                    subject=StaffAlertSubject(f"onboarding_request:{business.id}"),
                )
            )
