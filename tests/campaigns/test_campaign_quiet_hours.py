"""
Marketing respects the night in the business's time zone (Tbilisi in the
growth world, UTC+4): a campaign writes nothing from 21:00 to 09:00 there
(the due visits wait for the morning) and a message the outbox has not
delivered by 21:00 is dropped. Its WhatsApp template is its own MARKETING
template, never a service message's utility template.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from typed_time_provider import Microseconds

from app.schemas.configurations.app_settings import AppSettings
from app.use_cases.campaigns.marketing_template import (
    dedicated_marketing_template,
    service_template_names,
)
from app.use_cases.campaigns.quiet_hours import is_quiet_hour, quiet_hours_start
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.campaigns.campaign_world import CampaignWorld

VISIT_STARTS: str = "2026-09-04T19:00:00+04:00"
VISIT_ENDS: str = "2026-09-04T21:00:00+04:00"
TBILISI: ZoneInfo = ZoneInfo("Asia/Tbilisi")
ROME: ZoneInfo = ZoneInfo("Europe/Rome")


def at(moment: str) -> Microseconds:
    return Microseconds(int(datetime.fromisoformat(moment).timestamp()) * 1_000_000)


@pytest.mark.parametrize(
    ("moment", "is_quiet"),
    [
        ("2026-10-05T08:59:59+02:00", True),
        ("2026-10-05T09:00:00+02:00", False),
        ("2026-10-05T20:59:59+02:00", False),
        ("2026-10-05T21:00:00+02:00", True),
        ("2026-10-05T23:30:00+02:00", True),
        ("2026-10-05T03:00:00+02:00", True),
    ],
)
def test_the_quiet_hours_run_from_nine_in_the_evening_to_nine_in_the_morning(
    moment: str, is_quiet: bool
) -> None:
    assert is_quiet_hour(at(moment), ROME) is is_quiet


def test_the_quiet_hours_begin_at_the_next_local_nine_in_the_evening() -> None:
    assert quiet_hours_start(at("2026-10-05T10:00:00+02:00"), ROME) == at(
        "2026-10-05T21:00:00+02:00"
    )
    assert quiet_hours_start(at("2026-10-05T22:00:00+02:00"), ROME) == at(
        "2026-10-06T21:00:00+02:00"
    )
    # The night the clocks go back in Rome: 21:00 is still local 21:00.
    assert quiet_hours_start(at("2026-10-25T12:00:00+01:00"), ROME) == at(
        "2026-10-25T21:00:00+01:00"
    )


def due_world(now: str) -> tuple[CampaignWorld, int]:
    world = CampaignWorld(now=datetime.fromisoformat(now))
    world.enable()
    guest = world.guest("Giulia", "en")
    world.visit(guest, VISIT_STARTS, VISIT_ENDS)
    return world, len(world.messages_of(guest))


def test_a_campaign_writes_nothing_at_night_in_the_business_time_zone() -> None:
    # 22:30 in Tbilisi (18:30 UTC): the visit is due, the night holds it.
    world, decided = due_world("2026-10-05T18:30:00+00:00")

    report = world.run_campaigns()

    assert decided == 0
    assert int(report.processed_count) == 0
    assert world.outbox_texts() == []


def test_the_morning_run_writes_what_the_night_held() -> None:
    world, _ = due_world("2026-10-05T18:30:00+00:00")
    world.run_campaigns()

    world.clock.move_to(datetime.fromisoformat("2026-10-06T05:00:00+00:00"))
    report = world.run_campaigns()

    assert int(report.processed_count) == 1
    assert len(world.outbox_texts()) == 1


def test_a_message_is_dropped_rather_than_delivered_after_nine_at_night() -> None:
    # 20:00 in Tbilisi: written now, given up at 21:00 if still undelivered.
    world, _ = due_world("2026-10-05T16:00:00+00:00")

    assert int(world.run_campaigns().processed_count) == 1
    [message] = world.outbox_messages()
    assert message.send_before == at("2026-10-05T21:00:00+04:00")
    assert quiet_hours_start(at("2026-10-05T20:00:00+04:00"), TBILISI) == at(
        "2026-10-05T21:00:00+04:00"
    )


def settings_with(**templates: str) -> AppSettings:
    """The campaign's template "comeback_marketing" and these service ones."""

    return assemble_app_settings(
        {
            "WHATSAPP_REBOOKING_TEMPLATE": "comeback_marketing",
            **{
                f"WHATSAPP_{name.upper()}_TEMPLATE": value
                for name, value in templates.items()
            },
        }
    )


def test_the_campaign_keeps_its_own_marketing_template() -> None:
    settings = settings_with(reminder="booking_reminder")

    assert dedicated_marketing_template(settings) == "comeback_marketing"
    assert service_template_names(settings) == frozenset({"booking_reminder"})
    assert dedicated_marketing_template(assemble_app_settings({})) is None


@pytest.mark.parametrize(
    "service", ["reminder", "booking_confirmation", "notification", "waitlist"]
)
def test_a_service_messages_utility_template_never_carries_a_campaign(
    service: str,
) -> None:
    settings = settings_with(**{service: "comeback_marketing"})

    assert dedicated_marketing_template(settings) is None
