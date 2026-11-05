import logging
from collections.abc import Iterator

from typed_time_provider import Microseconds, WallClock

from app.contracts.catalog_registries import ExchangeRateRegistryContract
from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.invoicing import InvoiceIssuingFacilitatorContract
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.phone_numbers import PhoneNumberRepoContract
from app.contracts.registries import PlanRegistryContract
from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
    UsageEventRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.billing import BillingNoticeKind
from app.schemas.constants.phone_numbers import (
    PhoneNumberReleaseReason,
    PhoneNumberStatus,
    RentalMonthOutcome,
)
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.billing_profiles import InvoiceLineText
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.phone_numbers import PhoneNumberDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.billing_ledger import BillingNotice, InvoiceDescriptionInput
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.exceptions.application_errors import InvalidPhoneNumberError
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.strings import (
    FormattedPhoneNumber,
    RawPhoneNumberInput,
)
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.billing.number_rentals.rental_bills import RentalBills
from app.use_cases.billing.number_rentals.rental_months import (
    decide_rental_month,
    month_bounds,
)
from app.use_cases.billing.owner_notifications import notify_business_owners
from app.use_cases.shared.billing_records import find_current_subscription
from app.utilities.billing.billing_periods import add_local_days
from app.utilities.storage.release_gates import PHONE_NUMBER_RENTAL_GATE, is_gate_open
from app.utilities.telephony.number_release import mark_releasing

logger: logging.Logger = logging.getLogger(__name__)
BATCH: DocumentQueryLimit = DocumentQueryLimit(100)


class BillPhoneNumberRentalsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Background job (hourly): each rental month of a rented number, when it
    begins (`rental_months.py`).

    - A paying customer's month is BILLED: an invoice of the kind
      `number_rental` on the subscription, in its currency (the price fixed
      when the number was taken, converted at the official rate when the
      subscription pays in another currency), and the owners are told the
      amount and the deadline. Like the minutes above the package, a bill
      left unpaid makes the subscription past due after the plan's grace
      days (`grace_periods.py`).
    - A month on the platform (INCLUDED: the first month before the first
      payment, a running trial, a cancelled subscription's last period) is
      not billed.
    - Either way the month is a NUMBER_RENTAL usage event with the
      carrier's price as its cost (the client's cost and margin).
    - A month is judged as of its start (`decide_rental_month`). When
      nobody pays (past due beyond the grace too), the number goes back
      (RELEASING, for want of payment; the maintenance job returns it and
      turns the phone channel off) and the owners are told.

    Until the release gate `phone_number_rental` opens (the release after
    the one that taught every reader the kind), months are neither billed
    nor recorded: `billed_until` waits, and the first run after the gate
    opens catches up month by month. Each step is written once: a month's
    invoice and usage event are skipped when they exist, and `billed_until`
    moves on only from the value it was read with.
    """

    def __init__(
        self,
        phone_number_repo: PhoneNumberRepoContract,
        business_repo: BusinessRepoContract,
        subscription_repo: SubscriptionRepoContract,
        invoice_repo: InvoiceRepoContract,
        usage_event_repo: UsageEventRepoContract,
        user_repo: UserRepoContract,
        plan_registry: PlanRegistryContract,
        exchange_rate_registry: ExchangeRateRegistryContract,
        invoice_issuing: InvoiceIssuingFacilitatorContract,
        invoice_description_transformer: TransformerContract[
            InvoiceDescriptionInput, InvoiceDescription
        ],
        invoice_line_texts_transformer: TransformerContract[
            InvoiceDescriptionInput, list[InvoiceLineText]
        ],
        manager_notifier: ManagerNotificationFacilitatorContract,
        billing_notice_transformer: TransformerContract[BillingNotice, MessageText],
        phone_number_parser: PhoneNumberParserContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._phone_number_repo: PhoneNumberRepoContract = phone_number_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._subscription_repo: SubscriptionRepoContract = subscription_repo
        self._user_repo: UserRepoContract = user_repo
        self._plan_registry: PlanRegistryContract = plan_registry
        self._manager_notifier: ManagerNotificationFacilitatorContract = (
            manager_notifier
        )
        self._billing_notice_transformer: TransformerContract[
            BillingNotice, MessageText
        ] = billing_notice_transformer
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._bills: RentalBills = RentalBills(
            invoice_repo,
            usage_event_repo,
            plan_registry,
            exchange_rate_registry,
            invoice_issuing,
            invoice_description_transformer,
            invoice_line_texts_transformer,
        )

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        handled: int = sum(self._settle(number, now) for number in self._due(now))
        return JobReport(processed_count=ProcessedItemCount(handled))

    def _due(self, now: Microseconds) -> Iterator[PhoneNumberDocument]:
        """ACTIVE numbers whose next month began, earliest first."""

        after: PhoneNumberDocument | None = None
        while True:
            page: list[PhoneNumberDocument] = self._phone_number_repo.page_in_status(
                PhoneNumberStatus.ACTIVE, after, BATCH
            )
            for number in page:
                if number.billed_until > now:
                    return

                yield number

            if len(page) < int(BATCH):
                return

            after = page[-1]

    def _settle(self, number: PhoneNumberDocument, now: Microseconds) -> int:
        """Every month of the number that began by now; how many were settled."""

        business: BusinessDocument | None = self._business_repo.get(number.business_id)
        if business is None:
            return 0

        settled: int = 0
        current: PhoneNumberDocument | None = number
        while (
            current is not None
            and current.status is PhoneNumberStatus.ACTIVE
            and current.billed_until <= now
        ):
            month: tuple[Microseconds, Microseconds] = month_bounds(
                current, business.timezone
            )
            subscription: SubscriptionDocument | None = find_current_subscription(
                self._subscription_repo, business.id
            )
            outcome = decide_rental_month(current, subscription, month[0])
            if outcome is RentalMonthOutcome.RELEASED:
                return settled + self._give_back(business, current, now)

            if not is_gate_open(PHONE_NUMBER_RENTAL_GATE):
                return settled

            if (
                outcome is RentalMonthOutcome.BILLED
                and subscription is not None
                and not self._bill(business, subscription, current, month, now)
            ):
                return settled

            self._bills.record_usage(current, month[0], now)
            current = self._move_on(current, month[1], now)
            settled += 1

        return settled

    def _bill(
        self,
        business: BusinessDocument,
        subscription: SubscriptionDocument,
        number: PhoneNumberDocument,
        month: tuple[Microseconds, Microseconds],
        now: Microseconds,
    ) -> bool:
        """The month's invoice and notice; False when it cannot be priced yet."""

        price: Money | None = self._bills.price_in(number, subscription.currency_code)
        if price is None:
            logger.warning(
                "Rental month of number %s is not billed yet: no exchange rate "
                "%s -> %s.",
                number.id,
                number.currency_code,
                subscription.currency_code,
            )
            return False

        invoice: InvoiceDocument | None = self._bills.issue_invoice(
            business, subscription, self._display(number), price, month, now
        )
        if invoice is not None:
            deadline: Microseconds = add_local_days(
                invoice.created_at,
                int(self._plan_registry.get(subscription.plan_key).grace_period_days),
                business.timezone,
            )
            self._notify(
                business,
                BillingNoticeKind.NUMBER_RENTAL_INVOICED,
                Money(
                    amount_minor=invoice.amount_minor,
                    currency_code=invoice.currency_code,
                ),
                deadline,
            )

        return True

    def _move_on(
        self, number: PhoneNumberDocument, month_end: Microseconds, now: Microseconds
    ) -> PhoneNumberDocument | None:
        """`billed_until` to the next month, only from the value it was read with."""

        read_at: Microseconds = number.billed_until
        return self._phone_number_repo.modify(
            number.business_id,
            number.id,
            lambda stored: (
                stored.model_copy(update={"billed_until": month_end, "updated_at": now})
                if stored.billed_until == read_at
                and stored.status is PhoneNumberStatus.ACTIVE
                else None
            ),
        )

    def _give_back(
        self, business: BusinessDocument, number: PhoneNumberDocument, now: Microseconds
    ) -> int:
        released: PhoneNumberDocument | None = self._phone_number_repo.modify(
            number.business_id,
            number.id,
            lambda stored: mark_releasing(stored, PhoneNumberReleaseReason.UNPAID, now),
        )
        if released is None:
            return 0

        self._notify(business, BillingNoticeKind.PHONE_NUMBER_RELEASED, None, None)
        return 1

    def _display(self, number: PhoneNumberDocument) -> FormattedPhoneNumber:
        try:
            return self._phone_number_parser.parse(
                RawPhoneNumberInput(str(number.phone_number)), None
            ).international_format
        except InvalidPhoneNumberError:
            return FormattedPhoneNumber(str(number.phone_number))

    def _notify(
        self,
        business: BusinessDocument,
        kind: BillingNoticeKind,
        amount: Money | None,
        deadline: Microseconds | None,
    ) -> None:
        notify_business_owners(
            business,
            self._user_repo,
            self._manager_notifier,
            self._billing_notice_transformer.transform(
                BillingNotice(
                    kind=kind,
                    language=business.owner_language,
                    timezone=business.timezone,
                    business_name=business.name,
                    amount=amount,
                    deadline=deadline,
                )
            ),
        )
