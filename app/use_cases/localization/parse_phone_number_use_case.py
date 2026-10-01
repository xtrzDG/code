from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.catalog import ParsePhoneNumberRequest
from app.schemas.dto.localization import PhoneNumberDetails


class ParsePhoneNumberUseCase(
    UseCaseContract[ParsePhoneNumberRequest, PhoneNumberDetails]
):
    """
    Turn a phone number typed in any format into E.164 with its country, line
    kind and time zones, e.g. while a person from any country signs up.
    """

    def __init__(self, phone_number_parser: PhoneNumberParserContract) -> None:
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser

    def run(self, input_data: ParsePhoneNumberRequest) -> PhoneNumberDetails:
        return self._phone_number_parser.parse(
            input_data.raw_phone_number,
            input_data.country_hint,
        )
