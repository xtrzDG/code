"""
A customer can set off at most five requests and three staff alerts of
handoffs in 24 hours in conversations, so an anonymous visitor cannot flood
the team; an emergency always alerts, the business's own requests (public
API, no conversation) are not capped, test chats never count, and the next
day starts afresh.
"""

from datetime import datetime, timedelta

import pytest

from app.schemas.constants.bookings import LeadType
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffStatus, HandoffUrgency
from app.schemas.dto.bookings import CreateLeadCommand, LeadView
from app.schemas.exceptions.application_errors import RateLimitedError
from app.schemas.typings.bookings.strings import LeadDetails
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.conversations.contact_daily_caps import (
    MAX_HANDOFF_ALERTS_PER_CONTACT_PER_DAY,
    MAX_LEADS_PER_CONTACT_PER_DAY,
)
from tests.operations.handoff_fixture import HandoffFixture
from tests.operations.operations_world import OperationsWorld

MONDAY_NOON: datetime = datetime.fromisoformat("2026-10-05T12:00:00+04:00")


class LeadFlood:
    def __init__(self) -> None:
        self.world = OperationsWorld(MONDAY_NOON)
        self.business = self.world.add_business()
        self.contact = self.world.add_contact(self.business, "Visitor")
        self.conversation = self.world.add_conversation(
            self.business, self.contact, ChannelKind.WEB_CHAT
        )

    def request(self, is_sandbox: bool = False, in_chat: bool = True) -> LeadView:
        return self.world.create_lead().run(
            CreateLeadCommand(
                business_id=self.business.id,
                contact_id=self.contact.id,
                conversation_id=self.conversation.id if in_chat else None,
                lead_type=LeadType.OTHER,
                details=LeadDetails("Call me back"),
                source_channel=ChannelKind.WEB_CHAT,
                language=LanguageTag("en"),
                is_sandbox=is_sandbox,
            )
        )

    def next_day(self) -> None:
        later = MONDAY_NOON + timedelta(hours=24, minutes=1)
        self.world.clock.move_to(later)
        self.conversation = self.world.add_conversation(
            self.business, self.contact, ChannelKind.WEB_CHAT, created_at=later
        )


def test_a_contact_makes_five_requests_a_day() -> None:
    flood = LeadFlood()
    for _ in range(MAX_LEADS_PER_CONTACT_PER_DAY):
        flood.request()
    alerts = len(flood.world.notifier.sent)

    with pytest.raises(RateLimitedError, match="already made 5 requests today"):
        flood.request()

    assert len(flood.world.lead_repo.list_by_business(flood.business.id)) == 5
    assert len(flood.world.notifier.sent) == alerts
    flood.next_day()
    assert flood.request().id is not None


def test_requests_of_the_business_without_a_conversation_are_not_capped() -> None:
    flood = LeadFlood()
    for _ in range(MAX_LEADS_PER_CONTACT_PER_DAY):
        flood.request()

    assert flood.request(in_chat=False).id is not None
    with pytest.raises(RateLimitedError):
        flood.request()


def test_test_chat_requests_never_count() -> None:
    flood = LeadFlood()
    for _ in range(MAX_LEADS_PER_CONTACT_PER_DAY + 2):
        flood.request(is_sandbox=True)

    assert flood.request().id is not None


def test_handoffs_past_the_cap_are_queued_without_alerting_staff() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")
    alerted: list[int] = []
    statuses: list[HandoffStatus] = []
    for _ in range(MAX_HANDOFF_ALERTS_PER_CONTACT_PER_DAY + 1):
        before = len(fixture.world.notifier.sent)
        statuses.append(fixture.hand_off().status)
        alerted.append(len(fixture.world.notifier.sent) - before)

    assert alerted[:MAX_HANDOFF_ALERTS_PER_CONTACT_PER_DAY] == [3, 3, 3]
    assert alerted[-1] == 0
    # The last one still joins the queue and silences the assistant.
    assert statuses[-1] is HandoffStatus.PENDING
    assert len(fixture.world.handoff_repo.list_by_business(fixture.business.id)) == 4


def test_test_chat_handoffs_neither_alert_nor_count() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")
    for _ in range(MAX_HANDOFF_ALERTS_PER_CONTACT_PER_DAY + 1):
        fixture.hand_off(is_sandbox=True)
    before = len(fixture.world.notifier.sent)

    fixture.hand_off()

    assert len(fixture.world.notifier.sent) - before == 3


def test_an_emergency_alerts_staff_past_the_cap() -> None:
    fixture = HandoffFixture("2026-10-05T11:00:00+03:00")
    for _ in range(MAX_HANDOFF_ALERTS_PER_CONTACT_PER_DAY):
        fixture.hand_off()
    before = len(fixture.world.notifier.sent)

    quiet = fixture.hand_off(urgency=HandoffUrgency.HIGH)
    after_quiet = len(fixture.world.notifier.sent)
    emergency = fixture.hand_off(urgency=HandoffUrgency.CRITICAL)

    assert after_quiet == before
    assert quiet.status is HandoffStatus.PENDING
    assert len(fixture.world.notifier.sent) - after_quiet == 3
    assert emergency.urgency is HandoffUrgency.CRITICAL
