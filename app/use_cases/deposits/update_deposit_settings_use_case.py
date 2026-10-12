from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.deposits import DepositRefusalCode, PaymentLinkKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.deposits import DepositSettingsDocument
from app.schemas.dto.deposits.deposit_settings import (
    DepositSettingsRequest,
    DepositSettingsView,
    UpdateDepositSettingsCommand,
)
from app.use_cases.deposits.deposit_settings_changes import DepositSettingsChanges
from app.utilities.deposits.deposit_refusals import deposit_refusal


class UpdateDepositSettingsUseCase(
    UseCaseContract[UpdateDepositSettingsCommand, DepositSettingsView]
):
    """
    The owner turns deposits on or off, sets how long a held place waits
    for its deposit (15 minutes to a day), until when before the start a
    cancellation gets it back, and the template that serves the policies
    naming no page (a template of these settings; naming none keeps the
    current one, so turning deposits on never loses the page). Turning
    deposits off asks no new ones; those already asked keep their hold.
    Owners only; audited.
    """

    def __init__(self, changes: DepositSettingsChanges) -> None:
        self._changes: DepositSettingsChanges = changes

    def run(self, input_data: UpdateDepositSettingsCommand) -> DepositSettingsView:
        business: BusinessDocument = self._changes.owner_business(
            input_data.user_id, input_data.business_id
        )
        request: DepositSettingsRequest = input_data.request

        def edit(settings: DepositSettingsDocument) -> DepositSettingsDocument:
            if request.default_payment_link_id is not None and not any(
                link.id == request.default_payment_link_id
                and link.kind is PaymentLinkKind.TEMPLATE
                for link in settings.payment_links
            ):
                raise deposit_refusal(
                    DepositRefusalCode.NO_PAYMENT_LINK,
                    "The default payment page must be a template of these settings.",
                )

            settings.is_enabled = request.is_enabled
            settings.hold_minutes = request.hold_minutes
            settings.refund_cutoff_hours = request.refund_cutoff_hours
            if request.default_payment_link_id is not None:
                settings.default_payment_link_id = request.default_payment_link_id
            return settings

        return self._changes.apply(business, input_data.user_id, edit)
