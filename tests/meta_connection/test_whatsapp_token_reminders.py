"""
When a WhatsApp token is not renewed, `refresh_whatsapp_tokens` tells the
business's owners, once per token and stage: Meta refused (or the renewed
token failed its check), three days or less remain, or the token ended
(then the channel is put in ERROR too, without asking Meta). The old token
always stays as it was.
"""

import httpx
import pytest

from app.schemas.constants.channels import ChannelStatus
from app.schemas.constants.deliveries import DeliveryFailureReason
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.notifications import StaffLinkTarget
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.channels import ChannelDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelSecret, EncryptedChannelSecret
from app.use_cases.channels.meta_connection.refresh_whatsapp_tokens_use_case import (
    TOKEN_ENDED_ERROR,
)
from tests.live_events.recording_event_publisher import PublishedLiveEvent
from tests.meta_connection.token_refresh_fakes import (
    MANAGEMENT,
    MESSAGING,
    OTHER_WABA_ID,
    WABA_ID,
    graph_error,
)
from tests.meta_connection.token_refresh_world import (
    NEW_TOKEN,
    OLD_TOKEN,
    TokenRefreshWorld,
)
from tests.platform_ops.ops_documents import DAY, HOUR, MINUTE, at


def subject(channel: ChannelDocument, day: str, stage: str) -> str:
    """A reminder's subject: the channel, the day its token ends, the stage."""

    return f"whatsapp_token:{channel.id}-{day}-{stage}"


@pytest.mark.parametrize(
    ("status_code", "code"),
    [(400, 190), (401, 102), (403, 10), (400, 1)],
    ids=["token-refused", "credential-rejected", "forbidden", "request-refused"],
)
def test_a_refusal_keeps_the_old_token_and_tells_the_owners_once(
    status_code: int, code: int
) -> None:
    world = TokenRefreshWorld()
    channel = world.add_whatsapp(OLD_TOKEN, at(10 * DAY))
    world.meta.refuse(OLD_TOKEN, status_code=status_code, code=code)

    world.run()
    world.clock.advance(6 * HOUR)
    world.run()

    assert world.meta.renewed() == [OLD_TOKEN, OLD_TOKEN]
    assert world.token_of(channel) == OLD_TOKEN
    assert world.stored(channel).credential_expires_at == at(10 * DAY)
    assert world.audit_entries() == []
    assert world.alerts.subjects() == [subject(channel, "20261015", "refresh_refused")]
    assert len(world.alerts.raised) == 2  # The outbox keeps one of them.
    [alert] = world.alerts.queued
    assert alert.target is StaffLinkTarget.CHANNELS
    assert alert.member_roles == [BusinessMemberRole.OWNER]
    assert alert.event is None
    assert alert.is_urgent is False
    assert str(alert.tag) == f"whatsapp_token:{channel.id}"
    assert world.emails.mailed == [alert]


@pytest.mark.parametrize(
    ("account", "scopes", "renewed_end"),
    [
        (OTHER_WABA_ID, (MANAGEMENT, MESSAGING), 70 * DAY),
        (WABA_ID, (MANAGEMENT,), 70 * DAY),
        (WABA_ID, (MESSAGING,), 70 * DAY),
        (WABA_ID, (MANAGEMENT, MESSAGING), 10 * DAY),
        (WABA_ID, (MANAGEMENT, MESSAGING), 10 * DAY + 59 * MINUTE),
    ],
    ids=["other-account", "no-messaging", "no-management", "same-end", "too-short"],
)
def test_a_renewed_token_that_fails_its_check_is_never_stored(
    account: str, scopes: tuple[str, ...], renewed_end: int
) -> None:
    world = TokenRefreshWorld()
    channel = world.add_whatsapp(OLD_TOKEN, at(10 * DAY))
    world.meta.renew(OLD_TOKEN, NEW_TOKEN, at(renewed_end), account, scopes)

    world.run()

    assert world.token_of(channel) == OLD_TOKEN
    assert world.stored(channel).credential_expires_at == at(10 * DAY)
    assert world.audit_entries() == []
    assert world.alerts.subjects() == [subject(channel, "20261015", "refresh_refused")]


