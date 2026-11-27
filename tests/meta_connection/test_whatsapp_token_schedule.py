"""
When WhatsApp tokens are renewed and which reminder an outcome calls for:
the ends a run looks at, the moment a token has ended, the three days of
the ENDING reminder, and the subject that makes each reminder one per
token and stage.
"""

import re

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.meta_connection import (
    WhatsAppTokenNoticeStage,
    WhatsAppTokenRefreshOutcome,
)
from app.schemas.domain.channels import ChannelDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.meta_connection.constrained_integers import (
    MetaTokenRefreshDays,
)
from app.utilities.channels.whatsapp_token_schedule import (
    describe_end,
    has_token_ended,
    notice_stage,
    notice_subject,
    notice_tag,
    refresh_window,
)
from tests.platform_ops.ops_documents import DAY, HOUR, at

Outcome = WhatsAppTokenRefreshOutcome
Stage = WhatsAppTokenNoticeStage
CHANNEL: ChannelId = ChannelId()


def ending(ends_at: Microseconds | None) -> ChannelDocument:
    return ChannelDocument(
        business_id=BusinessId(),
        kind=ChannelKind.WHATSAPP,
        credential_expires_at=ends_at,
    )


def test_a_run_looks_a_week_back_on_errors_and_the_refresh_days_ahead() -> None:
    # (The earliest end on a channel in ERROR, the end tokens are renewed before.)
    assert refresh_window(at(0), MetaTokenRefreshDays(15)) == (
        at(-7 * DAY),
        at(15 * DAY),
    )
    assert refresh_window(at(0), MetaTokenRefreshDays(60)) == (
        at(-7 * DAY),
        at(60 * DAY),
    )


def test_a_token_has_ended_from_its_end_on() -> None:
    assert has_token_ended(ending(at(0)), at(0)) is True
    assert has_token_ended(ending(at(-DAY)), at(0)) is True
    assert has_token_ended(ending(at(1)), at(0)) is False
    assert has_token_ended(ending(None), at(0)) is False


@pytest.mark.parametrize(
    ("left", "outcome", "stage"),
    [
        (10 * DAY, Outcome.REFUSED, Stage.REFRESH_REFUSED),
        (3 * DAY + 1, Outcome.REFUSED, Stage.REFRESH_REFUSED),
        (3 * DAY, Outcome.REFUSED, Stage.ENDING),
        (HOUR, Outcome.REFUSED, Stage.ENDING),
        (10 * DAY, Outcome.DEFERRED, None),
        (3 * DAY + 1, Outcome.DEFERRED, None),
        (3 * DAY, Outcome.DEFERRED, Stage.ENDING),
        (HOUR, Outcome.REFRESHED, None),
        (HOUR, Outcome.REPLACED, None),
    ],
)
def test_the_reminder_an_outcome_calls_for(
    left: int, outcome: WhatsAppTokenRefreshOutcome, stage: Stage | None
) -> None:
    assert notice_stage(at(left), at(0), outcome) is stage


def test_each_token_end_and_stage_has_its_own_subject() -> None:
    morning = notice_subject(CHANNEL, at(HOUR), Stage.ENDING)
    evening = notice_subject(CHANNEL, at(12 * HOUR), Stage.ENDING)
    refused = notice_subject(CHANNEL, at(HOUR), Stage.REFRESH_REFUSED)
    next_day = notice_subject(CHANNEL, at(DAY), Stage.ENDING)
    other = notice_subject(ChannelId(), at(HOUR), Stage.ENDING)

    # Monday 2026-10-05 08:00 UTC, an hour and twelve hours later.
    assert str(morning) == f"whatsapp_token:{CHANNEL}-20261005-ending"
    assert evening == morning
    assert len({morning, refused, next_day, other}) == 4


def test_subjects_and_tags_keep_their_shapes() -> None:
    for stage in Stage:
        subject = str(notice_subject(CHANNEL, at(60 * DAY), stage))
        assert re.fullmatch(r"[a-z_]+:[A-Za-z0-9_-]+", subject)
        assert len(subject) <= 92

    assert str(notice_tag(CHANNEL)) == f"whatsapp_token:{CHANNEL}"


def test_a_tokens_end_reads_in_utc_for_the_log() -> None:
    assert describe_end(at(0)) == "2026-10-05T08:00:00+00:00"
    assert describe_end(None) == "never"
