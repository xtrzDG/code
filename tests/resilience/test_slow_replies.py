"""
The admin sees how fast each client's customers hear back (p50 and p95 of
the last 7 days, per channel), and SLOW_REPLIES when one reply in twenty
took more than 15 s.
"""

from collections.abc import Sequence

from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.client_health import ClientHealthIssue, ClientHealthStatus
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.admin import AdminClientsQuery, AdminClientSummary
from app.schemas.dto.reply_speed import ReplyLatencyBucketCount
from app.schemas.typings.client_health.constrained_integers import (
    MeasuredReplyCount,
)
from app.schemas.typings.conversations.constrained_integers import (
    ReplyLatencyMilliseconds,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.storage.constrained_integers import DocumentBucketIndex
from app.utilities.client_health.reply_speed import (
    REPLY_LATENCY_BUCKET_STARTS,
    build_client_reply_speed,
    is_slow,
)
from tests.billing.admin_world import AdminWorld, build_admin_world, days_ago
from tests.billing.client_list_runs import list_clients


def georgian_summary(world: AdminWorld) -> AdminClientSummary:
    page = list_clients(world.testbed, AdminClientsQuery(user_id=world.admin.id))
    return next(item for item in page.items if item.business_id == world.georgian.id)


def add_replies(
    world: AdminWorld,
    channel: ChannelKind | None,
    latencies_ms: Sequence[int | None],
    days: float = 1,
) -> None:
    created_at = days_ago(world.testbed, days)
    conversation_id = ConversationId()
    world.testbed.message_repo.save_many(
        [
            MessageDocument(
                conversation_id=conversation_id,
                business_id=world.georgian.id,
                direction=MessageDirection.OUTBOUND,
                author=MessageAuthor.ASSISTANT,
                text=MessageText("Here you are."),
                channel=channel,
                reply_latency_ms=(
                    None if latency is None else ReplyLatencyMilliseconds(latency)
                ),
                created_at=created_at,
                updated_at=created_at,
            )
            for latency in latencies_ms
        ]
    )


def test_quick_replies_show_their_percentiles_per_channel() -> None:
    world = build_admin_world()
    add_replies(world, ChannelKind.WHATSAPP, [2_500] * 18 + [9_000] * 2)
    add_replies(world, ChannelKind.TELEGRAM, [1_200] * 5)

    speed = georgian_summary(world).reply_speed

    assert int(speed.reply_count) == 25
    assert speed.p50_ms is not None and speed.p95_ms is not None
    assert 2_000 <= int(speed.p50_ms) <= 3_000
    assert int(speed.p95_ms) <= 10_000
    whatsapp, telegram = speed.channels
    assert (whatsapp.channel, int(whatsapp.reply_count)) == (ChannelKind.WHATSAPP, 20)
    assert (telegram.channel, int(telegram.reply_count)) == (ChannelKind.TELEGRAM, 5)
    assert 1_000 <= int(telegram.p50_ms) <= 1_500
    assert ClientHealthIssue.SLOW_REPLIES not in georgian_summary(world).health_issues


def test_slow_replies_need_attention() -> None:
    world = build_admin_world()
    add_replies(world, ChannelKind.WHATSAPP, [3_000] * 15 + [40_000] * 5)

    summary = georgian_summary(world)

    assert summary.reply_speed.p95_ms is not None
    assert int(summary.reply_speed.p95_ms) > 15_000
    assert ClientHealthIssue.SLOW_REPLIES in summary.health_issues
    assert summary.health_status is not ClientHealthStatus.HEALTHY


def test_only_measured_assistant_replies_of_the_last_week_count() -> None:
    world = build_admin_world()
    # Too old, unmeasured (test chat, voice, holding texts) or without a
    # channel: left out.
    add_replies(world, ChannelKind.WHATSAPP, [60_000] * 10, days=8)
    add_replies(world, ChannelKind.WHATSAPP, [None] * 10)
    add_replies(world, None, [60_000] * 10)
    add_replies(world, ChannelKind.INSTAGRAM, [4_000] * 3)

    speed = georgian_summary(world).reply_speed

    assert int(speed.reply_count) == 3
    assert [channel.channel for channel in speed.channels] == [ChannelKind.INSTAGRAM]


def test_a_few_slow_replies_of_a_quiet_client_are_not_a_pattern() -> None:
    world = build_admin_world()
    add_replies(world, ChannelKind.TELEGRAM, [40_000] * 9)

    summary = georgian_summary(world)

    assert int(summary.reply_speed.reply_count) == 9
    assert ClientHealthIssue.SLOW_REPLIES not in summary.health_issues


def test_no_measured_replies_mean_no_percentiles() -> None:
    speed = build_client_reply_speed([])

    assert int(speed.reply_count) == 0
    assert speed.p50_ms is None and speed.p95_ms is None
    assert not is_slow(speed)


def test_percentiles_are_interpolated_inside_their_bucket() -> None:
    fifteen_seconds = REPLY_LATENCY_BUCKET_STARTS.index(15_000)
    buckets = [
        ReplyLatencyBucketCount(
            channel=ChannelKind.WEB_CHAT,
            bucket=DocumentBucketIndex(fifteen_seconds - 1),
            count=MeasuredReplyCount(94),
        ),
        ReplyLatencyBucketCount(
            channel=ChannelKind.WEB_CHAT,
            bucket=DocumentBucketIndex(fifteen_seconds),
            count=MeasuredReplyCount(6),
        ),
    ]

    speed = build_client_reply_speed(buckets)

    assert speed.p95_ms is not None
    # 94 replies under 15 s, 6 from 15 s to 20 s: the 95th lies just past
    # 15 s, so the client is slow.
    assert 15_000 < int(speed.p95_ms) < 16_000
    assert is_slow(speed)