def test_a_renewed_token_meta_calls_invalid_is_never_stored() -> None:
    world = TokenRefreshWorld()
    channel = world.add_whatsapp(OLD_TOKEN, at(10 * DAY))
    world.meta.renewals[OLD_TOKEN] = (200, {"access_token": NEW_TOKEN})

    world.run()

    assert world.token_of(channel) == OLD_TOKEN
    assert world.alerts.subjects() == [subject(channel, "20261015", "refresh_refused")]


def test_a_token_that_cannot_be_read_is_refused_without_asking_meta() -> None:
    world = TokenRefreshWorld()
    channel = world.add_whatsapp(OLD_TOKEN, at(10 * DAY))
    unreadable = EncryptedChannelSecret("not-sealed-0000")
    world.channel_repo.save(channel.model_copy(update={"encrypted_secret": unreadable}))

    world.run()

    assert world.meta.requests == []
    assert world.stored(channel).encrypted_secret == unreadable
    assert world.alerts.subjects() == [subject(channel, "20261015", "refresh_refused")]


TEMPORARY_FAILURES: dict[str, tuple[int, object]] = {
    "rate_limit": (429, graph_error(4, "Application request limit reached")),
    "outage": (500, graph_error(2, "Service temporarily unavailable")),
    "transient": (
        400,
        {"error": {"message": "Please retry", "code": 2, "is_transient": True}},
    ),
}


@pytest.mark.parametrize("failure", ["network", *TEMPORARY_FAILURES])
def test_a_temporary_failure_tells_the_owners_only_in_the_last_three_days(
    failure: str,
) -> None:
    world = TokenRefreshWorld()
    channel = world.add_whatsapp(OLD_TOKEN, at(3 * DAY + MINUTE))
    if failure == "network":
        world.meta.failure = httpx.ConnectError("Meta is unreachable.")
    else:
        world.meta.renewals[OLD_TOKEN] = TEMPORARY_FAILURES[failure]

    world.run()
    assert world.alerts.raised == []

    world.clock.advance(MINUTE)
    world.run()

    assert world.token_of(channel) == OLD_TOKEN
    assert world.alerts.subjects() == [subject(channel, "20261008", "ending")]
    assert world.alerts.queued[0].is_urgent is False


def test_a_refusal_in_the_last_three_days_is_the_ending_reminder() -> None:
    world = TokenRefreshWorld()
    channel = world.add_whatsapp(OLD_TOKEN, at(2 * DAY))
    world.meta.refuse(OLD_TOKEN, status_code=401, code=102)

    world.run()

    assert world.alerts.subjects() == [subject(channel, "20261007", "ending")]


def test_an_ended_token_puts_the_channel_in_error_and_is_urgent_news() -> None:
    world = TokenRefreshWorld()
    channel = world.add_whatsapp(OLD_TOKEN, at(-HOUR))

    assert world.run() == 1
    world.clock.advance(6 * HOUR)
    world.run()

    assert world.meta.requests == []
    stored = world.stored(channel)
    assert stored.status is ChannelStatus.ERROR
    assert stored.last_error_reason is DeliveryFailureReason.CREDENTIAL_REJECTED
    assert str(stored.last_error) == TOKEN_ENDED_ERROR
    assert stored.last_error_at == at(0)
    assert world.token_of(channel) == OLD_TOKEN
    # Announced once: the second run finds it failing for that reason.
    assert world.live_events.events == [
        PublishedLiveEvent(
            world.business.id, LiveEventKind.CHANNEL_ERROR, (str(channel.id),)
        )
    ]
    assert world.alerts.subjects() == [subject(channel, "20261005", "ended")]
    assert world.alerts.queued[0].is_urgent is True
    assert world.emails.mailed == world.alerts.queued


