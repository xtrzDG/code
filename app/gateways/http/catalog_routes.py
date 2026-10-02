"""
HTTP routes of the catalog: countries, languages, plan quotes, phone number
parsing and call forwarding instructions for businesses in any country.
"""

from typing import Annotated

from base_typed_id import BaseTypedIdError
from fastapi import APIRouter, Depends, Query

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.catalog.call_forwarding import (
    CallForwardingInstructions,
    CallForwardingInstructionsRequest,
)
from app.schemas.dto.catalog.countries import (
    CountryList,
    CountryListRequest,
    CountryProfileRequest,
    CountryProfileView,
    LanguageList,
    LanguageListRequest,
    ParsePhoneNumberRequest,
)
from app.schemas.dto.catalog.plan_quotes import PlanQuoteList, PlanQuoteRequest
from app.schemas.dto.localization import PhoneNumberDetails
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    UnknownCountryError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.localization.language_tags import parse_language_tag

DEFAULT_DISPLAY_LANGUAGE: str = "en"
MAX_RAW_COUNTRY_CODE_LENGTH: int = 8

type ListCountriesOperator = OperatorContract[CountryListRequest, CountryList]
type GetCountryProfileOperator = OperatorContract[
    CountryProfileRequest, CountryProfileView
]
type ListLanguagesOperator = OperatorContract[LanguageListRequest, LanguageList]
type QuotePlansOperator = OperatorContract[PlanQuoteRequest, PlanQuoteList]
type ParsePhoneNumberOperator = OperatorContract[
    ParsePhoneNumberRequest, PhoneNumberDetails
]
type CallForwardingInstructionsOperator = OperatorContract[
    CallForwardingInstructionsRequest, CallForwardingInstructions
]


def build_catalog_router(
    list_countries_operator: ListCountriesOperator,
    get_country_profile_operator: GetCountryProfileOperator,
    list_languages_operator: ListLanguagesOperator,
    quote_plans_operator: QuotePlansOperator,
    parse_phone_number_operator: ParsePhoneNumberOperator,
    call_forwarding_instructions_operator: CallForwardingInstructionsOperator,
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Public catalog routes plus the cabinet route for call forwarding.

    - GET  /v1/catalog/countries?language=
    - GET  /v1/catalog/countries/{country_code}?language=
    - GET  /v1/catalog/languages?language=
    - GET  /v1/catalog/plans?country_code=&language=
    - POST /v1/phone-numbers/parse
    - GET  /v1/businesses/{business_id}/call-forwarding-instructions?language=
      (Bearer token; owners and staff of the business)

    `language` is a BCP 47 tag ("ka", "pt-BR"); catalog routes default to
    English, the forwarding route to the owner language of the business.
    """

    router = APIRouter()

    @router.get("/v1/catalog/countries")
    def list_countries(
        language: Annotated[str, Query()] = DEFAULT_DISPLAY_LANGUAGE,
    ) -> CountryList:
        return list_countries_operator.operate(
            CountryListRequest(display_language=parse_language_tag(language))
        )

    @router.get("/v1/catalog/countries/{country_code}")
    def get_country_profile(
        country_code: str,
        language: Annotated[str, Query()] = DEFAULT_DISPLAY_LANGUAGE,
    ) -> CountryProfileView:
        return get_country_profile_operator.operate(
            CountryProfileRequest(
                country_code=parse_country_code(country_code),
                display_language=parse_language_tag(language),
            )
        )

    @router.get("/v1/catalog/languages")
    def list_languages(
        language: Annotated[str, Query()] = DEFAULT_DISPLAY_LANGUAGE,
    ) -> LanguageList:
        return list_languages_operator.operate(
            LanguageListRequest(display_language=parse_language_tag(language))
        )

    @router.get("/v1/catalog/plans")
    def quote_plans(
        country_code: Annotated[str, Query()],
        language: Annotated[str, Query()] = DEFAULT_DISPLAY_LANGUAGE,
    ) -> PlanQuoteList:
        return quote_plans_operator.operate(
            PlanQuoteRequest(
                country_code=parse_country_code(country_code),
                display_language=parse_language_tag(language),
            )
        )

    @router.post("/v1/phone-numbers/parse")
    def parse_phone_number(request: ParsePhoneNumberRequest) -> PhoneNumberDetails:
        return parse_phone_number_operator.operate(request)

    @router.get("/v1/businesses/{business_id}/call-forwarding-instructions")
    def get_call_forwarding_instructions(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        language: Annotated[str | None, Query()] = None,
    ) -> CallForwardingInstructions:
        display_language: LanguageTag | None = (
            parse_language_tag(language) if language is not None else None
        )
        return call_forwarding_instructions_operator.operate(
            CallForwardingInstructionsRequest(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                display_language=display_language,
            )
        )

    return router


def parse_country_code(raw_country_code: str) -> CountryCode:
    """
    "ge" -> CountryCode("GE") at the transport boundary.

    Raises:
        UnknownCountryError: not an ISO 3166-1 alpha-2 shaped code.
    """

    normalized_code: str = raw_country_code.strip().upper()
    if len(normalized_code) <= MAX_RAW_COUNTRY_CODE_LENGTH:
        try:
            return CountryCode(normalized_code)
        except ValueError:
            pass

    raise UnknownCountryError(
        "Country must be an ISO 3166-1 alpha-2 code such as 'GE' or 'US'."
    )


def parse_business_id(raw_business_id: str) -> BusinessId:
    """
    Raises:
        NotFoundError: the id cannot belong to any business.
    """

    try:
        return BusinessId(raw_business_id)
    except (BaseTypedIdError, ValueError) as error:
        raise NotFoundError("Business was not found.") from error
