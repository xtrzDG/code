from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.notifications import StaffTextStyle
from app.schemas.dto.notifications.staff_alerts import StaffNotificationTextInput
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.notifications.staff_alert_texts import LINK_LINE
from app.utilities.scheduling.localized_formatting import choose_template_language


class StaffNotificationTextTransformer(
    TransformerContract[StaffNotificationTextInput, MessageText]
):
    """
    The text one staff recipient gets: the detailed text (a linked chat)
    or the brief title and line (e-mail, SMS), then "Open: <link>" in the
    recipient's language when the cabinet's address is known. The first
    line is the title (an e-mail's subject).
    """

    def __init__(self, text_resolver: LocalizedTextResolverContract) -> None:
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def transform(self, input_data: StaffNotificationTextInput) -> MessageText:
        lines: list[str] = []
        if input_data.style is StaffTextStyle.DETAILED and input_data.detailed:
            lines.append(str(input_data.detailed))
        elif input_data.brief is not None:
            lines.append(str(input_data.brief.title))
            if input_data.brief.detail is not None:
                lines.append(str(input_data.brief.detail))

        if input_data.link is not None:
            language: LanguageTag = choose_template_language(
                LINK_LINE, input_data.language
            )
            # The address stays as it is (no direction marks around it), so
            # every app recognises the link.
            text: str = str(self._text_resolver.resolve(LINK_LINE, language))
            lines.append(text.format(link=str(input_data.link)))

        return MessageText("\n".join(lines))
