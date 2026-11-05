from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.storage import StorageScopeContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.bookings import AvailabilityQuery, AvailabilityResult
from app.schemas.dto.brands.sister_locations import SisterLocationOption
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.knowledge.strings import ServiceReference
from app.utilities.channels.channel_links import build_hosted_chat_url

MAX_SISTER_LOCATIONS: int = 3
MAX_SISTER_TIMES: int = 3


class CheckAvailabilityWithSistersUseCase(
    UseCaseContract[AvailabilityQuery, AvailabilityResult]
):
    """
    The assistant's check_availability for a brand's location: when
    nothing is free there, the brand's other live locations (up to three,
    oldest first) are asked the same question (date, time, party, length,
    nights, the service by its name), each inside its own storage scope,
    and those with free times come back as `sister_locations` with their
    address, phone and chat page. The customer is offered them; nothing
    is booked or read there but free times. Staff's full-day view, a
    guest moving their booking and a business on its own get the plain
    answer.
    """

    def __init__(
        self,
        check_availability: UseCaseContract[AvailabilityQuery, AvailabilityResult],
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        storage_scope: StorageScopeContract,
        app_settings: AppSettings,
    ) -> None:
        self._check_availability: UseCaseContract[
            AvailabilityQuery, AvailabilityResult
        ] = check_availability
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._storage_scope: StorageScopeContract = storage_scope
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: AvailabilityQuery) -> AvailabilityResult:
        result: AvailabilityResult = self._check_availability.run(input_data)
        if result.slots or not is_customer_question(input_data):
            return result

        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None or business.brand_id is None:
            return result

        sisters: list[BusinessDocument] = [
            location
            for location in self._business_repo.list_by_brand(business.brand_id)
            if location.id != business.id and location.status is BusinessStatus.LIVE
        ][:MAX_SISTER_LOCATIONS]
        sister_query = AvailabilityQuery(
            business_id=business.id,
            date=input_data.date,
            resource_kind=input_data.resource_kind,
            service_reference=(
                ServiceReference(str(result.service.title))
                if result.service is not None
                else input_data.service_reference
            ),
            time=input_data.time,
            party_size=input_data.party_size,
            duration_minutes=input_data.duration_minutes,
            nights=input_data.nights,
            is_sandbox=input_data.is_sandbox,
        )
        options: list[SisterLocationOption] = [
            option
            for sister in sisters
            if (option := self._ask(sister, sister_query)) is not None
        ]
        return result.model_copy(update={"sister_locations": options})

    def _ask(
        self,
        sister: BusinessDocument,
        query: AvailabilityQuery,
    ) -> SisterLocationOption | None:
        """The sister's free times on the date, or None (nothing free, or
        the question does not fit it: an unknown service, a party it
        cannot seat)."""

        try:
            with self._storage_scope.scoped_to_business(sister.id):
                found: AvailabilityResult = self._check_availability.run(
                    query.model_copy(update={"business_id": sister.id})
                )
                profile: BusinessProfileDocument | None = (
                    self._business_profile_repo.get_by_business(sister.id)
                )
        except NotFoundError, ValidationFailedError:
            return None

        if not found.slots:
            return None

        base_url = self._app_settings.cabinet_base_url
        return SisterLocationOption(
            name=sister.name,
            city=sister.city,
            address=None
            if profile is None or profile.address is None
            else profile.address.text,
            maps_url=None
            if profile is None or profile.address is None
            else profile.address.maps_url,
            phone_number=None
            if profile is None
            else profile.contacts.public_phone_number,
            chat_url=None
            if base_url is None or sister.public_slug is None
            else build_hosted_chat_url(base_url, str(sister.public_slug)),
            timezone=found.timezone,
            date=query.date,
            free_times=list(
                dict.fromkeys(
                    slot.time for slot in found.slots if slot.time is not None
                )
            )[:MAX_SISTER_TIMES],
            has_free_stay=any(slot.nights is not None for slot in found.slots),
        )


def is_customer_question(query: AvailabilityQuery) -> bool:
    """A customer asking (not staff's full day, not a guest moving a booking)."""

    return (
        not query.full_day
        and not query.lists_every_time
        and query.excluded_booking_id is None
    )
