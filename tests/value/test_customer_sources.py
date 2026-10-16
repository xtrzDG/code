"""Where customers came from: conversations, bookings and value per source."""

import pytest

from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.value import CustomerSourceKind, ValueBasis
from app.schemas.domain.value_settings import ValueSettingsDocument
from app.schemas.dto.value.customer_sources import (
    CustomerSourceRow,
    CustomerSourcesQuery,
    CustomerSourcesView,
)
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.value.constrained_integers import AverageCheckMinor
from app.use_cases.insights.value.customer_source_rows import MAX_TAGGED_ROWS
from app.use_cases.insights.value.value_estimates import estimate_business_value
from app.utilities.value.value_keys import value_settings_id_of
from tests.value.insight_bench import InsightBench

WEEK_FROM: LocalDate = LocalDate("2026-09-28")
WEEK_TO: LocalDate = LocalDate("2026-10-04")


def report(bench: InsightBench, user_id: UserId | None = None) -> CustomerSourcesView:
    return bench.sources().run(
        CustomerSourcesQuery(
            user_id=user_id or bench.owner.id,
            business_id=bench.business.id,
            date_from=WEEK_FROM,
            date_to=WEEK_TO,
        )
    )


def with_check(bench: InsightBench, check: int) -> None:
    bench.world.value_settings_repo.save(
        ValueSettingsDocument(
            id=value_settings_id_of(bench.business.id),
            business_id=bench.business.id,
            average_check_minor=AverageCheckMinor(check),
        )
    )


def by_label(view: CustomerSourcesView) -> dict[str, CustomerSourceRow]:
    return {
        str(row.acquisition_source or ",".join(row.channels)): row for row in view.rows
    }


def test_each_source_counts_its_conversations_bookings_and_value() -> None:
    bench = InsightBench()
    with_check(bench, 5_000)
    qr = bench.tagged("2026-09-29T13:00:00+04:00", "qr-tables")
    bench.tagged("2026-09-30T13:00:00+04:00", "qr-tables", ChannelKind.TELEGRAM)
    untagged = bench.tagged("2026-10-01T13:00:00+04:00", None)
    bio = bench.tagged(
        "2026-10-02T13:00:00+04:00", "instagram-bio", ChannelKind.INSTAGRAM
    )
    older = bench.tagged("2026-09-20T13:00:00+04:00", "flyer")
    sandbox = bench.tagged("2026-09-30T15:00:00+04:00", "qr-tables", is_sandbox=True)
    bench.booking("2026-09-29T14:00:00+04:00", qr, value=(8_000, "GEL"))
    bench.booking("2026-09-29T15:00:00+04:00", qr)
    bench.booking("2026-09-29T16:00:00+04:00", qr, value=(3_000, "USD"))
    bench.booking("2026-10-01T14:00:00+04:00", untagged, BookingStatus.CANCELLED)
    bench.booking("2026-10-01T15:00:00+04:00", older, value=(4_000, "GEL"))
    bench.booking("2026-09-30T16:00:00+04:00", sandbox, is_sandbox=True)
    bench.booking("2026-10-01T17:00:00+04:00", None, value=(9_000, "GEL"))
    bench.request("2026-10-02T14:00:00+04:00", bio)

    view = report(bench)

    rows = by_label(view)
    assert list(rows) == ["qr-tables", "instagram-bio", "whatsapp", "flyer"]
    qr_row = rows["qr-tables"]
    assert qr_row.kind is CustomerSourceKind.TAGGED
    assert qr_row.channels == [ChannelKind.TELEGRAM, ChannelKind.WHATSAPP]
    assert (qr_row.conversation_count, qr_row.booking_count) == (2, 3)
    # Its own value, then the unvalued and the other currency's at the check.
    assert qr_row.estimated_value_minor == 8_000 + 2 * 5_000
    assert rows["instagram-bio"].request_count == 1
    assert rows["whatsapp"].kind is CustomerSourceKind.UNTAGGED
    assert rows["whatsapp"].booking_count == 0
    # A booking counts in the period it was made, for its conversation's source.
    assert (rows["flyer"].conversation_count, rows["flyer"].booking_count) == (0, 1)
    assert rows["flyer"].estimated_value_minor == 4_000
    assert (view.date_from, view.date_to, view.currency_code) == (
        "2026-09-28",
        "2026-10-04",
        "GEL",
    )


def test_without_the_owners_check_the_niches_prices_the_rest() -> None:
    bench = InsightBench()
    qr = bench.tagged("2026-09-29T13:00:00+04:00", "qr")
    plain = bench.tagged("2026-09-29T14:00:00+04:00", "flyer")
    bench.booking("2026-09-29T15:00:00+04:00", qr, value=(8_000, "GEL"))
    bench.booking("2026-09-29T16:00:00+04:00", plain)
    typical = estimate_business_value(bench.world.catalogs(), bench.business)

    rows = by_label(report(bench))

    assert rows["qr"].estimated_value_minor == 8_000
    assert typical.rates.average_check is not None
    assert rows["flyer"].estimated_value_minor == int(typical.rates.average_check)


def test_requests_earn_for_niches_that_take_orders() -> None:
    bench = InsightBench(niche_key=NicheKey.ONLINE_SHOP)
    with_check(bench, 7_000)
    bio = bench.tagged("2026-09-29T13:00:00+04:00", "bio", ChannelKind.INSTAGRAM)
    bench.request("2026-09-29T14:00:00+04:00", bio)
    bench.request("2026-09-30T14:00:00+04:00", bio)

    view = report(bench)

    assert view.value_basis is ValueBasis.REQUESTS
    assert by_label(view)["bio"].estimated_value_minor == 14_000


def test_many_tags_fold_the_smallest_together() -> None:
    bench = InsightBench()
    for number in range(MAX_TAGGED_ROWS + 3):
        for _ in range(1 + (number < MAX_TAGGED_ROWS)):
            bench.tagged("2026-09-29T13:00:00+04:00", f"tag-{number:02d}")

    rows = report(bench).rows

    assert len(rows) == MAX_TAGGED_ROWS + 1
    assert rows[-1].kind is CustomerSourceKind.OTHER
    assert (rows[-1].source_count, rows[-1].conversation_count) == (3, 3)
    assert rows[0].acquisition_source == "tag-00"


def test_staff_never_see_the_sources() -> None:
    bench = InsightBench()

    with pytest.raises(AccessDeniedError):
        report(bench, bench.staff_id)
