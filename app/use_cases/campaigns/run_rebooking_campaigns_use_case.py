"""Background job: the owners' rebooking campaigns write to their customers."""

import logging
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.campaign_repositories import (
    CampaignMessageRepoContract,
    CampaignSettingsRepoContract,
)
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.customer_repositories import (
    CustomerSegmentRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.campaigns import (
    CampaignAudience,
    CampaignMessageStatus,
    RebookingRuleKind,
)
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.campaigns import CampaignSettingsDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.typings.campaigns.constrained_strings import CampaignMonthKey
from app.schemas.typings.campaigns.prefixed_id import CampaignMessageId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.campaigns.campaign_targets import came_back, due_bookings
from app.use_cases.campaigns.campaign_writer import CampaignWriter
from app.use_cases.shared.customer_segment_members import (
    SegmentReaders,
    members_among,
)
from app.utilities.campaigns.campaign_keys import (
    campaign_message_id_of,
    campaign_month_of,
)
from app.utilities.scheduling.zoned_time import load_time_zone

LOGGER: logging.Logger = logging.getLogger(__name__)
MICROSECONDS_PER_DAY: int = 24 * 60 * 60 * 1_000_000
# A customer hears from a campaign at most once in two weeks.
MIN_GAP_DAYS: int = 14
INVITING_RULES: frozenset[RebookingRuleKind] = frozenset(
    {RebookingRuleKind.REBOOK, RebookingRuleKind.RECALL}
)


class RunRebookingCampaignsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Periodic job (hourly, across businesses): every live business whose
    campaign is on writes about the bookings its rule finds, once per
    booking: an invitation back the rule's days after a visit the customer
    did not follow with a new booking, a recall when a regular check is
    due, or a pre-arrival note the rule's days before an arrival. With a
    segment as audience only its members hear from it. A customer hears
    from a campaign at most once in two weeks, and a business sends at most
    its monthly cap in a calendar month of its time zone; STOP, the
    suppression list and a block always win. One business failing never
    stops the others.
    """

    def __init__(
        self,
        campaign_settings_repo: CampaignSettingsRepoContract,
        campaign_message_repo: CampaignMessageRepoContract,
        business_repo: BusinessRepoContract,
        booking_repo: BookingRepoContract,
        contact_repo: ContactRepoContract,
        customer_segment_repo: CustomerSegmentRepoContract,
        segment_readers: SegmentReaders,
        writer: CampaignWriter,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._settings_repo: CampaignSettingsRepoContract = campaign_settings_repo
        self._message_repo: CampaignMessageRepoContract = campaign_message_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._segment_repo: CustomerSegmentRepoContract = customer_segment_repo
        self._readers: SegmentReaders = segment_readers
        self._writer: CampaignWriter = writer
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        sent: int = 0
        for settings in self._settings_repo.list_enabled():
            business: BusinessDocument | None = self._business_repo.get(
                settings.business_id
            )
            if business is None or business.status is not BusinessStatus.LIVE:
                continue

            try:
                sent += self._run_business(business, settings)
            except Exception:  # noqa: BLE001 - one business never stops the others
                LOGGER.exception("The campaign of %s failed this hour.", business.id)

        return JobReport(processed_count=ProcessedItemCount(sent))

    def _run_business(
        self, business: BusinessDocument, settings: CampaignSettingsDocument
    ) -> int:
        now: Microseconds = self._wall_clock.now_unix()
        zone: ZoneInfo = load_time_zone(business.timezone)
        month: CampaignMonthKey = campaign_month_of(now, zone)
        left: int = int(settings.monthly_cap) - int(
            self._message_repo.count_sent_in_month(business.id, month)
        )
        if left <= 0:
            return 0

        due: list[BookingDocument] = self._undecided(business, settings, now)
        contacts: dict[ContactId, ContactDocument] = self._contact_repo.get_many(
            business.id, list({booking.contact_id for booking in due})
        )
        audience: set[ContactId] | None = self._audience(
            business, settings, contacts, now
        )
        sent: int = 0
        for booking in due:
            if sent >= left:
                LOGGER.info("The campaign of %s reached its monthly cap.", business.id)
                break

            if audience is not None and booking.contact_id not in audience:
                continue

            if self._heard_lately(business, booking.contact_id, now):
                continue

            if self._writer.write(
                business,
                settings.rule_kind,
                booking,
                contacts.get(booking.contact_id),
                month,
                zone,
                now,
            ):
                sent += 1

        if sent:
            LOGGER.info("The campaign of %s wrote to %d customers.", business.id, sent)

        return sent

    def _undecided(
        self,
        business: BusinessDocument,
        settings: CampaignSettingsDocument,
        now: Microseconds,
    ) -> list[BookingDocument]:
        """
        The due bookings no message was decided for yet, one per customer
        (their latest), and for an invitation only visits not followed by
        a new booking.
        """

        latest: dict[ContactId, BookingDocument] = {}
        for booking in due_bookings(self._booking_repo, settings, now):
            current = latest.get(booking.contact_id)
            if current is None or int(booking.starts_at) > int(current.starts_at):
                latest[booking.contact_id] = booking

        ids: dict[CampaignMessageId, BookingDocument] = {
            campaign_message_id_of(business.id, settings.rule_kind, booking.id): booking
            for booking in latest.values()
        }
        decided = self._message_repo.get_many(business.id, list(ids))
        return sorted(
            (
                booking
                for message_id, booking in ids.items()
                if message_id not in decided
                and (
                    settings.rule_kind not in INVITING_RULES
                    or not came_back(self._readers.history_repo, business.id, booking)
                )
            ),
            key=lambda booking: int(booking.starts_at),
        )

    def _audience(
        self,
        business: BusinessDocument,
        settings: CampaignSettingsDocument,
        contacts: dict[ContactId, ContactDocument],
        now: Microseconds,
    ) -> set[ContactId] | None:
        """The members among these customers, or None: everyone may hear."""

        if settings.audience is CampaignAudience.ALL_CUSTOMERS:
            return None

        segment = (
            None
            if settings.segment_id is None
            else self._segment_repo.get(business.id, settings.segment_id)
        )
        if segment is None:
            return set()

        return members_among(
            self._readers, business.id, segment.rules, now, list(contacts.values())
        )

    def _heard_lately(
        self, business: BusinessDocument, contact_id: ContactId, now: Microseconds
    ) -> bool:
        since: int = int(now) - MIN_GAP_DAYS * MICROSECONDS_PER_DAY
        return any(
            message.status is not CampaignMessageStatus.SKIPPED
            and message.sent_at is not None
            and int(message.sent_at) >= since
            for message in self._message_repo.list_of_contact(business.id, contact_id)
        )
