"""Seams of numbers the platform rents for businesses (W21)."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.adapter_contract import AdapterContract
from app.contracts.registry_contract import RegistryContract
from app.contracts.repo_contract import RepoContract
from app.contracts.utility_contract import UtilityContract
from app.schemas.constants.phone_numbers import (
    PhoneNumberAvailability,
    PhoneNumberStatus,
    PhoneNumberType,
)
from app.schemas.domain.phone_numbers import (
    PhoneNumberDocument,
    PhoneNumberRequestDocument,
)
from app.schemas.dto.phone_numbers.provisioning import (
    PhoneNumberOfferClaims,
    PhoneNumberPurchase,
    PhoneNumberRelease,
    PhoneNumberSearchQuery,
    PhoneNumberSearchResult,
    ProvisionedPhoneNumber,
    VoicePlatformImport,
)
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
)
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.telephony.constrained_strings import (
    PhoneNumberOfferToken,
    RentedLineNumber,
)
from app.schemas.typings.telephony.prefixed_id import PhoneNumberId
from app.schemas.typings.telephony.strings import VoicePlatformPhoneNumberId

type PhoneNumberChange = Callable[[PhoneNumberDocument], PhoneNumberDocument | None]


class PhoneNumberProvisionerAdapterContract(AdapterContract, Protocol):
    """
    A carrier that rents numbers (search by country, kind and city; buy;
    give back), together with the voice platform the numbers answer on
    (import, assign to the business's agent, remove).
    """

    def list_missing_settings(self) -> list[EnvironmentVariableName]:
        """
        Server settings the carrier or the voice platform still needs
        before numbers can be rented here (empty when it is ready).
        """
        raise NotImplementedError

    def search_numbers(self, query: PhoneNumberSearchQuery) -> PhoneNumberSearchResult:
        """
        Numbers on offer now and the carrier's monthly price of the kind.
        Raises ExternalServiceError.
        """
        raise NotImplementedError

    def quote_monthly_cost(
        self, country_code: CountryCode, number_type: PhoneNumberType
    ) -> CostMicroUsd | None:
        """
        The carrier's monthly price of the kind in the country (None: it
        sells none there). Raises ExternalServiceError.
        """
        raise NotImplementedError

    def buy_number(self, purchase: PhoneNumberPurchase) -> ProvisionedPhoneNumber:
        """
        Rent exactly this number. Raises PhoneNumberUnavailableError when
        the carrier no longer has it, ExternalServiceError otherwise.
        """
        raise NotImplementedError

    def import_number(self, request: VoicePlatformImport) -> VoicePlatformPhoneNumberId:
        """
        Bring a rented number into the voice platform (assigned to the
        agent when one is given). Raises ExternalServiceError.
        """
        raise NotImplementedError

    def assign_agent(
        self,
        voice_platform_number_id: VoicePlatformPhoneNumberId,
        agent_id: VoiceAgentId | None,
    ) -> None:
        """
        Calls to the number reach this agent (None: no agent answers).
        Raises ExternalServiceError.
        """
        raise NotImplementedError

    def release_number(self, release: PhoneNumberRelease) -> None:
        """
        Remove the number from the voice platform, then return it to the
        carrier; a number either has already forgotten is not an error.
        Raises ExternalServiceError.
        """
        raise NotImplementedError


class PhoneNumberRepoContract(RepoContract, Protocol):
    """Numbers rented for businesses (1213)."""

    def save(self, number: PhoneNumberDocument) -> None:
        raise NotImplementedError

    def get(
        self, business_id: BusinessId, number_id: PhoneNumberId
    ) -> PhoneNumberDocument | None:
        raise NotImplementedError

    def find_held(self, business_id: BusinessId) -> PhoneNumberDocument | None:
        """The business's number that is ACTIVE or being given back, if any."""
        raise NotImplementedError

    def find_holder(self, phone_number: RentedLineNumber) -> PhoneNumberDocument | None:
        """
        Across businesses (call it platform-wide): the rental that holds
        this number now (ACTIVE or RELEASING), if any.
        """
        raise NotImplementedError

    def page_in_status(
        self,
        status: PhoneNumberStatus,
        after: PhoneNumberDocument | None,
        limit: DocumentQueryLimit,
    ) -> list[PhoneNumberDocument]:
        """
        Across businesses (platform-wide): numbers in this status after
        `after` (from the start without it), by when their next rental month
        begins (`billed_until`), then their first write; a keyset page, so
        a walk meets every number once however many share a month.
        """
        raise NotImplementedError

    def modify(
        self,
        business_id: BusinessId,
        number_id: PhoneNumberId,
        change: PhoneNumberChange,
    ) -> PhoneNumberDocument | None:
        """
        Change a stored number in one step (no other write in between);
        None, and nothing written, when it is missing or `change` declines.
        """
        raise NotImplementedError


class PhoneNumberRequestRepoContract(RepoContract, Protocol):
    """Requests for numbers the platform team arranges (1213), one per business."""

    def get_by_business(
        self, business_id: BusinessId
    ) -> PhoneNumberRequestDocument | None:
        raise NotImplementedError

    def open_request(self, request: PhoneNumberRequestDocument) -> bool:
        """
        Store the request as the business's open one, unless one is open
        already (atomic, also across processes); True when written now.
        """
        raise NotImplementedError

    def save(self, request: PhoneNumberRequestDocument) -> None:
        raise NotImplementedError

    def page_open(
        self,
        after: PhoneNumberRequestDocument | None,
        limit: DocumentQueryLimit,
    ) -> list[PhoneNumberRequestDocument]:
        """
        Across businesses (platform-wide): open requests, oldest first, the
        page after `after` (a keyset walk over all of them).
        """
        raise NotImplementedError


class PhoneNumberCountryRegistryContract(RegistryContract, Protocol):
    """Where an owner can pick a number in the cabinet and have it at once."""

    def get_availability(
        self, country_code: CountryCode, number_type: PhoneNumberType
    ) -> PhoneNumberAvailability:
        """
        SELF_SERVE where the platform rents this kind without papers,
        REQUIRES_DOCUMENTS where the regulator wants the business's
        documents (and in every country the registry does not list).
        """
        raise NotImplementedError

    def list_self_serve_countries(self) -> list[CountryCode]:
        raise NotImplementedError


class PhoneLineLockRegistryContract(RegistryContract, Protocol):
    def lock_for(self, business_id: BusinessId) -> AbstractContextManager[object]:
        """
        Lock serializing the changes of one business's phone line across
        every process (taking a number, giving it back, the jobs acting on
        it); the block may call the carrier and the voice platform.
        """
        raise NotImplementedError


class PhoneNumberOfferSignerContract(UtilityContract, Protocol):
    """Signs the numbers a search offers, so a rental takes only those."""

    def sign(self, claims: PhoneNumberOfferClaims) -> PhoneNumberOfferToken:
        """The offer's token (its expiry in clear, the rest signed)."""
        raise NotImplementedError

    def read_expiry(self, token: PhoneNumberOfferToken) -> Microseconds:
        """Until when the token says its offer holds (not yet verified)."""
        raise NotImplementedError

    def is_genuine(
        self, claims: PhoneNumberOfferClaims, token: PhoneNumberOfferToken
    ) -> bool:
        """
        True when this platform signed exactly these claims (the expiry
        included); whether the offer still holds is the caller's check.
        """
        raise NotImplementedError
