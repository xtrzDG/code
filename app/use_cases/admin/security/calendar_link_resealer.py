"""
Seal the secrets of resources' calendars again with the current key: the
addresses of imported iCal feeds and the booking systems' API keys, each
written back only if it did not change meanwhile (a feed replaced or a key
entered again is sealed with the current key already).
"""

from collections.abc import Callable

from app.contracts.calendar_sync import ResourceCalendarLinkRepoContract
from app.schemas.domain.calendar_sync import ResourceCalendarLinkDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.calendar_sync.prefixed_id import IcalImportFeedId
from app.schemas.typings.channels.strings import EncryptedChannelSecret

type Reseal = Callable[[EncryptedChannelSecret], EncryptedChannelSecret | None]


def reseal_calendar_links(
    link_repo: ResourceCalendarLinkRepoContract,
    business_id: BusinessId,
    reseal: Reseal,
) -> None:
    """Every calendar secret of the business under the current key."""

    for link in link_repo.list_by_business(business_id):
        feeds: dict[
            IcalImportFeedId, tuple[EncryptedChannelSecret, EncryptedChannelSecret]
        ] = {}
        for feed in link.ical_imports:
            sealed = reseal(feed.encrypted_url)
            if sealed is not None and sealed != feed.encrypted_url:
                feeds[feed.feed_id] = (feed.encrypted_url, sealed)

        key: tuple[EncryptedChannelSecret, EncryptedChannelSecret] | None = None
        if link.booking_system is not None:
            sealed_key = reseal(link.booking_system.encrypted_api_key)
            if (
                sealed_key is not None
                and sealed_key != link.booking_system.encrypted_api_key
            ):
                key = (link.booking_system.encrypted_api_key, sealed_key)

        if feeds or key is not None:
            link_repo.update(business_id, link.resource_id, replacing(feeds, key))


def replacing(
    feeds: dict[
        IcalImportFeedId, tuple[EncryptedChannelSecret, EncryptedChannelSecret]
    ],
    key: tuple[EncryptedChannelSecret, EncryptedChannelSecret] | None,
) -> Callable[[ResourceCalendarLinkDocument], ResourceCalendarLinkDocument | None]:
    def replace(
        stored: ResourceCalendarLinkDocument,
    ) -> ResourceCalendarLinkDocument | None:
        changed: bool = False
        for feed in stored.ical_imports:
            pair = feeds.get(feed.feed_id)
            if pair is not None and feed.encrypted_url == pair[0]:
                feed.encrypted_url = pair[1]
                changed = True
        system = stored.booking_system
        if (
            key is not None
            and system is not None
            and system.encrypted_api_key == key[0]
        ):
            system.encrypted_api_key = key[1]
            changed = True
        return stored if changed else None

    return replace
