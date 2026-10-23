"""The cabinet's phone card: the rented number, a request, what is on offer."""

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.phone_numbers import (
    PhoneNumberCountryRegistryContract,
    PhoneNumberProvisionerAdapterContract,
    PhoneNumberRepoContract,
    PhoneNumberRequestRepoContract,
)
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.phone_numbers import PhoneNumberDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.phone_numbers.phone_line import PhoneLineQuery, PhoneLineView
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.channels.phone_numbers.phone_line_lookups import (
    find_answering_agent,
)
from app.use_cases.channels.phone_numbers.phone_line_views import (
    build_open_request_view,
    build_rented_number_view,
)


class GetPhoneLineUseCase(UseCaseContract[PhoneLineQuery, PhoneLineView]):
    """
    Any member reads the business's phone line: the number the platform
    rents for it (active or being given back), the owner's open request for
    a number the team arranges, whether this server rents numbers by itself
    and in which countries an owner has one at once. The price reads in the
    display language (the owner's language by default).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        phone_number_repo: PhoneNumberRepoContract,
        phone_number_request_repo: PhoneNumberRequestRepoContract,
        phone_number_provisioner: PhoneNumberProvisionerAdapterContract,
        phone_number_country_registry: PhoneNumberCountryRegistryContract,
        phone_number_parser: PhoneNumberParserContract,
        assistant_version_repo: AssistantVersionRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._phone_number_repo: PhoneNumberRepoContract = phone_number_repo
        self._phone_number_request_repo: PhoneNumberRequestRepoContract = (
            phone_number_request_repo
        )
        self._provisioner: PhoneNumberProvisionerAdapterContract = (
            phone_number_provisioner
        )
        self._country_registry: PhoneNumberCountryRegistryContract = (
            phone_number_country_registry
        )
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )

    def run(self, input_data: PhoneLineQuery) -> PhoneLineView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id, business_id=input_data.business_id
            )
        )
        language: LanguageTag = input_data.display_language or business.owner_language
        held: PhoneNumberDocument | None = self._phone_number_repo.find_held(
            business.id
        )
        is_self_serve: bool = self._provisioner.list_missing_settings() == []
        return PhoneLineView(
            business_id=business.id,
            rented_number=(
                None
                if held is None
                else build_rented_number_view(
                    held,
                    self._phone_number_parser,
                    language,
                    find_answering_agent(self._assistant_version_repo, business.id)
                    is not None,
                )
            ),
            open_request=build_open_request_view(
                self._phone_number_request_repo.get_by_business(business.id)
            ),
            are_numbers_self_serve=is_self_serve,
            self_serve_countries=(
                self._country_registry.list_self_serve_countries()
                if is_self_serve
                else []
            ),
            default_country_code=business.country_code,
        )
