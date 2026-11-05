"""
A sign-in from a country none of the person's live sessions was opened or
used from is told to them even from a known device, and the notice names
the country in the reader's language; without a country database only
the device counts.
"""

from app.schemas.typings.compliance.strings import ClientIpAddress
from tests.notifications.alert_world import AlertWorld
from tests.users.access.session_steps import HOME_IP, MAC_CHROME
from tests.users.access.test_sign_in_notices import build_notices, owner_of, session
from tests.users.fake_ip_countries import FixedIpCountries

ROME_IP: str = "198.51.100.80"
MILAN_IP: str = "198.51.100.81"
BERLIN_IP: str = "192.0.2.90"
COUNTRIES: dict[str, str] = {
    HOME_IP: "GE",
    ROME_IP: "IT",
    MILAN_IP: "IT",
    BERLIN_IP: "DE",
}


def test_a_known_device_in_a_new_country_is_told_with_the_country() -> None:
    world = AlertWorld()
    world.add_device(world.owner, "en")
    notices = build_notices(world, FixedIpCountries(COUNTRIES))

    notices.notice_new_device(
        owner_of(world, "owner@salobie.example"),
        session(world, MAC_CHROME, BERLIN_IP),
        [session(world, MAC_CHROME, ROME_IP)],
    )

    [push] = world.push_queue.queued
    assert push.is_urgent is True
    assert "new country" in str(push.brief.title)
    assert "Germany" in str(push.brief.detail)
    assert BERLIN_IP in str(push.brief.detail)
    [(_, text)] = world.notifier.sent
    assert "Accesso al tuo account da un nuovo paese" in str(text)
    assert "Germania" in str(text)
    assert "Nessuna delle tue altre sessioni" in str(text)


def test_the_same_country_or_an_unknown_one_adds_nothing() -> None:
    world = AlertWorld()
    world.add_device(world.owner, "en")
    countries = FixedIpCountries(COUNTRIES)
    notices = build_notices(world, countries)
    owner = owner_of(world)

    # Rome then Milan: Italy both times, the same device.
    notices.notice_new_device(
        owner,
        session(world, MAC_CHROME, MILAN_IP),
        [session(world, MAC_CHROME, ROME_IP)],
    )
    # An address the database does not place.
    notices.notice_new_device(
        owner,
        session(world, MAC_CHROME, "203.0.113.200"),
        [session(world, MAC_CHROME, ROME_IP)],
    )

    assert world.push_queue.queued == []


def test_where_the_other_sessions_were_last_used_counts_too() -> None:
    world = AlertWorld()
    world.add_device(world.owner, "en")
    notices = build_notices(world, FixedIpCountries(COUNTRIES))
    travelled = session(world, MAC_CHROME, ROME_IP)
    travelled.last_seen_ip = ClientIpAddress(BERLIN_IP)

    notices.notice_new_device(
        owner_of(world), session(world, MAC_CHROME, BERLIN_IP), [travelled]
    )

    assert world.push_queue.queued == []


def test_without_a_country_database_a_known_device_tells_nobody() -> None:
    world = AlertWorld()
    world.add_device(world.owner, "en")

    build_notices(world).notice_new_device(
        owner_of(world),
        session(world, MAC_CHROME, BERLIN_IP),
        [session(world, MAC_CHROME, ROME_IP)],
    )

    assert world.push_queue.queued == []
