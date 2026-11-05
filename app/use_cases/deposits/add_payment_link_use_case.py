from typed_time_provider import Microseconds

from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.deposits import PaymentLinkKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.deposits import DepositSettingsDocument, PaymentLink
from app.schemas.dto.deposits.deposit_settings import (
    AddPaymentLinkCommand,
    DepositSettingsView,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.channels.strings import ChannelSecret
from app.use_cases.deposits.deposit_settings_changes import DepositSettingsChanges
from app.utilities.deposits.payment_link_addresses import (
    VettedPaymentLink,
    vet_payment_link,
)

# Pages one business keeps: a template and a fixed page per deposit rule.
MAX_PAYMENT_LINKS: int = 20


class AddPaymentLinkUseCase(
    UseCaseContract[AddPaymentLinkCommand, DepositSettingsView]
):
    """
    The owner adds one of their own payment pages: a fixed page (one
    amount) or a template the platform fills with {amount} or
    {amount_minor}, {currency} and {reference}. The address must be https
    on a public host, with no user name and only those placeholders
    (`payment_link_addresses`). One that carries a key in its query is
    stored sealed with the platform key ring and never shown again (the
    cabinet sees its host and path). The first template becomes the
    default. Owners only; audited.
    """

    def __init__(
        self,
        changes: DepositSettingsChanges,
        secret_cipher: SecretCipherAdapterContract,
    ) -> None:
        self._changes: DepositSettingsChanges = changes
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher

    def run(self, input_data: AddPaymentLinkCommand) -> DepositSettingsView:
        business: BusinessDocument = self._changes.owner_business(
            input_data.user_id, input_data.business_id
        )
        vetted: VettedPaymentLink = vet_payment_link(
            str(input_data.link.address), input_data.link.kind
        )
        now: Microseconds = self._changes.wall_clock.now_unix()
        link = PaymentLink(
            label=input_data.link.label,
            kind=input_data.link.kind,
            address=None if vetted.is_secret else vetted.address,
            sealed_address=(
                self._secret_cipher.encrypt(ChannelSecret(str(vetted.address)))
                if vetted.is_secret
                else None
            ),
            host=vetted.host,
            preview=vetted.preview,
            added_at=now,
        )

        def edit(settings: DepositSettingsDocument) -> DepositSettingsDocument:
            if len(settings.payment_links) >= MAX_PAYMENT_LINKS:
                raise ValidationFailedError(
                    f"A business keeps at most {MAX_PAYMENT_LINKS} payment pages."
                )

            settings.payment_links.append(link)
            if (
                settings.default_payment_link_id is None
                and link.kind is PaymentLinkKind.TEMPLATE
            ):
                settings.default_payment_link_id = link.id
            return settings

        return self._changes.apply(business, input_data.user_id, edit)
