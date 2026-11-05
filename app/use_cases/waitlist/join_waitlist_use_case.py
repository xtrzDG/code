from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.repositories.waitlist_repositories import (
    WaitlistEntryRepoContract,
    WaitlistSettingsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.waitlist import WaitlistStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.waitlist import WaitlistEntryDocument, WaitlistSettingsDocument
from app.schemas.dto.bookings import AvailabilityQuery, AvailabilityResult
from app.schemas.dto.growth.waitlist_joining import (
    JoinWaitlistCommand,
    WaitlistJoinReceipt,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.use_cases.shared.business_access import require_business
from app.use_cases.shared.proactive_routes import messenger_identities
from app.use_cases.waitlist.waitlist_wishes import (
    WaitlistWish,
    fitting_free_times,
    refuse_free_times,
    resolve_wish,
    wish_ends_at,
)
from app.utilities.scheduling.zoned_time import load_time_zone
from app.utilities.waitlist.waitlist_keys import waitlist_settings_id_of

OPEN_STATUSES: frozenset[WaitlistStatus] = frozenset(
    {WaitlistStatus.WAITING, WaitlistStatus.OFFERED}
)
# One customer waits for a few days at most (a flood is abuse).
MAX_OPEN_ENTRIES_PER_CUSTOMER: int = 3


class JoinWaitlistUseCase(UseCaseContract[JoinWaitlistCommand, WaitlistJoinReceipt]):
    """
    Put a customer on the business's waitlist for a local date (model tool
    join_waitlist), when nothing that fits is free: the date, the time
    window, the party, a stay's nights, the service and the resource they
    named are stored with the conversation, channel and language they wrote
    in, until the end of that window.

    Refused when the business keeps no waitlist, when free time already
    fits the wish (the model offers it instead), or when the customer
    waits for three days already; asking again for the same day updates
    the wish (an offered place stays offered). Test chats' entries are
    stored but never offered anything.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        waitlist_settings_repo: WaitlistSettingsRepoContract,
        waitlist_entry_repo: WaitlistEntryRepoContract,
        resource_repo: ResourceRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        contact_repo: ContactRepoContract,
        check_availability: UseCaseContract[AvailabilityQuery, AvailabilityResult],
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._settings_repo: WaitlistSettingsRepoContract = waitlist_settings_repo
        self._entry_repo: WaitlistEntryRepoContract = waitlist_entry_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._check_availability: UseCaseContract[
            AvailabilityQuery, AvailabilityResult
        ] = check_availability
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JoinWaitlistCommand) -> WaitlistJoinReceipt:
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        settings: WaitlistSettingsDocument = self._settings(business)
        if not settings.is_enabled:
            raise ValidationFailedError(
                "This business keeps no waitlist. Offer other dates or times, "
                "or pass the request to a colleague with create_lead."
            )

        now: Microseconds = self._wall_clock.now_unix()
        waits_until: Microseconds = wish_ends_at(
            input_data, load_time_zone(business.timezone)
        )
        if int(waits_until) <= int(now):
            raise ValidationFailedError("That time has already passed.")

        wish: WaitlistWish = resolve_wish(
            input_data,
            self._knowledge_item_repo.list_by_business(business.id),
            self._resource_repo.list_by_business(business.id),
        )
        self._refuse_when_free(input_data, wish)
        entry, is_already_waiting = self._store(input_data, wish, waits_until, now)
        self._live_events.publish(
            business.id,
            LiveEventKind.WAITLIST_CHANGED,
            (entry.id,),
            is_sandbox=entry.is_sandbox,
        )
        contact: ContactDocument | None = self._contact_repo.get(
            business.id, input_data.contact_id
        )
        return WaitlistJoinReceipt(
            entry_id=entry.id,
            date=entry.date,
            time_from=entry.time_from,
            time_to=entry.time_to,
            party_size=entry.party_size,
            nights=entry.nights,
            service_title=None if wish.service is None else wish.service.title,
            resource_name=None if wish.resource is None else wish.resource.name,
            hold_minutes=settings.hold_minutes,
            timezone=business.timezone,
            is_already_waiting=is_already_waiting,
            is_web_chat_only=(
                input_data.source_channel is ChannelKind.WEB_CHAT
                and (contact is None or not messenger_identities(contact, None))
            ),
        )

    def _settings(self, business: BusinessDocument) -> WaitlistSettingsDocument:
        return self._settings_repo.get_by_business(
            business.id
        ) or WaitlistSettingsDocument(
            id=waitlist_settings_id_of(business.id),
            business_id=business.id,
            created_at=business.created_at,
            updated_at=business.created_at,
        )

    def _refuse_when_free(
        self, command: JoinWaitlistCommand, wish: WaitlistWish
    ) -> None:
        result: AvailabilityResult = self._check_availability.run(
            AvailabilityQuery(
                business_id=command.business_id,
                date=command.date,
                resource_kind=command.resource_kind,
                resource_id=None if wish.resource is None else wish.resource.id,
                service_item_id=None if wish.service is None else wish.service.id,
                party_size=command.party_size,
                nights=command.nights,
                is_sandbox=command.is_sandbox,
                conversation_id=command.conversation_id,
                lists_every_time=True,
                contact_id=command.contact_id,
            )
        )
        free = fitting_free_times(result, command)
        if free:
            raise refuse_free_times(free)

    def _store(
        self,
        command: JoinWaitlistCommand,
        wish: WaitlistWish,
        waits_until: Microseconds,
        now: Microseconds,
    ) -> tuple[WaitlistEntryDocument, bool]:
        open_entries: list[WaitlistEntryDocument] = [
            entry
            for entry in self._entry_repo.list_of_contact(
                command.business_id, command.contact_id
            )
            if entry.status in OPEN_STATUSES and entry.is_sandbox == command.is_sandbox
        ]
        for entry in open_entries:
            if entry.date == command.date:
                return self._update_wish(entry, command, wish, waits_until, now), True

        if len(open_entries) >= MAX_OPEN_ENTRIES_PER_CUSTOMER:
            raise ValidationFailedError(
                "The customer already waits for "
                f"{MAX_OPEN_ENTRIES_PER_CUSTOMER} days; offer to replace one of "
                "them or pass the request to a colleague."
            )

        entry = WaitlistEntryDocument(
            business_id=command.business_id,
            contact_id=command.contact_id,
            source_channel=command.source_channel,
            language=command.language,
            date=command.date,
            party_size=command.party_size,
            waits_until=waits_until,
            is_sandbox=command.is_sandbox,
            created_at=now,
            updated_at=now,
        ).model_copy(update=wish_fields(command, wish, waits_until))
        self._entry_repo.save(entry)
        return entry, False

    def _update_wish(
        self,
        entry: WaitlistEntryDocument,
        command: JoinWaitlistCommand,
        wish: WaitlistWish,
        waits_until: Microseconds,
        now: Microseconds,
    ) -> WaitlistEntryDocument:
        if entry.status is not WaitlistStatus.WAITING:
            return entry

        def rewish(current: WaitlistEntryDocument) -> WaitlistEntryDocument | None:
            if current.status is not WaitlistStatus.WAITING:
                return None

            return current.model_copy(
                update={**wish_fields(command, wish, waits_until), "updated_at": now}
            )

        return self._entry_repo.update(command.business_id, entry.id, rewish) or entry


def wish_fields(
    command: JoinWaitlistCommand, wish: WaitlistWish, waits_until: Microseconds
) -> dict[str, object]:
    """The stored fields of a wish (the same for a new entry and an update)."""

    return {
        "contact_name": command.contact_name,
        "conversation_id": command.conversation_id,
        "source_channel": command.source_channel,
        "language": command.language,
        "date": command.date,
        "time_from": command.time_from,
        "time_to": command.time_to,
        "party_size": command.party_size,
        "nights": command.nights,
        "resource_kind": command.resource_kind,
        "resource_id": None if wish.resource is None else wish.resource.id,
        "service_item_id": None if wish.service is None else wish.service.id,
        "notes": command.notes,
        "waits_until": waits_until,
        "is_sandbox": command.is_sandbox,
    }