def test_a_token_that_ended_weeks_ago_on_a_connected_channel_is_still_news() -> None:
    # Switched off by a business closure with its token; the closure was
    # cancelled weeks later, after the token had ended.
    world = TokenRefreshWorld()
    channel = world.add_whatsapp(OLD_TOKEN, at(-15 * DAY))
    handled = world.add_whatsapp("EAAfake-handled", at(-15 * DAY), ChannelStatus.ERROR)

    assert world.run() == 1
    world.clock.advance(6 * HOUR)
    assert world.run() == 0

    assert world.meta.requests == []
    stored = world.stored(channel)
    assert stored.status is ChannelStatus.ERROR
    assert stored.last_error_reason is DeliveryFailureReason.CREDENTIAL_REJECTED
    assert world.live_events.kinds() == [LiveEventKind.CHANNEL_ERROR]
    assert world.alerts.subjects() == [subject(channel, "20260920", "ended")]
    assert world.alerts.queued[0].is_urgent is True
    # In ERROR that long, a channel was handled when its token ended.
    assert world.stored(handled) == handled


def test_a_token_meta_keeps_refusing_gets_three_reminders_in_all() -> None:
    world = TokenRefreshWorld()
    channel = world.add_whatsapp(OLD_TOKEN, at(10 * DAY))
    world.meta.refuse(OLD_TOKEN)

    for _ in range(4 * 12):  # Every 6 hours, until two days after the end.
        world.run()
        world.clock.advance(6 * HOUR)

    assert world.alerts.subjects() == [
        subject(channel, "20261015", stage)
        for stage in ("refresh_refused", "ending", "ended")
    ]
    assert world.stored(channel).status is ChannelStatus.ERROR
    assert world.live_events.kinds() == [LiveEventKind.CHANNEL_ERROR]


def test_nobody_hears_of_a_token_the_owner_replaced_meanwhile() -> None:
    world = TokenRefreshWorld()
    ended = world.add_whatsapp(OLD_TOKEN, at(-HOUR))
    refused = world.add_whatsapp("EAAfake-refused", at(2 * DAY))

    def reconnect() -> None:
        for channel in (ended, refused):
            world.channel_repo.save(
                channel.model_copy(
                    update={
                        "encrypted_secret": world.cipher.encrypt(
                            ChannelSecret("EAAfake-reconnected")
                        )
                    }
                )
            )

    world.watch.after_listing = reconnect

    world.run()

    assert world.stored(ended).status is ChannelStatus.CONNECTED
    assert world.live_events.events == []
    assert world.alerts.raised == []


def test_a_token_found_working_meanwhile_is_not_called_ended() -> None:
    world = TokenRefreshWorld()
    channel = world.add_whatsapp(OLD_TOKEN, at(-HOUR))
    # The hourly check asks Meta right after the run listed the channel.
    world.watch.after_listing = lambda: world.channel_repo.save(
        channel.model_copy(update={"credential_expires_at": at(50 * DAY)})
    )

    assert world.run() == 0

    assert world.stored(channel).status is ChannelStatus.CONNECTED
    assert world.live_events.events == []
    assert world.alerts.raised == []


def test_one_failing_channel_never_stops_the_others() -> None:
    world = TokenRefreshWorld()
    broken = world.add_whatsapp("EAAfake-broken", at(-HOUR))
    channel = world.add_whatsapp(OLD_TOKEN, at(10 * DAY), business_id=BusinessId())
    world.meta.renew(OLD_TOKEN, NEW_TOKEN, at(70 * DAY))
    world.flaky_channels.failing.add(broken.id)

    assert world.run() == 1

    assert world.token_of(channel) == NEW_TOKEN
    assert world.stored(broken).status is ChannelStatus.CONNECTED


def test_a_channel_of_no_stored_business_gets_no_reminder() -> None:
    world = TokenRefreshWorld()
    world.add_whatsapp(OLD_TOKEN, at(10 * DAY), business_id=BusinessId())
    world.meta.refuse(OLD_TOKEN)

    assert world.run() == 0

    assert world.alerts.raised == []
