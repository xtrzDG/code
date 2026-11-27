"""
`refresh_whatsapp_tokens` renews the business's own WhatsApp token before
it ends: which tokens it asks Meta about, what it stores (the renewed
token, its end, an audit entry without an actor), and what it never
undoes (a reconnect meanwhile) or loses (a key rotation's reseal).
"""

import logging

import pytest

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ChannelSecret
from app.utilities.channels.whatsapp_token_schedule import REFRESHES_PER_RUN
from tests.meta_connection.token_refresh_world import (
    APP_ID,
    APP_SECRET,
    NEW_TOKEN,
    OLD_TOKEN,
    TokenRefreshWorld,
)
from tests.platform_ops.ops_documents import DAY, HOUR, MINUTE, at


def test_a_token_that_ends_within_the_window_is_renewed() -> None:
    world = TokenRefreshWorld()
    channel = world.add_whatsapp(OLD_TOKEN, at(10 * DAY))
    world.meta.renew(OLD_TOKEN, NEW_TOKEN, at(70 * DAY))

    assert world.run() == 1

    stored = world.stored(channel)
    assert world.token_of(channel) == NEW_TOKEN
    assert stored.credential_expires_at == at(70 * DAY)
    assert stored.credential_checked_at == at(0)
    assert stored.updated_at == at(0)
    assert stored.status is ChannelStatus.CONNECTED
    [entry] = world.audit_entries()
    assert (entry.action, str(entry.entity), str(entry.entity_id)) == (
        AuditAction.UPDATE,
        "channel",
        str(channel.id),
    )
    assert entry.actor_id is None
    renewal, check = world.meta.requests
    assert renewal.url.path == "/v23.0/oauth/access_token"
    assert dict(renewal.url.params) == {
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": OLD_TOKEN,
        "set_token_expires_in_60_days": "true",
    }
    assert check.url.path == "/v23.0/debug_token"
    assert check.url.params["input_token"] == NEW_TOKEN
    # The old token is never revoked, and a renewal is no news for owners.
    assert world.alerts.raised == []
    assert world.emails.mailed == []
    assert world.live_events.events == []


def test_only_whatsapp_tokens_of_its_own_within_the_window_are_renewed() -> None:
    world = TokenRefreshWorld()
    edge = world.add_whatsapp("EAAfake-edge", at(15 * DAY - 1))
    left_alone = [
        world.add_whatsapp("EAAfake-later", at(15 * DAY)),
        world.add_whatsapp("EAAfake-never", None),
        world.add_whatsapp(
            "EAAfake-instagram", at(2 * DAY), kind=ChannelKind.INSTAGRAM
        ),
        world.add_whatsapp(
            "EAAfake-messenger", at(2 * DAY), kind=ChannelKind.MESSENGER
        ),
        world.add_whatsapp(None, at(2 * DAY)),
        world.add_whatsapp(None, at(-HOUR)),
        world.add_whatsapp("EAAfake-off", at(2 * DAY), ChannelStatus.DISABLED),
        world.add_whatsapp("EAAfake-new", at(2 * DAY), ChannelStatus.PENDING),
        # In ERROR since its token ended over a week ago: handled back then.
        world.add_whatsapp("EAAfake-long-gone", at(-7 * DAY - 1), ChannelStatus.ERROR),
    ]
    world.meta.renew("EAAfake-edge", NEW_TOKEN, at(70 * DAY))

    assert world.run() == 1

    assert world.meta.renewed() == ["EAAfake-edge"]
    assert world.token_of(edge) == NEW_TOKEN
    assert [world.stored(channel) for channel in left_alone] == left_alone
    assert world.alerts.raised == []
    assert world.live_events.events == []


def test_the_window_is_meta_token_refresh_days() -> None:
    early = TokenRefreshWorld(refresh_days="30")
    channel = early.add_whatsapp(OLD_TOKEN, at(20 * DAY))
    early.meta.renew(OLD_TOKEN, NEW_TOKEN, at(70 * DAY))
    default = TokenRefreshWorld()
    default.add_whatsapp(OLD_TOKEN, at(20 * DAY))

    assert early.run() == 1
    assert default.run() == 0

    assert early.token_of(channel) == NEW_TOKEN
    assert default.meta.requests == []


def test_with_the_whole_sixty_days_a_renewed_token_is_renewed_again() -> None:
    # META_TOKEN_REFRESH_DAYS=60 renews a fresh token at the next run, and
    # again at every run after it: a few hours later is still later.
    world = TokenRefreshWorld(refresh_days="60")
    channel = world.add_whatsapp(OLD_TOKEN, at(59 * DAY))
    world.meta.renew(OLD_TOKEN, NEW_TOKEN, at(60 * DAY))
    world.meta.renew(NEW_TOKEN, "EAAfake-token-3", at(60 * DAY + 6 * HOUR))

    assert world.run() == 1
    world.clock.advance(6 * HOUR)
    assert world.run() == 1

    assert world.token_of(channel) == "EAAfake-token-3"
    assert world.stored(channel).credential_expires_at == at(60 * DAY + 6 * HOUR)
    assert len(world.audit_entries()) == 2
    assert world.alerts.raised == []


