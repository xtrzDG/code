"""
The demo's AI-safety data tells one truth: the guard verdicts stored on the
replies are the ones the handoffs, the inbox chips and the admin's cards
read, the quality card has the month's judged conversations, and reply
speed differs per channel as live replies do.

- every handoff for unconfirmed values (UNVERIFIED_VALUES) has the reply the
  guard held back, with the values it names;
- the admin's guard counts are the stored verdicts of the last 7 days;
- a Georgian reply was rewritten for an unsupported claim;
- eight conversations of the last 30 days were judged, one below 3;
- web-chat replies wait 4 to 7 s, messenger replies 6 to 11 s.
"""

from collections import Counter
from typing import Any, cast

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor, ReplyGuardVerdict
from app.schemas.constants.handoffs import HandoffSummaryCode
from app.schemas.constants.reply_safety import ClaimVerdict
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.handoffs import HandoffDocument
from tests.demo.test_demo_seeding import (
    DEMO_ENVIRONMENT,
    RESTAURANT,
    SALON,
    businesses_by_name,
    sign_in_owner,
)
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import ADMIN_EMAIL

type JsonObject = dict[str, Any]

WEEK_MICROSECONDS: int = 7 * 24 * 60 * 60 * 1_000_000
WAIT_RANGES_MS: dict[ChannelKind, tuple[int, int]] = {
    ChannelKind.WEB_CHAT: (4_000, 7_000),
    ChannelKind.WHATSAPP: (6_000, 11_000),
    ChannelKind.TELEGRAM: (6_000, 11_000),
    ChannelKind.INSTAGRAM: (6_000, 11_000),
    ChannelKind.MESSENGER: (6_000, 11_000),
}
# The admin's percentiles are read from 1-second buckets.
BUCKET_MS: int = 1_000


class StoredDemo:
    """The seeded records of one demo business, read platform-wide."""

    def __init__(self, workshop: Workshop, business_id: str) -> None:
        collections = workshop.container.adapters.collections
        with workshop.container.utilities.storage_scope().platform_wide():
            self.messages: list[MessageDocument] = [
                message
                for message in collections.message_collection().list_all()
                if str(message.business_id) == business_id
            ]
            self.handoffs: list[HandoffDocument] = [
                handoff
                for handoff in collections.handoff_collection().list_all()
                if str(handoff.business_id) == business_id
            ]
            self.conversations: dict[str, ConversationDocument] = {
                str(conversation.id): conversation
                for conversation in collections.conversation_collection().list_all()
                if str(conversation.business_id) == business_id
            }

    def replies(self) -> list[MessageDocument]:
        return [m for m in self.messages if m.author is MessageAuthor.ASSISTANT]


def read(client: Any, path: str, headers: dict[str, str]) -> Any:
    response = client.get(path, headers=headers)
    assert response.status_code == 200, (path, response.text)
    return response.json()


def test_every_unconfirmed_value_handoff_has_the_reply_the_guard_held_back() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        businesses = businesses_by_name(client, sign_in_owner(workshop))
        stored = StoredDemo(workshop, str(businesses[RESTAURANT]["id"]))

    coded = [
        handoff
        for handoff in stored.handoffs
        if handoff.summary_code is HandoffSummaryCode.UNVERIFIED_VALUES
    ]
    assert coded, "the demo shows a guard handoff (Lukas Weber's corkage fee)"
    for handoff in coded:
        held = [
            reply
            for reply in stored.replies()
            if reply.conversation_id == handoff.conversation_id
            and reply.guard_verdict is ReplyGuardVerdict.HANDED_OFF
        ]
        assert held, f"no held-back reply in {handoff.conversation_id}"
        flagged = {str(value) for value in handoff.flagged_values}
        assert flagged <= {
            str(value) for reply in held for value in reply.unverified_values
        }

    rewritten = [
        reply
        for reply in stored.replies()
        if reply.guard_verdict is ReplyGuardVerdict.REWRITTEN
    ]
    assert [str(reply.language) for reply in rewritten] == ["ka"]
    assert [finding.verdict for finding in rewritten[0].claim_findings] == [
        ClaimVerdict.UNSUPPORTED
    ]


def test_the_admin_guard_counts_are_the_stored_verdicts() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        businesses = businesses_by_name(client, sign_in_owner(workshop))
        admin_token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
        admin = bearer(admin_token)
        now = int(workshop.clock.wall_clock.now_unix())
        for name in (RESTAURANT, SALON):
            business_id = str(businesses[name]["id"])
            detail: JsonObject = read(client, f"/v1/admin/clients/{business_id}", admin)
            guard: JsonObject = detail["summary"]["guard_activity"]
            stored = StoredDemo(workshop, business_id)
            verdicts = Counter(
                reply.guard_verdict
                for reply in stored.replies()
                if int(reply.created_at) >= now - WEEK_MICROSECONDS
                and reply.guard_verdict is not None
            )

            assert guard["checked_replies"] == sum(verdicts.values()), name
            assert guard["rewritten_replies"] == verdicts[ReplyGuardVerdict.REWRITTEN]
            assert guard["handed_off_replies"] == verdicts[ReplyGuardVerdict.HANDED_OFF]
        restaurant = read(
            client, f"/v1/admin/clients/{businesses[RESTAURANT]['id']}", admin
        )["summary"]["guard_activity"]
        assert (restaurant["rewritten_replies"], restaurant["handed_off_replies"]) == (
            1,
            1,
        )


def test_eight_judged_conversations_one_below_three() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        businesses = businesses_by_name(client, sign_in_owner(workshop))
        admin_token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
        admin = bearer(admin_token)
        samples: dict[str, int] = {}
        for name in (RESTAURANT, SALON):
            business_id = str(businesses[name]["id"])
            quality: JsonObject = read(
                client, f"/v1/admin/clients/{business_id}/quality", admin
            )

            samples[name] = int(quality["sample_count"])
            scores = [float(sample["average_score"]) for sample in quality["lowest"]]
            assert len([score for score in scores if score < 3]) == 1, name
            assert 3 < float(quality["average_score"]) < 5, name

    # The salon's quieter month has fewer conversations to judge.
    assert samples[RESTAURANT] == 8
    assert 3 <= samples[SALON] <= 8


def test_reply_speed_differs_per_channel_as_live_replies_do() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        businesses = businesses_by_name(client, sign_in_owner(workshop))
        admin_token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
        admin = bearer(admin_token)
        business_id = str(businesses[RESTAURANT]["id"])
        stored = StoredDemo(workshop, business_id)
        speed: JsonObject = read(client, f"/v1/admin/clients/{business_id}", admin)[
            "summary"
        ]["reply_speed"]

    measured = [
        reply for reply in stored.replies() if reply.reply_latency_ms is not None
    ]
    assert measured
    waits: dict[ChannelKind, set[int]] = {}
    for reply in measured:
        assert reply.channel is not None
        low, high = WAIT_RANGES_MS[reply.channel]
        assert low <= int(cast(int, reply.reply_latency_ms)) <= high, reply.channel
        waits.setdefault(reply.channel, set()).add(
            int(cast(int, reply.reply_latency_ms))
        )
    assert len(waits[ChannelKind.WHATSAPP]) > 1, "waits are drawn, not one number"
    for channel in cast(list[JsonObject], speed["channels"]):
        low, high = WAIT_RANGES_MS[ChannelKind(channel["channel"])]
        assert low - BUCKET_MS <= int(channel["p50_ms"]) <= high, channel
