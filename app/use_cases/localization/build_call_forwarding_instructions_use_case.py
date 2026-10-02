from app.contracts.catalog_registries import CallForwardingGuideRegistryContract
from app.contracts.localization_utilities import (
    LocalizedTextResolverContract,
    PhoneNumberParserContract,
)
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.localization import CallForwardingCondition
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.catalog import (
    CallForwardingCode,
    CallForwardingCodeTemplate,
    CallForwardingGuide,
    CallForwardingInstructions,
    CallForwardingInstructionsQuery,
    CarrierForwardingInstructions,
)
from app.schemas.dto.localization import LocalizedText, PhoneNumberDetails
from app.schemas.exceptions.application_errors import (
    InvalidPhoneNumberError,
    ValidationFailedError,
)
from app.schemas.typings.localization.constrained_strings import (
    CallForwardingDialCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import (
    InstructionText,
    RawPhoneNumberInput,
)

NUMBER_PLACEHOLDER: str = "{number}"
CODE_PLACEHOLDER_NAMES: dict[CallForwardingCondition, str] = {
    CallForwardingCondition.NO_ANSWER: "no_answer_code",
    CallForwardingCondition.BUSY: "busy_code",
    CallForwardingCondition.UNREACHABLE: "unreachable_code",
    CallForwardingCondition.CANCEL_ALL: "cancel_code",
}


class BuildCallForwardingInstructionsUseCase(
    UseCaseContract[CallForwardingInstructionsQuery, CallForwardingInstructions]
):
    """
    Step-by-step forwarding of unanswered, busy and unreachable calls from the
    venue's own number to the assistant's number (concept section 6).

    The assistant's number is the `external_id` of the business's phone
    channel (E.164). Codes are filled with that number; texts are rendered in
    the display language with English as the fallback. Georgia also lists
    Magti, Silknet and Cellfie.

    Raises:
        ValidationFailedError: the business has no assistant phone number yet.
    """

    def __init__(
        self,
        channel_repo: ChannelRepoContract,
        phone_number_parser: PhoneNumberParserContract,
        call_forwarding_guide_registry: CallForwardingGuideRegistryContract,
        localized_text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._channel_repo: ChannelRepoContract = channel_repo
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._call_forwarding_guide_registry: CallForwardingGuideRegistryContract = (
            call_forwarding_guide_registry
        )
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )

    def run(
        self,
        input_data: CallForwardingInstructionsQuery,
    ) -> CallForwardingInstructions:
        business: BusinessDocument = input_data.business
        assistant_number: PhoneNumberDetails = self._find_assistant_number(input_data)
        guide: CallForwardingGuide = self._call_forwarding_guide_registry.get(
            business.country_code
        )
        language: LanguageTag = input_data.display_language
        codes: list[CallForwardingCode] = self._render_codes(
            guide.code_templates,
            assistant_number,
            language,
        )
        placeholder_values: dict[str, str] = {
            CODE_PLACEHOLDER_NAMES[code.condition]: str(code.dial_code)
            for code in codes
        }
        placeholder_values["number"] = str(assistant_number.international_format)
        return CallForwardingInstructions(
            business_id=business.id,
            country_code=business.country_code,
            display_language=language,
            assistant_phone_number=assistant_number.e164,
            assistant_phone_number_display=assistant_number.international_format,
            codes=codes,
            carriers=[
                CarrierForwardingInstructions(
                    carrier_name=carrier.carrier_name,
                    codes=self._render_codes(
                        carrier.code_templates,
                        assistant_number,
                        language,
                    ),
                    note=(
                        self._render_text(carrier.notes, language, placeholder_values)
                        if carrier.notes is not None
                        else None
                    ),
                )
                for carrier in guide.carriers
            ],
            steps=[
                self._render_text(step, language, placeholder_values)
                for step in guide.steps
            ],
            notes=[
                self._render_text(note, language, placeholder_values)
                for note in guide.notes
            ],
        )

    def _find_assistant_number(
        self,
        input_data: CallForwardingInstructionsQuery,
    ) -> PhoneNumberDetails:
        phone_channels: list[ChannelDocument] = sorted(
            (
                channel
                for channel in self._channel_repo.list_by_business(
                    input_data.business.id
                )
                if channel.kind is ChannelKind.PHONE
                and channel.external_id is not None
                and channel.status is not ChannelStatus.DISABLED
            ),
            key=lambda channel: (
                channel.status is not ChannelStatus.CONNECTED,
                int(channel.created_at),
            ),
        )
        if phone_channels == []:
            raise ValidationFailedError(
                "The assistant has no phone number yet. Connect the phone "
                "channel first, then set up call forwarding."
            )

        try:
            return self._phone_number_parser.parse(
                RawPhoneNumberInput(str(phone_channels[0].external_id)),
                input_data.business.country_code,
            )
        except InvalidPhoneNumberError as error:
            raise ValidationFailedError(
                "The assistant's phone number is not a valid phone number. "
                "Reconnect the phone channel."
            ) from error

    def _render_codes(
        self,
        code_templates: list[CallForwardingCodeTemplate],
        assistant_number: PhoneNumberDetails,
        language: LanguageTag,
    ) -> list[CallForwardingCode]:
        return [
            CallForwardingCode(
                condition=code_template.condition,
                dial_code=CallForwardingDialCode(
                    str(code_template.dial_code_template).replace(
                        NUMBER_PLACEHOLDER,
                        str(assistant_number.e164),
                    )
                ),
                description=InstructionText(
                    self._localized_text_resolver.resolve(
                        code_template.descriptions,
                        language,
                    )
                ),
            )
            for code_template in code_templates
        ]

    def _render_text(
        self,
        text: LocalizedText,
        language: LanguageTag,
        placeholder_values: dict[str, str],
    ) -> InstructionText:
        template: str = str(self._localized_text_resolver.resolve(text, language))
        return InstructionText(template.format_map(placeholder_values))