def test_a_renewed_token_without_an_end_is_stored_and_left_alone_after() -> None:
    # `debug_token` names no end (`expires_at` 0): later than any end.
    world = TokenRefreshWorld()
    channel = world.add_whatsapp(OLD_TOKEN, at(10 * DAY))
    world.meta.renew(OLD_TOKEN, NEW_TOKEN, None)

    assert world.run() == 1

    stored = world.stored(channel)
    assert world.token_of(channel) == NEW_TOKEN
    assert stored.credential_expires_at is None
    assert stored.credential_checked_at == at(0)
    [entry] = world.audit_entries()
    assert (entry.action, entry.actor_id) == (AuditAction.UPDATE, None)
    assert world.alerts.raised == []
    assert world.emails.mailed == []
    # A token that never ends is out of the window: Meta is not asked again.
    asked = len(world.meta.requests)
    world.clock.advance(6 * HOUR)
    assert world.run() == 0
    assert len(world.meta.requests) == asked


def test_a_reconnect_meanwhile_keeps_the_reconnects_token() -> None:
    world = TokenRefreshWorld()
    channel = world.add_whatsapp(OLD_TOKEN, at(10 * DAY))
    world.meta.renew(OLD_TOKEN, NEW_TOKEN, at(70 * DAY))
    reconnected = channel.model_copy(
        update={
            "encrypted_secret": world.cipher.encrypt(
                ChannelSecret("EAAfake-reconnected")
            ),
            "credential_expires_at": at(60 * DAY),
            "credential_checked_at": at(0),
        }
    )
    world.meta.before_renewal = lambda: world.channel_repo.save(reconnected)

    assert world.run() == 0

    assert world.stored(channel) == reconnected
    assert world.audit_entries() == []
    assert world.alerts.raised == []


def test_a_channel_switched_off_meanwhile_stays_off_without_a_token() -> None:
    world = TokenRefreshWorld()
    channel = world.add_whatsapp(OLD_TOKEN, at(10 * DAY))
    world.meta.renew(OLD_TOKEN, NEW_TOKEN, at(70 * DAY))
    switched_off = channel.model_copy(
        update={
            "status": ChannelStatus.DISABLED,
            "encrypted_secret": None,
            "external_id": None,
            "credential_expires_at": None,
            "credential_checked_at": None,
        }
    )
    world.meta.before_renewal = lambda: world.channel_repo.save(switched_off)

    assert world.run() == 0

    assert world.stored(channel) == switched_off
    assert world.audit_entries() == []


def test_a_reseal_meanwhile_still_stores_the_renewed_token() -> None:
    world = TokenRefreshWorld()
    channel = world.add_whatsapp(OLD_TOKEN, at(10 * DAY))
    world.meta.renew(OLD_TOKEN, NEW_TOKEN, at(70 * DAY))
    resealed = channel.model_copy(
        update={"encrypted_secret": world.cipher.encrypt(ChannelSecret(OLD_TOKEN))}
    )
    assert resealed.encrypted_secret != channel.encrypted_secret
    world.meta.before_renewal = lambda: world.channel_repo.save(resealed)

    assert world.run() == 1

    assert world.token_of(channel) == NEW_TOKEN
    assert world.stored(channel).credential_expires_at == at(70 * DAY)
    assert len(world.audit_entries()) == 1


def test_one_run_renews_a_bounded_number_of_tokens_soonest_first() -> None:
    world = TokenRefreshWorld()
    tokens = [f"EAAfake-{index:04d}" for index in range(REFRESHES_PER_RUN + 3)]
    for index, token in enumerate(reversed(tokens)):
        world.add_whatsapp(
            token, at(DAY + (len(tokens) - index) * MINUTE), business_id=BusinessId()
        )
        world.meta.renew(token, f"{token}-renewed", at(70 * DAY))

    assert world.run() == REFRESHES_PER_RUN
    assert world.meta.renewed() == tokens[:REFRESHES_PER_RUN]

    world.clock.advance(6 * HOUR)
    assert world.run() == 3
    assert world.meta.renewed() == tokens


def test_without_the_meta_app_the_run_does_nothing() -> None:
    world = TokenRefreshWorld(has_meta_app=False)
    world.add_whatsapp(OLD_TOKEN, at(DAY))
    ended = world.add_whatsapp("EAAfake-ended", at(-HOUR))

    assert world.run() == 0

    assert world.meta.requests == []
    assert world.stored(ended).status is ChannelStatus.CONNECTED
    assert world.alerts.raised == []


def test_no_token_and_no_secret_reach_the_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    world = TokenRefreshWorld()
    renewed = world.add_whatsapp(OLD_TOKEN, at(10 * DAY))
    refused = world.add_whatsapp("EAAfake-refused", at(9 * DAY))
    world.meta.renew(OLD_TOKEN, NEW_TOKEN, at(70 * DAY))
    world.meta.refuse("EAAfake-refused")

    with caplog.at_level(logging.DEBUG):
        world.run()

    written = "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name.startswith("app.")
    )
    assert str(renewed.id) in written
    assert str(refused.id) in written
    for secret in (OLD_TOKEN, NEW_TOKEN, "EAAfake-refused", APP_SECRET):
        assert secret not in written
