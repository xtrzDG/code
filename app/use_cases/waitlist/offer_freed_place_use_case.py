from typed_time_provider import Microseconds, WallClock

from app.contracts.calendar_sync import (
    BusyTimeSyncFacilitatorContract,
    CalendarBusyTimesRepoContract,
)
from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.operations import BusinessLockRegistryContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.repositories.knowledge_repositories import ResourceRepoContract
from app.contracts.repositories.waitlist_repositories import (
    WaitlistEntryRepoContract,
    WaitlistSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.waitlist import WaitlistStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.domain.waitlist import WaitlistEntryDocument, WaitlistOffer
from app.schemas.dto.growth.freed_places import FreedPlace
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.waitlist.constrained_integers import WaitlistHoldMinutes
from app.use_cases.waitlist.offer_delivery import (
    OfferPlan,
    OfferReceipt,
    WaitlistOfferDelivery,
)
from app.use_cases.waitlist.place_holding import hold_ends_at, hold_for, is_place_free
from app.utilities.calendar_sync.busy_periods import blocked_times_of
from app.utilities.calendar_sync.busy_windows import ON_DEMAND_READ_SECONDS
from app.utilities.scheduling.zoned_time import load_time_zone
from app.utilities.waitlist.offer_jobs import decode_freed_place
from app.utilities.waitlist.place_matching import describe_freed_place, entry_fits

SECONDS_PER_MINUTE: int = 60
DEFAULT_HOLD_MINUTES: WaitlistHoldMinutes = WaitlistHoldMinutes(30)
# The longest queue one freed place is matched against, first come first.
WAITING_LIMIT: DocumentQueryLimit = DocumentQueryLimit(500)


class OfferFreedPlaceUseCase(UseCaseContract[QueuedJobInput, JobReport]):
    """
    Queued job (`offer_freed_place`): a cancellation or a move freed a
    place; offer it to the first customer on the waitlist it fits (oldest
    first: the day, their time window, the party, the kind, a named master
    or room, the service, a stay's nights) who can be reached now.

    Under the business's booking lock the place is checked to be still
    free (no booking and no other hold takes its unit, and no calendar
    outside the platform made the resource busy then, its busy times read
    again first when stale, as availability does) and the customer's
    entry becomes OFFERED with the place held until the business's hold
    ends (or the online-booking notice before the place starts, whichever
    is first; with under five minutes left nothing is offered). Then the
    offer goes to the customer in their language. Businesses that are not
    live or keep no waitlist, test bookings and places nobody fits are
    left alone.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        waitlist_settings_repo: WaitlistSettingsRepoContract,
        waitlist_entry_repo: WaitlistEntryRepoContract,
        booking_repo: BookingRepoContract,
        resource_repo: ResourceRepoContract,
        lock_registry: BusinessLockRegistryContract,
        delivery: WaitlistOfferDelivery,
        live_events: EventPublisherFacilitatorContract,
        busy_times_repo: CalendarBusyTimesRepoContract,
        busy_time_sync: BusyTimeSyncFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._settings_repo: WaitlistSettingsRepoContract = waitlist_settings_repo
        self._entry_repo: WaitlistEntryRepoContract = waitlist_entry_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._lock_registry: BusinessLockRegistryContract = lock_registry
        self._delivery: WaitlistOfferDelivery = delivery
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._busy_times_repo: CalendarBusyTimesRepoContract = busy_times_repo
        self._busy_time_sync: BusyTimeSyncFacilitatorContract = busy_time_sync
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: QueuedJobInput) -> JobReport:
        place: FreedPlace = decode_freed_place(input_data.payload)
        business: BusinessDocument | None = (
            None
            if input_data.business_id is None
            else self._business_repo.get(input_data.business_id)
        )
        if business is None or business.status is not BusinessStatus.LIVE:
            return JobReport()

        settings = self._settings_repo.get_by_business(business.id)
        if settings is not None and not settings.is_enabled:
            return JobReport()

        freed: BookingDocument | None = self._booking_repo.get(
            business.id, place.freed_booking_id
        )
        resource: ResourceDocument | None = self._resource_repo.get(
            business.id, place.resource_id
        )
        if freed is None or freed.is_sandbox or resource is None:
            return JobReport()

        now: Microseconds = self._wall_clock.now_unix()
        profile = self._profile_repo.get_by_business(business.id)
        expires_at: Microseconds | None = hold_ends_at(
            place,
            DEFAULT_HOLD_MINUTES if settings is None else settings.hold_minutes,
            None if profile is None else profile.booking_rules,
            now,
        )
        if expires_at is None or not resource.is_active:
            return JobReport()

        held = self._hold(business, place, resource, freed, expires_at, now)
        if held is None:
            return JobReport()

        self._send(business, *held)
        return JobReport(processed_count=ProcessedItemCount(1))

    def _hold(
        self,
        business: BusinessDocument,
        place: FreedPlace,
        resource: ResourceDocument,
        freed: BookingDocument,
        expires_at: Microseconds,
        now: Microseconds,
    ) -> tuple[WaitlistEntryDocument, OfferPlan] | None:
        """The first customer who fits and can be reached, now holding the place."""

        facts = describe_freed_place(
            place, resource, freed, load_time_zone(business.timezone)
        )
        # The busy times of the resource's calendars, read again when stale,
        # as availability reads them (before the lock: it may call out).
        self._busy_time_sync.refresh_stale(business.id, ON_DEMAND_READ_SECONDS)
        blocked = blocked_times_of(self._busy_times_repo.list_by_business(business.id))
        buffer_seconds: int = int(freed.buffer_minutes or 0) * SECONDS_PER_MINUTE
        offer = WaitlistOffer(
            freed_booking_id=freed.id,
            resource_id=resource.id,
            starts_at=place.starts_at,
            ends_at=place.ends_at,
            buffer_minutes=freed.buffer_minutes,
            service_item_id=freed.service_item_id,
            value_minor=freed.value_minor,
            currency_code=freed.currency_code,
            offered_at=now,
        )
        with self._lock_registry.lock_for(business.id):
            if not is_place_free(
                self._booking_repo,
                self._entry_repo,
                place,
                resource,
                buffer_seconds,
                now,
                blocked,
            ):
                return None

            for entry in self._entry_repo.list_in_status(
                business.id, WaitlistStatus.WAITING, WAITING_LIMIT
            ):
                if not entry_fits(entry, facts):
                    continue

                plan: OfferPlan | None = self._delivery.plan(business, entry, now)
                if plan is None:
                    continue

                channel = (
                    entry.source_channel
                    if plan.route is None
                    else plan.route.identity.channel
                )
                held = hold_for(self._entry_repo, entry, offer, expires_at, channel)
                if held is not None:
                    return held, plan

        return None

    def _send(
        self, business: BusinessDocument, entry: WaitlistEntryDocument, plan: OfferPlan
    ) -> None:
        if entry.offer is None:
            return

        receipt: OfferReceipt = self._delivery.deliver(
            business,
            entry,
            entry.offer,
            plan,
            load_time_zone(business.timezone),
        )

        def note(current: WaitlistEntryDocument) -> WaitlistEntryDocument | None:
            if current.offer is None:
                return None

            current.offer = current.offer.model_copy(
                update={
                    "channel": receipt.channel,
                    "conversation_id": (
                        None
                        if receipt.conversation is None
                        else receipt.conversation.id
                    ),
                }
            )
            return current

        self._entry_repo.update(business.id, entry.id, note)
        self._live_events.publish(
            business.id, LiveEventKind.WAITLIST_CHANGED, (entry.id,)
        )
