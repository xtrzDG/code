from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    LeadRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.deposit_repositories import (
    DepositSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.deposits import DepositExemption
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.deposits import DepositSettingsDocument
from app.schemas.dto.deposits.payment_link_requests import (
    DepositQuote,
    DepositQuoteQuery,
)
from app.use_cases.deposits.deposit_quotes import (
    QuotedDeposit,
    quote_banquet,
    quote_booking,
)
from app.use_cases.shared.business_access import require_business


class QuoteDepositUseCase(UseCaseContract[DepositQuoteQuery, DepositQuote]):
    """
    Whether a booking or a banquet request the assistant just made needs a
    deposit, and how much, so its tool result tells the model to send the
    payment link. Reads only; one settings read for a business without
    deposits.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        deposit_settings_repo: DepositSettingsRepoContract,
        booking_repo: BookingRepoContract,
        lead_repo: LeadRepoContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._settings_repo: DepositSettingsRepoContract = deposit_settings_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._lead_repo: LeadRepoContract = lead_repo

    def run(self, input_data: DepositQuoteQuery) -> DepositQuote:
        settings: DepositSettingsDocument | None = self._settings_repo.get_by_business(
            input_data.business_id
        )
        if settings is None or not settings.is_enabled:
            return DepositQuote(exemption=DepositExemption.DEPOSITS_OFF)

        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        quoted: QuotedDeposit = QuotedDeposit(exemption=DepositExemption.NOTHING_OPEN)
        if input_data.booking_id is not None:
            booking = self._booking_repo.get(business.id, input_data.booking_id)
            if booking is not None:
                quoted = quote_booking(settings, booking, business.currency_code)
        elif input_data.lead_id is not None:
            lead = self._lead_repo.get(business.id, input_data.lead_id)
            if lead is not None:
                quoted = quote_banquet(settings, lead, business.currency_code)

        return DepositQuote(amount=quoted.amount, exemption=quoted.exemption)
