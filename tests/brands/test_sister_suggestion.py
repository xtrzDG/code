"""
When nothing is free at a brand's location, the assistant's availability
answer names the brand's other live locations that are free, each asked
in its own storage scope; a location on its own, staff's full-day view
and a free location get the plain answer.
"""

from collections.abc import Callable, Generator
from contextlib import contextmanager

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.use_case_contract import UseCaseContract
from app.repositories.business_repositories import (
    BusinessProfileRepository,
    BusinessRepository,
)
from app.schemas.constants.bookings import BookingUnit
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import (
    BusinessAddress,
    BusinessContacts,
    BusinessProfileDocument,
)
from app.schemas.dto.bookings import (
    AvailabilityQuery,
    AvailabilityResult,
    AvailableSlot,
)
from app.schemas.dto.storage import StorageScope
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import AddressText, BusinessName
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.sharing.constrained_strings import BusinessPublicSlug
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.brands.check_availability_with_sisters_use_case import (
    CheckAvailabilityWithSistersUseCase,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.brands.brand_builders import build_brand, build_location

DATE = LocalDate("2026-10-16")
OWNER = UserId()


class RecordingScope(StorageScopeContext):
    def __init__(self) -> None:
        super().__init__()
        self.entered: list[BusinessId] = []

    @contextmanager
    def scoped_to_business(self, business_id: BusinessId) -> Generator[StorageScope]:
        with super().scoped_to_business(business_id) as scope:
            self.entered.append(business_id)
            yield scope


class FreeTimes(UseCaseContract[AvailabilityQuery, AvailabilityResult]):
    """Each location's free times, as the booking rules would find them."""

    def __init__(
        self, free: dict[BusinessId, list[str]], scope: RecordingScope
    ) -> None:
        self._free = free
        self._scope = scope
        self.asked_in: list[tuple[BusinessId, BusinessId | None]] = []

    def run(self, input_data: AvailabilityQuery) -> AvailabilityResult:
        entered = self._scope.entered[-1] if self._scope.entered else None
        self.asked_in.append((input_data.business_id, entered))
        return AvailabilityResult(
            timezone=TimezoneName("Asia/Tbilisi"),
            is_open_on_date=True,
            slots=[
                AvailableSlot(
                    resource_id=ResourceId(),
                    resource_name=ResourceName("Table 4"),
                    booking_unit=BookingUnit.TIME_SLOT,
                    date=input_data.date,
                    time=LocalTimeOfDay(time),
                )
                for time in self._free.get(input_data.business_id, [])
            ],
        )


def live(
    location: BusinessDocument, name: str, slug: str | None = None
) -> BusinessDocument:
    return location.model_copy(
        update={
            "name": BusinessName(name),
            "status": BusinessStatus.LIVE,
            "public_slug": None if slug is None else BusinessPublicSlug(slug),
        }
    )


def world(
    free: Callable[[list[BusinessDocument]], dict[BusinessId, list[str]]],
) -> tuple[
    CheckAvailabilityWithSistersUseCase,
    FreeTimes,
    RecordingScope,
    list[BusinessDocument],
]:
    brand = build_brand(OWNER)
    here = live(build_location(brand, OWNER, 1), "Mtsvane Ezo Vera")
    vake = live(build_location(brand, OWNER, 2), "Mtsvane Ezo Vake", "mtsvane-vake")
    resting = build_location(brand, OWNER, 3)  # Not live yet.
    full = live(build_location(brand, OWNER, 4), "Mtsvane Ezo Batumi")
    outsider = live(build_location(None, OWNER, 5), "Somebody else")
    locations = [here, vake, resting, full, outsider]
    business_repo = BusinessRepository(
        InMemoryDocumentCollectionAdapter[BusinessDocument](BusinessDocument)
    )
    for location in locations:
        business_repo.save(location)
    profiles = BusinessProfileRepository(
        InMemoryDocumentCollectionAdapter[BusinessProfileDocument](
            BusinessProfileDocument
        )
    )
    profiles.save(
        BusinessProfileDocument(
            business_id=vake.id,
            niche_key=NicheKey.RESTAURANT,
            answers_language=LanguageTag("ka"),
            address=BusinessAddress(text=AddressText("Chavchavadze Ave 10")),
            contacts=BusinessContacts(
                public_phone_number=E164PhoneNumber("+995322000111")
            ),
        )
    )
    scope = RecordingScope()
    free_times = FreeTimes(free(locations), scope)
    use_case = CheckAvailabilityWithSistersUseCase(
        check_availability=free_times,
        business_repo=business_repo,
        business_profile_repo=profiles,
        storage_scope=scope,
        app_settings=assemble_app_settings(
            {"CABINET_BASE_URL": "https://cabinet.example.com"}
        ),
    )
    return use_case, free_times, scope, locations


def question(business: BusinessDocument, **extra: object) -> AvailabilityQuery:
    return AvailabilityQuery.model_validate(
        {"business_id": business.id, "date": DATE, "time": "20:00", **extra}
    )


def test_a_full_location_suggests_its_free_live_sisters() -> None:
    def free(locations: list[BusinessDocument]) -> dict[BusinessId, list[str]]:
        _, vake, resting, _, outsider = locations
        return {
            vake.id: ["19:30", "20:00", "20:30", "21:00"],
            resting.id: ["20:00"],
            outsider.id: ["20:00"],
        }

    use_case, free_times, scope, locations = world(free)
    here, vake, resting, full, outsider = locations

    result = use_case.run(question(here))

    assert result.slots == []
    [option] = result.sister_locations
    assert option.name == vake.name
    assert option.free_times == ["19:30", "20:00", "20:30"]
    assert option.address == "Chavchavadze Ave 10"
    assert option.phone_number == "+995322000111"
    assert option.chat_url is not None and "mtsvane-vake" in str(option.chat_url)
    # Live sisters only, each asked inside its own scope; never others.
    assert scope.entered == [vake.id, full.id]
    assert (vake.id, vake.id) in free_times.asked_in
    assert all(
        asked not in (resting.id, outsider.id) for asked, _ in free_times.asked_in
    )


def test_a_free_location_or_a_lone_business_gets_the_plain_answer() -> None:
    def free(locations: list[BusinessDocument]) -> dict[BusinessId, list[str]]:
        here, vake, *_ = locations
        return {here.id: ["20:00"], vake.id: ["20:00"]}

    use_case, _, scope, locations = world(free)
    here, *_, outsider = locations

    assert use_case.run(question(here)).sister_locations == []
    assert use_case.run(question(outsider)).sister_locations == []
    assert scope.entered == []


def test_staff_full_day_view_never_asks_the_sisters() -> None:
    def free(locations: list[BusinessDocument]) -> dict[BusinessId, list[str]]:
        return {locations[1].id: ["20:00"]}

    use_case, _, scope, locations = world(free)

    result = use_case.run(question(locations[0], full_day=True))

    assert result.sister_locations == []
    assert scope.entered == []
