from typed_time_provider import Microseconds

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.deposits import DepositSettingsDocument
from app.schemas.dto.deposits.deposit_settings import (
    DepositSettingsView,
    RemovePaymentLinkCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.deposits.deposit_settings_changes import DepositSettingsChanges
from app.utilities.deposits.payment_pages import retire_page


class RemovePaymentLinkUseCase(
    UseCaseContract[RemovePaymentLinkCommand, DepositSettingsView]
):
    """
    The owner removes a payment page. Policies that named it fall back to
    the default template; when it was the default, there is none until the
    owner picks another. Deposits already asked keep their link: the page
    is retired, out of the owner's list, and goes for good only once no
    hold can still need it (`payment_pages`). Owners only; audited.
    """

    def __init__(self, changes: DepositSettingsChanges) -> None:
        self._changes: DepositSettingsChanges = changes

    def run(self, input_data: RemovePaymentLinkCommand) -> DepositSettingsView:
        business: BusinessDocument = self._changes.owner_business(
            input_data.user_id, input_data.business_id
        )
        now: Microseconds = self._changes.wall_clock.now_unix()

        def edit(settings: DepositSettingsDocument) -> DepositSettingsDocument:
            if not retire_page(settings, input_data.link_id, now):
                raise NotFoundError(f"Payment link {input_data.link_id} was not found.")

            if settings.default_payment_link_id == input_data.link_id:
                settings.default_payment_link_id = None
            for entry in settings.policies:
                if entry.policy.payment_link_id == input_data.link_id:
                    entry.policy.payment_link_id = None
            return settings

        return self._changes.apply(business, input_data.user_id, edit)
