"""
Mass bookings and mass cancellations of one business (ABUSE-04, OWASP
OAT-021 denial of inventory): every announced booking change counts in the
business's hourly bucket, shared by every process. The new booking past
BOOKING_SURGE_PER_HOUR of an hour, and the cancellation past
CANCELLATION_SURGE_PER_HOUR, count the platform signal of the
`booking_spike` or `cancellation_spike` alert once, and a warning line
names the business (never a customer). Nothing is refused: the booking
caps (`booking_limits.py`) refuse, this only tells the platform team.

A booking announced as changed counts as a cancellation when it is
CANCELLED now and was written within RECENT_CHANGE_SECONDS (the change
just announced, not a later change of a booking cancelled long ago).
Owners' test chats are never announced, so they never count.
"""

import logging
from collections.abc import Generator, Sequence
from contextlib import contextmanager, nullcontext

from base_typed_id import BasePrefixedTypedId
from pydantic import ValidationError
from typed_time_provider import Microseconds, WallClock

from app.contracts.integrations import BusinessEventObserverContract
from app.contracts.monitoring import SignalCounterAdapterContract
from app.contracts.rate_limits import RateLimitBucketAdapterContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.storage import StorageScopeContract
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.constants.storage import StorageScopeKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.rate_limits import RateLimitCounter, RateLimitWindow
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import RateWindowSeconds
from app.schemas.typings.platform.constrained_strings import RateLimitKey
from app.utilities.limits.sliding_window_limits import locate_window
from app.utilities.monitoring.signal_windows import UNLIMITED

LOGGER: logging.Logger = logging.getLogger(__name__)
HOUR: RateWindowSeconds = RateWindowSeconds(60 * 60)
# A busy restaurant takes a few dozen bookings in its best hour; a script
# holding every slot takes far more. Cancellations come one at a time.
BOOKING_SURGE_PER_HOUR: int = 40
CANCELLATION_SURGE_PER_HOUR: int = 15
RECENT_CHANGE_SECONDS: int = 60
MICROSECONDS_PER_SECOND: int = 1_000_000
NEW_BOOKINGS_KEY: str = "booking-surge:new:"
CANCELLATIONS_KEY: str = "booking-surge:cancelled:"


class BookingSurgeObserverFacilitator(BusinessEventObserverContract):
    """Counts a business's new and cancelled bookings an hour (see the module)."""

    def __init__(
        self,
        booking_repo: BookingRepoContract,
        buckets: RateLimitBucketAdapterContract,
        signal_counter: SignalCounterAdapterContract,
        storage_scope: StorageScopeContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._booking_repo: BookingRepoContract = booking_repo
        self._buckets: RateLimitBucketAdapterContract = buckets
        self._signals: SignalCounterAdapterContract = signal_counter
        self._storage_scope: StorageScopeContract = storage_scope
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def notice(
        self,
        business_id: BusinessId,
        event: LiveEventKind,
        ids: Sequence[BasePrefixedTypedId],
    ) -> None:
        try:
            if event is LiveEventKind.BOOKING_CREATED:
                self._count(business_id, NEW_BOOKINGS_KEY, BOOKING_SURGE_PER_HOUR)
            elif event is LiveEventKind.BOOKING_CHANGED and self._is_cancellation(
                business_id, ids
            ):
                self._count(
                    business_id, CANCELLATIONS_KEY, CANCELLATION_SURGE_PER_HOUR
                )
        except (ApplicationError, ValidationError) as error:
            LOGGER.warning(
                "Booking surge of business %s was not counted: %s",
                business_id,
                type(error).__name__,
            )

    def _is_cancellation(
        self, business_id: BusinessId, ids: Sequence[BasePrefixedTypedId]
    ) -> bool:
        if not ids or not isinstance(ids[0], BookingId):
            return False

        with self._business_scope(business_id):
            booking: BookingDocument | None = self._booking_repo.get(
                business_id, ids[0]
            )
        if booking is None or booking.status is not BookingStatus.CANCELLED:
            return False

        age: int = int(self._wall_clock.now_unix()) - int(booking.updated_at)
        return age <= RECENT_CHANGE_SECONDS * MICROSECONDS_PER_SECOND

    def _count(self, business_id: BusinessId, prefix: str, surge: int) -> None:
        key = RateLimitKey(f"{prefix}{business_id}")
        window: RateLimitWindow = locate_window(self._wall_clock.now_unix(), HOUR)
        self._buckets.count_if_within(
            [RateLimitCounter(key=key, limit=UNLIMITED)], window
        )
        if int(self._buckets.read_counts(key, window).current_count) != surge + 1:
            return

        is_new: bool = prefix == NEW_BOOKINGS_KEY
        self._signals.count(
            PlatformSignal.BOOKING_SURGE if is_new else PlatformSignal.CANCELLATION_SURGE
        )
        LOGGER.warning(
            "Business %s had more than %s %s this hour",
            business_id,
            surge,
            "new bookings" if is_new else "cancellations",
        )

    @contextmanager
    def _business_scope(self, business_id: BusinessId) -> Generator[None]:
        """The change's own scope, or the business's when it ran unscoped."""

        unscoped: bool = self._storage_scope.current().kind is StorageScopeKind.UNSCOPED
        with (
            self._storage_scope.scoped_to_business(business_id)
            if unscoped
            else nullcontext()
        ):
            yield
