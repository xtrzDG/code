from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.support_settings import SupportSettings
from app.schemas.dto.help import SupportContactsQuery, SupportContactsView
from app.schemas.typings.help.constrained_strings import SupportLinkUrl


class GetSupportContactsUseCase(
    UseCaseContract[SupportContactsQuery, SupportContactsView]
):
    """
    GET /v1/support/contacts: how owners reach a person at the platform
    (SUPPORT_WHATSAPP, SUPPORT_TELEGRAM, SUPPORT_EMAIL) with links that
    open the chat or the e-mail at once. Public: someone who cannot sign
    in needs it most.
    """

    def __init__(self, support_settings: SupportSettings) -> None:
        self._settings: SupportSettings = support_settings

    def run(self, input_data: SupportContactsQuery) -> SupportContactsView:
        settings: SupportSettings = self._settings
        number = settings.whatsapp_number
        username = settings.telegram_username
        email = settings.email
        return SupportContactsView(
            whatsapp_number=number,
            whatsapp_url=(
                None
                if number is None
                else SupportLinkUrl(f"https://wa.me/{number.removeprefix('+')}")
            ),
            telegram_username=username,
            telegram_url=(
                None if username is None else SupportLinkUrl(f"https://t.me/{username}")
            ),
            email=email,
            email_url=None if email is None else SupportLinkUrl(f"mailto:{email}"),
        )
