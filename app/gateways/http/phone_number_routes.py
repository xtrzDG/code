"""Cabinet /channels: a phone number for the assistant, rented or arranged."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.idempotency.idempotency_dependency import (
    NO_IDEMPOTENCY,
    IdempotencyDependency,
)
from app.gateways.http.language_negotiation import parse_language_parameter
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.query_parsing import parse_optional
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.phone_numbers import PhoneNumberType
from app.schemas.dto.phone_numbers.phone_line import (
    CancelPhoneNumberRequestCommand,
    PhoneLineQuery,
    PhoneLineView,
    PhoneNumberOfferList,
    PhoneNumberOfferQuery,
    PhoneNumberRequestBody,
    PhoneNumberRequestView,
    RentedPhoneNumberView,
    RentPhoneNumberCommand,
    RentPhoneNumberRequest,
    RequestPhoneNumberCommand,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.telephony.constrained_strings import PhoneNumberCityQuery
from app.schemas.typings.users.prefixed_id import UserId

PHONE_LINE_PATH: str = "/v1/businesses/{business_id}/phone-line"

read_rent_body = build_json_body_dependency(RentPhoneNumberRequest)
read_request_body = build_json_body_dependency(PhoneNumberRequestBody)


def build_phone_number_router(
    current_user: CurrentUserDependency,
    get_phone_line_operator: OperatorContract[PhoneLineQuery, PhoneLineView],
    search_phone_numbers_operator: OperatorContract[
        PhoneNumberOfferQuery, PhoneNumberOfferList
    ],
    rent_phone_number_operator: OperatorContract[
        RentPhoneNumberCommand, RentedPhoneNumberView
    ],
    request_phone_number_operator: OperatorContract[
        RequestPhoneNumberCommand, PhoneNumberRequestView
    ],
    cancel_phone_number_request_operator: OperatorContract[
        CancelPhoneNumberRequestCommand, None
    ],
    idempotent: IdempotencyDependency = NO_IDEMPOTENCY,
) -> APIRouter:
    """
    Routes (all require a bearer token; everything but reading is the owner's):
        GET    /v1/businesses/{business_id}/phone-line?language=
                    the rented number, an open request, where numbers are
                    self-serve (any member)
        GET    /v1/businesses/{business_id}/phone-line/offers
                    ?country=US&number_type=local&city=Austin&language=
                    numbers on offer and their monthly price (30 an hour)
        POST   /v1/businesses/{business_id}/phone-line/number
                    take one ({phone_number, number_type, monthly_price,
                    locality?}; step-up; Idempotency-Key) -> 201
        POST   /v1/businesses/{business_id}/phone-line/request
                    ask the team for one ({country_code, number_type, city?};
                    Idempotency-Key) -> 201
        DELETE /v1/businesses/{business_id}/phone-line/request
                    cancel the open request -> 204

    A rented number is given back by turning the phone channel off
    (DELETE /v1/businesses/{business_id}/channels/phone).
    """

    router = APIRouter(tags=["phone_numbers"], responses=standard_error_responses())

    @router.get(PHONE_LINE_PATH)
    def get_phone_line(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        language: str | None = None,
    ) -> PhoneLineView:
        return get_phone_line_operator.operate(
            PhoneLineQuery(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                display_language=parse_language_parameter(language),
            )
        )

    @router.get(f"{PHONE_LINE_PATH}/offers")
    def search_phone_numbers(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        country: str,
        number_type: str,
        city: str | None = None,
        language: str | None = None,
    ) -> PhoneNumberOfferList:
        country_code: CountryCode | None = parse_optional(
            country.strip().upper(), CountryCode, "country"
        )
        kind: PhoneNumberType | None = parse_optional(
            number_type, PhoneNumberType, "number_type"
        )
        if country_code is None or kind is None:
            raise ValidationFailedError(
                "Query parameters country and number_type are required."
            )

        return search_phone_numbers_operator.operate(
            PhoneNumberOfferQuery(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                country_code=country_code,
                number_type=kind,
                city=parse_optional(
                    None if city is None else city.strip(),
                    PhoneNumberCityQuery,
                    "city",
                ),
                display_language=parse_language_parameter(language),
            )
        )

    @router.post(
        f"{PHONE_LINE_PATH}/number",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(RentPhoneNumberRequest),
        dependencies=[Depends(idempotent)],
    )
    def rent_phone_number(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[RentPhoneNumberRequest, Depends(read_rent_body)],
        language: str | None = None,
    ) -> RentedPhoneNumberView:
        return rent_phone_number_operator.operate(
            RentPhoneNumberCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                request=body,
                client_ip_address=read_client_ip_address(request),
                display_language=parse_language_parameter(language),
            )
        )

    @router.post(
        f"{PHONE_LINE_PATH}/request",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(PhoneNumberRequestBody),
        dependencies=[Depends(idempotent)],
    )
    def request_phone_number(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[PhoneNumberRequestBody, Depends(read_request_body)],
    ) -> PhoneNumberRequestView:
        return request_phone_number_operator.operate(
            RequestPhoneNumberCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                request=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.delete(f"{PHONE_LINE_PATH}/request", status_code=status.HTTP_204_NO_CONTENT)
    def cancel_phone_number_request(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        cancel_phone_number_request_operator.operate(
            CancelPhoneNumberRequestCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router


def parse_business_id(raw_business_id: str) -> BusinessId:
    return parse_path_identifier(raw_business_id, BusinessId, "Business")
