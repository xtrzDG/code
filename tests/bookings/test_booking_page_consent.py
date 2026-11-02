"""
End to end over HTTP: the marketing box of a guest's booking page. It is
unticked until the guest ticks it; ticking records the consent on their
contact (the page, the booking, the wording's version, the moment) and the
team's card shows it; unticking takes it back.
"""

from typing import cast

import pytest
from typed_time_provider import Microseconds

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.customer_repositories import CustomerCardRepoContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.booking_manage import BookingManageClaims, ManagedBookingAction
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.constrained_integers import (
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.booleans import IsMarketingConsentGiven
from app.use_cases.bookings.public.change_managed_booking_consent_use_case import (
    ChangeManagedBookingConsentUseCase,
)
from app.use_cases.bookings.public.managed_booking_pages import ManagedBookingPages
from tests.bookings.manage_journey import BookedTable, book_a_table
from tests.e2e.harness import Workshop
from tests.e2e.journeys import JsonObject
from tests.users.accounts_clock import AdjustableClock

TEXT_VERSION: str = "2026-11-02"


def tick(workshop: Workshop, booked: BookedTable, is_given: bool) -> JsonObject:
    answer = workshop.client.post(
        f"{booked.page}/marketing-consent",
        json={"is_given": is_given, "text_version": TEXT_VERSION},
    )
    assert answer.status_code == 200, answer.text
    assert answer.headers["cache-control"] == "no-store"
    view: JsonObject = answer.json()
    return view


def card_consent(workshop: Workshop, booked: BookedTable) -> JsonObject:
    """The team's view of the booking's guest: their marketing consent."""

    restaurant = booked.restaurant
    [customer] = workshop.client.get(
        f"{restaurant.base}/contacts", headers=restaurant.headers
    ).json()["items"]
    detail = workshop.client.get(
        f"{restaurant.base}/contacts/{customer['id']}", headers=restaurant.headers
    )
    assert detail.status_code == 200, detail.text
    consent: JsonObject = detail.json()["marketing_consent"]
    return consent


def contact_updates(
    workshop: Workshop, booked: BookedTable
) -> list[AuditLogEntryDocument]:
    """The business's audit entries that changed a contact, oldest first."""

    business_id = BusinessId(booked.restaurant.business_id)
    container = workshop.container
    with container.utilities.storage_scope().scoped_to_business(business_id):
        entries = container.repositories.audit_log_repo().list_by_business(business_id)
    return [
        entry
        for entry in entries
        if entry.entity == "contact" and entry.action is AuditAction.UPDATE
    ]


def test_the_box_is_unticked_until_the_guest_ticks_it(workshop: Workshop) -> None:
    booked = book_a_table(workshop)

    page = workshop.client.get(booked.page).json()

    assert page["marketing_consent"] is False
    assert card_consent(workshop, booked)["status"] == "not_given"


def test_a_tick_is_recorded_kept_and_taken_back_by_unticking(
    workshop: Workshop,
) -> None:
    booked = book_a_table(workshop)

    ticked = tick(workshop, booked, True)

    assert ticked["marketing_consent"] is True
    assert workshop.client.get(booked.page).json()["marketing_consent"] is True
    consent = card_consent(workshop, booked)
    assert (consent["status"], consent["source"], consent["text_version"]) == (
        "agreed",
        "booking_page",
        TEXT_VERSION,
    )
    assert consent["recorded_by"] is None

    unticked = tick(workshop, booked, False)

    assert unticked["marketing_consent"] is False
    withdrawn = card_consent(workshop, booked)
    assert (withdrawn["status"], withdrawn["withdrawal"]) == (
        "withdrawn",
        "booking_page",
    )


def test_each_change_of_the_box_is_audited_as_the_guests_own(
    workshop: Workshop,
) -> None:
    booked = book_a_table(workshop)
    before = contact_updates(workshop, booked)

    tick(workshop, booked, True)
    tick(workshop, booked, False)

    changes = contact_updates(workshop, booked)[len(before) :]
    assert len(changes) == 2
    assert all(entry.actor_id is None for entry in changes)


def test_the_box_has_its_own_limit_and_never_uses_up_the_cancellation(
    workshop: Workshop,
) -> None:
    booked = book_a_table(workshop)

    answers = [
        workshop.client.post(
            f"{booked.page}/marketing-consent",
            json={"is_given": index % 2 == 0, "text_version": TEXT_VERSION},
        )
        for index in range(11)
    ]

    assert [answer.status_code for answer in answers[:10]] == [200] * 10
    assert answers[10].status_code == 429
    cancelled = workshop.client.post(f"{booked.page}/cancel")
    assert cancelled.status_code == 200, cancelled.text


def test_an_unknown_wording_or_a_forged_link_is_refused(workshop: Workshop) -> None:
    booked = book_a_table(workshop)

    unknown = workshop.client.post(
        f"{booked.page}/marketing-consent",
        json={"is_given": True, "text_version": "2020-01-01"},
    )
    forged = workshop.client.post(
        f"{booked.page[:-4]}AAAA/marketing-consent",
        json={"is_given": True, "text_version": TEXT_VERSION},
    )

    assert unknown.status_code == 422
    assert forged.status_code == 404
    assert card_consent(workshop, booked)["status"] == "not_given"


def test_an_erased_guest_cannot_tick_the_box(workshop: Workshop) -> None:
    booked = book_a_table(workshop)
    restaurant = booked.restaurant
    [customer] = workshop.client.get(
        f"{restaurant.base}/contacts", headers=restaurant.headers
    ).json()["items"]
    erased = workshop.client.delete(
        f"{restaurant.base}/contacts/{customer['id']}", headers=restaurant.headers
    )
    assert erased.status_code == 204, erased.text

    ticked = workshop.client.post(
        f"{booked.page}/marketing-consent",
        json={"is_given": True, "text_version": TEXT_VERSION},
    )

    assert ticked.status_code == 409


def test_a_change_without_the_wording_is_refused_before_anything_is_read() -> None:
    business_id = BusinessId()
    use_case = ChangeManagedBookingConsentUseCase(
        pages=cast(ManagedBookingPages, object()),
        card_repo=cast(CustomerCardRepoContract, object()),
        audit_log_repo=cast(AuditLogRepoContract, object()),
        wall_clock=AdjustableClock().build_wall_clock(),
    )

    with pytest.raises(ValidationFailedError):
        use_case.run(
            ManagedBookingAction(
                business_id=business_id,
                claims=BookingManageClaims(
                    business_id=business_id,
                    booking_id=BookingId(),
                    booking_version=BookingStartsAtUnixSeconds(1_790_000_000),
                    expires_at=Microseconds(1_800_000_000_000_000),
                ),
                marketing_consent=IsMarketingConsentGiven(True),
            )
        )
